"""API local, contratos operacionais e serving da interface de produção."""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import db, settings
from backend.analytics import analytics
from backend.insights import generate_insights, ollama_status
from backend.ml import infer, train_all
from backend.pipelines import etl, quality, now
from backend.n8n_gateway import router as n8n_router

@asynccontextmanager
async def lifespan(application):
    db.init_db()
    # Uma reinicialização não pode deixar execuções antigas parecendo ativas.
    with db.connect() as con:
        db.execute(con, '''UPDATE pipeline_run SET status='interrupted',finished_at=?,
        error='ProcessRestart' WHERE status='running' ''', (now(),))
        for item in db.execute(con, "SELECT key,value FROM app_state WHERE key LIKE 'job:%'").fetchall():
            state = json.loads(item['value'])
            if state.get('status') in ('queued','running'):
                db.set_state(item['key'], {**state,'status':'failed','error':'ProcessRestart'}, con)
    yield


app = FastAPI(title='Predictive BI — Intelligent Analytics Platform', version='1.0.0', lifespan=lifespan,
              description='Analytics local com dataset comercial inteiramente demonstrativo.')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5180','http://127.0.0.1:5180'],
                   allow_methods=['GET','POST'], allow_headers=['Content-Type','Idempotency-Key'])
pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='predictive')
job_lock = Lock()
submit_lock = Lock()
app.include_router(n8n_router)


@app.get('/internal/orders')
def source_orders():
    """Fonte de registros: os KPIs no modo n8n são calculados pelo nó Code."""
    rows = db.query('''SELECT f.order_id,f.customer_id,f.order_date,f.quantity,f.revenue_cents,
    f.status,c.name AS customer,c.region,c.channel,p.name AS product,p.category
    FROM fact_order f JOIN dim_customer c ON f.customer_id=c.customer_id
    JOIN dim_product p ON f.product_id=p.product_id ORDER BY f.order_id''')
    return {'rows':rows,'demonstrative':True,'grain':'Um pedido de um produto'}


@app.get('/health')
def health():
    try:
        db.query('SELECT 1 AS ok')
        return {'status':'ok', 'application':'predictive-bi', 'database':'postgresql' if db.is_postgres() else 'sqlite-degraded',
                'demonstrative':True}
    except Exception:
        raise HTTPException(503, 'Banco indisponível') from None


@app.get('/api/analytics')
def get_analytics(start: date | None = None,
                  end: date | None = None,
                  category: str | None = None, region: str | None = None):
    if start and end and start > end:
        raise HTTPException(422, 'O início deve ser anterior ao fim do período.')
    return analytics(start.isoformat() if start else None, end.isoformat() if end else None, category, region)


@app.get('/api/models')
def models():
    return {k: db.get_state(k, {}) for k in ('models','forecast','churn','segments','inference')}


@app.get('/api/quality')
def get_quality():
    return db.get_state('quality', {})


@app.get('/api/pipelines')
def pipelines():
    runs = db.query('SELECT * FROM pipeline_run ORDER BY started_at DESC LIMIT 100')
    for run in runs:
        run['details'] = json.loads(run['details'])
    return {'runs':runs}


@app.get('/api/insights')
def insights():
    return db.get_state('insights', {})


@app.get('/api/status')
def status():
    return {'database':'PostgreSQL' if db.is_postgres() else 'SQLite (modo degradado)',
            'ollama':ollama_status(), 'demonstrative':True, 'manifest':db.get_state('manifest', {}),
            'tracking_uri':settings.MLFLOW_URI, 'served_at':now()}


class JobRequest(BaseModel):
    pipeline: str = Field(pattern='^(etl|train|infer|quality|insights)$')
    question: str = Field(default='Gerar resumo executivo.', max_length=1000)


def run_job(job_id, request):
    try:
        db.set_state('job:'+job_id, {'id':job_id,'status':'running','pipeline':request.pipeline})
        functions = {'etl':etl,'train':train_all,'infer':infer,'quality':quality,
                     'insights':lambda:generate_insights(request.question)}
        result = functions[request.pipeline]()
        db.set_state('job:'+job_id, {'id':job_id,'status':'success','pipeline':request.pipeline,'result':result})
    except Exception as error:
        db.set_state('job:'+job_id, {'id':job_id,'status':'failed','error':type(error).__name__})
    finally:
        job_lock.release()


@app.post('/api/jobs', status_code=202)
def submit(request: JobRequest, idempotency_key: str | None = Header(None, max_length=160)):
    with submit_lock:
        if idempotency_key:
            previous = db.get_state('request:'+idempotency_key)
            if previous:
                if previous['pipeline'] != request.pipeline or previous['question'] != request.question:
                    raise HTTPException(409, 'Chave de idempotência já usada com outro pedido.')
                return previous['response']
        if not job_lock.acquire(blocking=False):
            raise HTTPException(409,'Há um pipeline em execução; acompanhe a execução atual.')
        job_id = uuid4().hex
        response = {'id':job_id,'status':'queued','status_url':'/api/jobs/'+job_id,'queued_at':now()}
        try:
            db.set_state('job:'+job_id, {**response,'pipeline':request.pipeline})
            if idempotency_key:
                db.set_state('request:'+idempotency_key, {'pipeline':request.pipeline,
                    'question':request.question,'response':response})
            pool.submit(run_job, job_id, request)
        except Exception:
            job_lock.release()
            raise
        return response


@app.get('/api/jobs/{job_id}')
def job(job_id: str):
    result = db.get_state('job:'+job_id)
    if not result:
        raise HTTPException(404,'Execução não encontrada')
    return result


@app.post('/api/analyst')
def analyst(question: JobRequest):
    if question.pipeline != 'insights':
        raise HTTPException(422,'Use o pipeline insights para consultar o analista.')
    if not job_lock.acquire(blocking=False):
        raise HTTPException(409,'Pipeline em execução')
    try:
        return generate_insights(question.question)
    finally:
        job_lock.release()


# O build Vite também pode ser servido pela API, sem outro processo Node.
dist = settings.ROOT / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=str(dist), html=True), name='dashboard')
