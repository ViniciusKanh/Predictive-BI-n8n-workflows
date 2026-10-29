"""Testes de invariantes reais, com dados de teste isolados do banco demonstrativo."""

import hashlib
import json
import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import db, settings
from backend.insights import Finding, Selection, render, verify_selection
from backend.ml import FEATURES, churn_snapshot
from backend.pipelines import etl
from backend.runtime_loop import create_loop


def client_for(app):
    return TestClient(app, backend_options={'loop_factory': create_loop})


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    import backend.pipelines as pipelines
    import backend.dataset as dataset
    folder = tmp_path/'source'
    folder.mkdir()
    monkeypatch.setattr(settings,'DATABASE_URL','sqlite:///'+str(tmp_path/'test.db'))
    monkeypatch.setattr(pipelines,'DATA',folder)
    monkeypatch.setattr(dataset,'DATA',folder)
    pd.DataFrame([{'customer_id':1,'name':'Cliente teste','region':'Sul','joined_at':'2024-01-01',
                   'channel':'E-commerce'}]).to_csv(folder/'customers.csv',index=False)
    pd.DataFrame([{'product_id':1,'name':'Produto teste','category':'Casa','price_cents':1000}]).to_csv(folder/'products.csv',index=False)
    rows = [{'order_id':i,'customer_id':1,'product_id':1,'order_date':f'2024-01-{i:02}',
             'quantity':1,'gross_cents':1000,'discount_cents':100,'revenue_cents':900,
             'status':'completed','updated_at':f'2024-01-{i:02}T00:00:00'} for i in (1,2,10)]
    pd.DataFrame(rows).to_csv(folder/'orders.csv',index=False)
    (folder/'manifest.json').write_text(json.dumps({'start':'2024-01-01','end':'2024-01-31',
        'demonstrative':True,'orders':3}),encoding='utf-8')
    db.init_db()
    return folder


def test_etl_replay_does_not_duplicate_or_rewrite(isolated):
    first=etl()
    total=db.query('SELECT SUM(revenue_cents) AS total FROM fact_order')[0]['total']
    second=etl()
    assert first['inserted']==3
    assert second['inserted']==second['updated']==0
    assert total==db.query('SELECT SUM(revenue_cents) AS total FROM fact_order')[0]['total']==2700
    assert len(db.query('SELECT * FROM fact_order'))==3


def test_late_correction_updates_old_order_without_duplication(isolated):
    etl()
    frame=pd.read_csv(isolated/'orders.csv')
    frame.loc[frame.order_id==1,['discount_cents','revenue_cents','updated_at']]=[200,800,'2024-01-20T00:00:00']
    frame.to_csv(isolated/'orders.csv',index=False)
    result=etl()
    assert result['updated']==1 and result['inserted']==0
    assert db.query('SELECT revenue_cents FROM fact_order WHERE order_id=1')[0]['revenue_cents']==800
    assert db.get_state('etl_watermark')['updated_at']=='2024-01-20T00:00:00'


def test_invalid_batch_preserves_data_and_watermark(isolated):
    etl()
    watermark=db.get_state('etl_watermark')
    frame=pd.read_csv(isolated/'orders.csv')
    frame.loc[frame.order_id==10,'quantity']=-1
    frame.to_csv(isolated/'orders.csv',index=False)
    with pytest.raises(ValidationError):
        etl()
    assert db.get_state('etl_watermark')==watermark
    assert db.query('SELECT SUM(revenue_cents) AS total FROM fact_order')[0]['total']==2700
    assert db.query("SELECT status FROM pipeline_run ORDER BY started_at DESC LIMIT 1")[0]['status']=='failed'


def test_orphan_rolls_back(isolated):
    etl()
    original=db.get_state('etl_watermark')
    frame=pd.read_csv(isolated/'orders.csv')
    frame.loc[frame.order_id==10,'customer_id']=999
    frame.to_csv(isolated/'orders.csv',index=False)
    with pytest.raises(ValueError,match='órfão'):
        etl()
    assert db.get_state('etl_watermark')==original


def test_raw_duplicates_are_not_silently_dropped(isolated):
    frame=pd.read_csv(isolated/'orders.csv')
    pd.concat([frame,frame.iloc[[0]]]).to_csv(isolated/'orders.csv',index=False)
    with pytest.raises(ValueError,match='duplicados'):
        etl()
    assert not db.query('SELECT * FROM fact_order')


def temporal_data():
    return pd.DataFrame([{'order_id':i,'customer_id':customer,'date':pd.Timestamp(d),
                          'status':'completed','revenue_cents':1000} for i,(customer,d) in enumerate(
                              [(1,'2024-01-01'),(2,'2024-01-05'),(1,'2024-05-01'),(2,'2024-07-01')])])


def test_future_purchases_change_labels_but_not_features():
    frame=temporal_data()
    before=churn_snapshot(frame,'2024-03-31')
    extra=pd.DataFrame([{'order_id':99,'customer_id':2,'date':pd.Timestamp('2024-05-02'),
                         'status':'completed','revenue_cents':99999999}])
    after=churn_snapshot(pd.concat([frame,extra]),'2024-03-31')
    pd.testing.assert_frame_equal(before[FEATURES],after[FEATURES])
    assert before.set_index('customer_id').loc[2,'churn']==1
    assert after.set_index('customer_id').loc[2,'churn']==0


def test_immature_labels_are_rejected():
    with pytest.raises(ValueError,match='amadureceram'):
        churn_snapshot(temporal_data(),'2024-06-15')


def test_agent_rejects_missing_evidence_and_incompatible_recommendation():
    facts={'revenue':{'value':123,'unit':'BRL','label':'Receita'}}
    with pytest.raises(ValueError):
        verify_selection(Selection(findings=[Finding(metric_id='risk',recommendation='monitorar')]),facts)
    with pytest.raises(ValueError):
        verify_selection(Selection(findings=[Finding(metric_id='revenue',recommendation='priorizar_retencao')]),facts)


def test_agent_cannot_inject_numeric_estimates():
    with pytest.raises(ValidationError):
        Selection.model_validate({'findings':[{'metric_id':'invented_revenue','recommendation':'monitorar'}]})
    selection=Selection(findings=[Finding(metric_id='revenue',recommendation='monitorar')])
    facts={'revenue':{'value':123,'unit':'BRL','label':'Receita'}}
    assert '123,00' in render(selection,facts)[0]['text']
    assert render(selection,facts)[0]['evidence']==facts['revenue']


def test_agent_rejects_interpretation_that_contradicts_growth():
    selection=Selection(findings=[Finding(metric_id='growth',recommendation='monitorar',interpretation='crescimento')])
    with pytest.raises(ValueError,match='contradiz'):
        verify_selection(selection,{'growth':{'value':-2.5}})


def test_ollama_does_not_select_embedding_cloud_or_oversized_models(monkeypatch):
    import backend.insights as insights
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'models':[
                {'name':'qwen3-embedding:0.6b','size':600_000_000},
                {'name':'qwen3:480b-cloud','size':100_000_000},
                {'name':'qwen3:14b','size':9_000_000_000},
                {'name':'qwen2.5:3b','size':2_000_000_000}]}
    monkeypatch.setattr(insights.httpx,'get',lambda *args,**kwargs:Response())
    assert insights.ollama_status()['model']=='qwen2.5:3b'


def test_unsupported_analyst_question_returns_no_fabricated_answer(isolated):
    from backend.insights import generate_insights
    etl()
    result=generate_insights('Qual a capital de outro planeta?')
    assert result['mode']=='insufficient_evidence' and result['findings']==[]


def test_job_retry_reuses_id_and_does_not_repeat_effect(isolated,monkeypatch):
    import backend.main as main
    class Immediate:
        def submit(self,fn,*args):
            fn(*args)
    monkeypatch.setattr(main,'pool',Immediate())
    client=client_for(main.app)
    request={'pipeline':'etl'}
    one=client.post('/api/jobs',json=request,headers={'Idempotency-Key':'test-key'})
    two=client.post('/api/jobs',json=request,headers={'Idempotency-Key':'test-key'})
    assert one.status_code==two.status_code==202
    assert one.json()['id']==two.json()['id']
    assert client.get(one.json()['status_url']).json()['status']=='success'
    assert len(db.query("SELECT * FROM pipeline_run WHERE pipeline='ETL'"))==1
    assert client.post('/api/jobs',json={'pipeline':'quality'},headers={'Idempotency-Key':'test-key'}).status_code==409


def test_real_demo_and_evaluated_artifacts():
    manifest=json.loads((settings.DATA/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['orders']>=10000 and manifest['demonstrative']
    assert hashlib.sha256((settings.DATA/'orders.csv').read_bytes()).hexdigest()==manifest['sha256']
    forecast=db.get_state('forecast')
    assert len(forecast['holdout'])==8 and len(forecast['forecast'])==8
    assert all(math.isfinite(row['prediction']) and row['prediction']>=0 for row in forecast['forecast'])
    actual=[r['actual'] for r in forecast['holdout']]
    predicted=[r['prediction'] for r in forecast['holdout']]
    measured=sum(abs(a-p) for a,p in zip(actual,predicted))/sum(actual)
    assert measured==pytest.approx(forecast['metrics']['wape'])
    churn=db.get_state('churn')
    assert len(churn['models'])>=2 and churn['explanation']['method']=='SHAP TreeExplainer'
    assert all(0<=row['test']['roc_auc']<=1 for row in churn['models'])


def test_importable_workflows_reference_real_api_routes():
    from backend.main import app
    paths=app.openapi()['paths']
    assert '/api/jobs' in paths and '/api/jobs/{job_id}' in paths
    files=list((settings.ROOT/'workflows').glob('*.json'))
    assert len(files)==4
    allowed={'manualTrigger','scheduleTrigger','httpRequest','wait','if','stopAndError'}
    for path in files:
        workflow=json.loads(path.read_text(encoding='utf-8'))
        names={n['name'] for n in workflow['nodes']}
        assert len(names)==len(workflow['nodes'])
        assert len({n['id'] for n in workflow['nodes']})==len(names)
        assert all(n['type'].split('.')[-1] in allowed for n in workflow['nodes'])
        for source,connection in workflow['connections'].items():
            assert source in names
            for branch in connection['main']:
                assert all(target['node'] in names for target in branch)


def test_live_api_endpoints_and_filters():
    from backend.main import app
    client=client_for(app)
    for path in ['/health','/api/analytics','/api/models','/api/quality','/api/pipelines','/api/insights','/api/status']:
        response=client.get(path)
        assert response.status_code==200, (path,response.text)
    all_rows=client.get('/api/analytics').json()
    region=client.get('/api/analytics?region=Sul').json()
    assert region['kpis']['orders']<all_rows['kpis']['orders']
    assert all(row['region']=='Sul' for row in region['orders'])
    assert sum(row['revenue'] for row in region['monthly'])==pytest.approx(region['kpis']['revenue'])
    assert client.get('/api/analytics?start=invalid').status_code==422
    assert client.get('/api/jobs/nonexistent').status_code==404
