"""Proxy local para os webhooks do backend n8n, sem fallback silencioso para Python."""

import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

router = APIRouter()
READ_RESOURCES = {'analytics','models','quality','pipelines','insights','status'}
WRITE_RESOURCES = {'jobs','analyst'}


def target_for(method, path):
    """Expõe somente contratos conhecidos; o navegador não escolhe URLs de destino."""
    if method == 'GET' and path in READ_RESOURCES:
        return 'predictive-bi-data', {'resource':path}
    if method == 'GET' and path.startswith('jobs/'):
        identifier = path.split('/',1)[1]
        if len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
            raise HTTPException(422, 'Identificador de execução inválido.')
        return 'predictive-bi-data', {'resource':'job','id':identifier}
    if method == 'POST' and path in WRITE_RESOURCES:
        return 'predictive-bi-actions', {'resource':path}
    raise HTTPException(404, 'Rota não disponível no backend n8n.')


def n8n_base_url():
    value = os.getenv('N8N_BASE_URL','http://127.0.0.1:5678').rstrip('/')
    parsed = urlparse(value)
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1','localhost','n8n'}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('','/')):
        raise HTTPException(503, 'N8N_BASE_URL deve apontar para o serviço local do projeto.')
    return value


@router.get('/workflow-api/{path:path}', operation_id='n8n_read_proxy')
@router.post('/workflow-api/{path:path}', operation_id='n8n_write_proxy')
async def via_n8n(path: str, request: Request):
    webhook, parameters = target_for(request.method, path)
    allowed_filters = {'start','end','category','region'} if path == 'analytics' else set()
    if any(key not in allowed_filters for key in request.query_params):
        raise HTTPException(422, 'Filtro desconhecido para esta rota.')
    parameters.update(dict(request.query_params))
    kwargs = {'params':parameters}
    if request.method == 'POST':
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(422, 'Corpo JSON inválido.') from None
        if not isinstance(payload, dict):
            raise HTTPException(422, 'Envie um objeto JSON.')
        kwargs['json'] = payload
        key = request.headers.get('idempotency-key')
        if key:
            if len(key)>160:
                raise HTTPException(422, 'Chave de idempotência muito longa.')
            kwargs['headers'] = {'Idempotency-Key':key}
    url = n8n_base_url()+'/webhook/'+webhook
    try:
        async with httpx.AsyncClient(timeout=150, trust_env=False) as client:
            response = await client.request(request.method, url, **kwargs)
        if response.status_code == 404:
            raise HTTPException(503, 'Publique os workflows Backend de leitura e Backend de ações no n8n. O webhook ainda não está disponível.')
        try:
            body = response.json()
        except ValueError:
            raise HTTPException(502, 'O workflow n8n não retornou JSON válido.') from None
        return JSONResponse(body, status_code=response.status_code,
                            headers={'X-Predictive-Backend':'n8n'})
    except httpx.RequestError:
        raise HTTPException(503, 'O backend n8n não respondeu. Confira o serviço em localhost:5678 e os workflows publicados. A chamada não foi desviada para Python.') from None
