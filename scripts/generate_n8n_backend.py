"""Gera o backend HTTP do dashboard como workflows n8n editáveis."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]


def generate(api_url='http://127.0.0.1:8101', output=None):
    address = urlparse(api_url)
    if (address.scheme != 'http' or address.hostname not in ('127.0.0.1','localhost','api')
            or address.username or address.password or address.query or address.fragment
            or address.path not in ('','/')):
        raise ValueError('Use somente o endereço local da API worker, sem credenciais ou caminho.')
    api_url = api_url.rstrip('/')
    output = Path(output) if output else ROOT/'workflows'/'backend'
    output.mkdir(parents=True,exist_ok=True)
    aggregation = (ROOT/'workflows/code/analytics.cjs').read_text(encoding='utf-8').split('// O gerador')[0]
    for method, slug, title in [('GET','data','Backend de leitura'),('POST','actions','Backend de ações')]:
        read = method == 'GET'
        validator = '''
const request = $input.first().json;
const query = request.query || {};
const resource = query.resource;
const failure = detail => [{json:{ok:false,statusCode:422,body:{detail}}}];
const origin = __ORIGIN__;
'''.replace('__ORIGIN__',json.dumps(api_url))
        if read:
            validator += '''
const allowed = ['analytics','models','quality','pipelines','insights','status','job'];
if (!allowed.includes(resource)) return failure('Recurso de leitura desconhecido.');
const filters = {};
for (const key of ['start','end','category','region']) {
  const value = query[key];
  if (value !== undefined && (typeof value !== 'string' || value.length > 80)) return failure('Filtro inválido.');
  filters[key] = value || null;
}
for (const key of ['start','end']) {
  const value = filters[key];
  if (value) {
    const date = new Date(value+'T00:00:00Z');
    if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(value) || !Number.isFinite(date.getTime()) || date.toISOString().slice(0,10)!==value)
      return failure('Data inválida.');
  }
}
if (filters.start && filters.end && filters.start > filters.end) return failure('Período invertido.');
if (resource === 'job' && !/^[a-f0-9]{32}$/.test(query.id || '')) return failure('Identificador de execução inválido.');
const target = resource === 'analytics' ? '/internal/orders' : (resource === 'job' ? '/api/jobs/'+query.id : '/api/'+resource);
return [{json:{ok:true,resource,filters,worker_url:origin+target}}];
'''
        else:
            validator += '''
if (!['jobs','analyst'].includes(resource)) return failure('Ação desconhecida.');
const body = request.body;
if (!body || typeof body !== 'object' || Array.isArray(body)) return failure('Envie um objeto JSON.');
if (!['etl','quality','train','infer','insights'].includes(body.pipeline)) return failure('Pipeline inválido.');
if (resource === 'analyst' && body.pipeline !== 'insights') return failure('O analista aceita somente insights.');
if (body.question !== undefined && (typeof body.question !== 'string' || body.question.length>1000)) return failure('Pergunta inválida.');
const key = request.headers?.['idempotency-key'] || 'n8n-backend-'+$execution.id;
if (typeof key !== 'string' || key.length>160) return failure('Chave de idempotência inválida.');
return [{json:{ok:true,resource,worker_url:origin+'/api/'+resource,
  body:{pipeline:body.pipeline,question:body.question || 'Gerar resumo executivo.'},idempotency_key:key}}];
'''
        format_code = '''
const response = $input.first().json;
const code = Number(response.statusCode || 200);
if (code >= 400) return [{json:{statusCode:code,body:response.body || {detail:'Falha no worker'}}}];
'''
        if read:
            format_code += aggregation + '''
const request = $('Validar pedido').first().json;
const body = request.resource === 'analytics' ? calculateAnalytics(response.body.rows,request.filters) : response.body;
return [{json:{statusCode:code,body}}];
'''
        else:
            format_code += "return [{json:{statusCode:code,body:response.body}}];"
        def node(name, kind, version, params, position, **extra):
            return {'id':str(uuid5(NAMESPACE_URL,'pbi-backend-'+slug+name)), 'name':name,
                    'type':'n8n-nodes-base.'+kind,'typeVersion':version,
                    'parameters':params,'position':position,**extra}
        worker_params = {'method':method,'url':'={{ $json.worker_url }}',
                         'options':{'timeout':140000,'response':{'response':{
                             'fullResponse':True,'neverError':True,'responseFormat':'json'}}}}
        if not read:
            worker_params.update(sendBody=True,specifyBody='json',jsonBody='={{ $json.body }}',
                sendHeaders=True,headerParameters={'parameters':[
                    {'name':'Idempotency-Key','value':'={{ $json.idempotency_key }}'}]})
        nodes = [
            node('Receber pedido do dashboard','webhook',2,
                 {'httpMethod':method,'path':'predictive-bi-'+slug,'responseMode':'responseNode','options':{}},
                 [0,0],webhookId=str(uuid5(NAMESPACE_URL,'predictive-bi-'+slug))),
            node('Validar pedido','code',2,{'jsCode':validator,'mode':'runOnceForAllItems'},[250,0]),
            node('Pedido válido?','if',2.2,{'conditions':{'options':{'typeValidation':'strict','version':2},
                 'conditions':[{'id':'valid','leftValue':'={{ $json.ok }}','rightValue':True,
                 'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}},[500,0]),
            node('Consultar fonte de dados' if read else 'Executar serviço especializado','httpRequest',4.2,worker_params,[750,-100]),
            node('Calcular KPIs e montar resposta' if read else 'Preparar resposta da ação','code',2,
                 {'jsCode':format_code,'mode':'runOnceForAllItems'},[1000,-100]),
            node('Responder ao frontend','respondToWebhook',1.4,
                 {'respondWith':'json','responseBody':'={{ $json.body }}',
                  'options':{'responseCode':'={{ $json.statusCode }}','responseHeaders':{'entries':[
                      {'name':'X-Predictive-Backend','value':'n8n'}]}}},[1250,0]),
        ]
        def target(name):
            return {'node':name,'type':'main','index':0}
        workflow = {'id':'pbi-backend-'+slug,'name':'Predictive BI | '+title,'active':False,
                    'nodes':nodes,'connections':{
                        nodes[0]['name']:{'main':[[target(nodes[1]['name'])]]},
                        nodes[1]['name']:{'main':[[target(nodes[2]['name'])]]},
                        nodes[2]['name']:{'main':[[target(nodes[3]['name'])],[target(nodes[5]['name'])]]},
                        nodes[3]['name']:{'main':[[target(nodes[4]['name'])]]},
                        nodes[4]['name']:{'main':[[target(nodes[5]['name'])]]}},
                    'settings':{'executionOrder':'v1','timezone':'America/Sao_Paulo','executionTimeout':180},
                    'pinData':{},'tags':[]}
        (output/f'backend-{slug}.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2),encoding='utf-8')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-url',default='http://127.0.0.1:8101')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    print(generate(args.api_url,args.output))
