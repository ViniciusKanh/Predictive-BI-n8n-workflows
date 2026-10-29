"""Valida cálculo compartilhado com o Code node e o contrato frontend → n8n."""

import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import db, settings
from backend.analytics import analytics
from backend.main import app, source_orders
from backend.n8n_gateway import target_for
from backend.runtime_loop import create_loop
from scripts.generate_n8n_backend import generate

NODE = shutil.which('node')


def run_js(script, payload):
    if not NODE:
        pytest.skip('Node.js necessário para conferir o Code node')
    result = subprocess.run([NODE,'-e',script], input=json.dumps(payload,ensure_ascii=False),
                            capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('filters',[{}, {'region':'Sul'}, {'start':'2026-07-01','category':'Casa'},
                                    {'region':'Região inexistente'}])
def test_n8n_kpis_reconcile_with_existing_reference(filters):
    source = source_orders()['rows']
    module = str(settings.ROOT/'workflows/code/analytics.cjs')
    script = '''const fs=require('fs'); const {calculateAnalytics}=require(process.argv[1]);
    const input=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(calculateAnalytics(input.rows,input.filters)));'''
    result = subprocess.run([NODE,'-e',script,module], input=json.dumps({'rows':source,'filters':filters}),
                            capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    expected = analytics(**filters)
    assert actual['empty'] == expected['empty']
    for key,value in expected['kpis'].items():
        if isinstance(value,(int,float)):
            assert actual['kpis'][key] == pytest.approx(value),key
        else:
            assert actual['kpis'][key] == value
    for key in ['monthly','daily','categories','regions','products','channels','heatmap','orders']:
        assert len(actual[key]) == len(expected[key]),key
    if not actual['empty']:
        assert sum(item['revenue'] for item in actual['monthly']) == pytest.approx(actual['kpis']['revenue'])
        assert [r['order_id'] for r in actual['orders']] == [r['order_id'] for r in expected['orders']]


def validator(workflow, request):
    code = next(node['parameters']['jsCode'] for node in workflow['nodes'] if node['name']=='Validar pedido')
    return run_js('''const fs=require('fs');const p=JSON.parse(fs.readFileSync(0,'utf8'));
    const value=new Function('$input','$execution',p.code)({first:()=>({json:p.request})},{id:'test-execution'});
    console.log(JSON.stringify(value[0].json));''', {'code':code,'request':request})


def test_webhook_validation_blocks_unknown_routes_and_dates(tmp_path):
    generate(output=tmp_path)
    flow = json.loads((tmp_path/'backend-data.json').read_text(encoding='utf-8'))
    for query in [{'resource':'http://example.com'}, {'resource':'analytics','start':'2026-02-31'},
                  {'resource':'job','id':'../../etc'}, {'resource':'analytics','start':'2026-09-01','end':'2026-01-01'}]:
        result = validator(flow,{'query':query})
        assert result['ok'] is False and result['statusCode'] == 422
    valid = validator(flow,{'query':{'resource':'analytics','region':'Sul'}})
    assert valid['worker_url']=='http://127.0.0.1:8101/internal/orders'


def test_mutation_workflow_rejects_invalid_pipeline_and_preserves_idempotency(tmp_path):
    generate(output=tmp_path)
    flow = json.loads((tmp_path/'backend-actions.json').read_text(encoding='utf-8'))
    invalid = validator(flow,{'query':{'resource':'jobs'},'body':{'pipeline':'shell-command'}})
    assert invalid['ok'] is False
    valid = validator(flow,{'query':{'resource':'jobs'},'body':{'pipeline':'train'},
                           'headers':{'idempotency-key':'same-action'}})
    assert valid['idempotency_key']=='same-action'
    assert valid['body']['pipeline']=='train'


def test_gateway_forwards_to_n8n_instead_of_python_and_preserves_status(monkeypatch):
    import backend.n8n_gateway as gateway
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(202,json={'id':'a'*32,'status':'queued'})
    original = httpx.AsyncClient
    monkeypatch.setattr(gateway.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    client=TestClient(app,backend_options={'loop_factory':create_loop})
    response=client.post('/workflow-api/jobs',json={'pipeline':'train'},headers={'Idempotency-Key':'click-123'})
    assert response.status_code==202 and response.headers['x-predictive-backend']=='n8n'
    assert calls[0].url.path=='/webhook/predictive-bi-actions'
    assert calls[0].url.params['resource']=='jobs'
    assert calls[0].headers['idempotency-key']=='click-123'


def test_unpublished_webhook_does_not_fallback_to_python(monkeypatch):
    import backend.n8n_gateway as gateway
    original=httpx.AsyncClient
    monkeypatch.setattr(gateway.httpx,'AsyncClient',lambda **kwargs:original(
        transport=httpx.MockTransport(lambda request:httpx.Response(404,json={'message':'not registered'}))))
    client=TestClient(app,backend_options={'loop_factory':create_loop})
    result=client.get('/workflow-api/analytics')
    assert result.status_code==503
    assert 'Publique' in result.json()['detail']
    assert client.get('/workflow-api/../../unsupported').status_code==404


def test_internal_source_contains_real_rows_and_gateway_whitelists_paths():
    rows=source_orders()['rows']
    total=db.query('SELECT COUNT(*) AS count FROM fact_order')[0]['count']
    assert len(rows)==total
    assert target_for('GET','models')==('predictive-bi-data',{'resource':'models'})
    assert target_for('GET','jobs/'+'a'*32)[1]['id']=='a'*32
