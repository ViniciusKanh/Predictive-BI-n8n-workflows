"""Gera quatro workflows reais com polling limitado, erros explícitos e idempotência."""

import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]


def generate(base_url='http://api:8000', output=None, include_master=False):
    output = output or ROOT/'workflows'
    output.mkdir(parents=True, exist_ok=True)
    configs = [('etl','ETL',['etl','quality'],2),
               ('predictive','Predictive Analytics',['train','infer'],3),
               ('insights','GenAI Insights',['insights'],4),
               ('quality','Data Quality',['quality'],5)]
    if include_master:
        configs.append(('complete','Fluxo completo',['etl','quality','train','infer','insights'],2))
    for slug, title, stages, hour in configs:
        nodes, connections = [], {}
        def node(name, kind, version, parameters, x, y=0, **kwargs):
            nodes.append({'id':str(uuid5(NAMESPACE_URL, slug+name)), 'name':name,
                          'type':'n8n-nodes-base.'+kind, 'typeVersion':version,
                          'position':[x,y], 'parameters':parameters, **kwargs})
        def edge(source, target, output_index=0):
            outputs = connections.setdefault(source, {'main':[]})['main']
            while len(outputs) <= output_index:
                outputs.append([])
            outputs[output_index].append({'node':target,'type':'main','index':0})
        node('Executar manualmente','manualTrigger',1,{},0)
        node('Agendamento diário','scheduleTrigger',1.2,
             {'rule':{'interval':[{'field':'days','daysInterval':1,'triggerAtHour':hour,'triggerAtMinute':0}]}},0,160)
        previous = ['Executar manualmente','Agendamento diário']
        for index, stage in enumerate(stages):
            x = 260+index*1300
            submit, wait, poll, success, failed, stop = [f'{name} {stage}' for name in
                ['Disparar','Aguardar','Consultar','Concluído?','Falhou ou expirou?','Registrar falha']]
            node(submit,'httpRequest',4.2,{'method':'POST','url':base_url+'/api/jobs',
                'sendHeaders':True,'headerParameters':{'parameters':[{'name':'Idempotency-Key',
                    'value':"={{ 'n8n-' + $execution.id + '-"+stage+"' }}"}]},
                'sendBody':True,'specifyBody':'json','jsonBody':json.dumps({'pipeline':stage}),
                'options':{'timeout':30000}},x,retryOnFail=True,maxTries=3,waitBetweenTries=2000)
            for prior in previous:
                edge(prior,submit)
            node(wait,'wait',1.1,{'amount':2,'unit':'seconds'},x+220)
            edge(submit,wait)
            node(poll,'httpRequest',4.2,{'url':"={{ '"+base_url+"/api/jobs/' + $node['"+submit+"'].json.id }}",
                'options':{'timeout':30000}},x+440,retryOnFail=True,maxTries=3,waitBetweenTries=2000)
            edge(wait,poll)
            def conditions(expression):
                return {'conditions':{'options':{'caseSensitive':True,'typeValidation':'strict','version':2},
                    'conditions':[{'id':str(uuid5(NAMESPACE_URL, slug+expression)),
                    'leftValue':expression,'rightValue':True,
                    'operator':{'type':'boolean','operation':'true','singleValue':True}}],
                    'combinator':'and'},'options':{}}
            node(success,'if',2.2,conditions("={{ $json.status === 'success' }}"),x+650)
            edge(poll,success)
            timeout_expr = "={{ $json.status === 'failed' || (Date.now() - Date.parse($node['"+submit+"'].json.queued_at)) > 600000 }}"
            node(failed,'if',2.2,conditions(timeout_expr),x+870,160)
            edge(success,failed,1)
            node(stop,'stopAndError',1,{'errorMessage':'Pipeline falhou ou excedeu 10 minutos; consulte o histórico da API.'},x+1080,200)
            edge(failed,stop,0)
            edge(failed,wait,1)
            previous = [success]
            if stage == 'quality':
                gate = 'Qualidade aprovada?'
                node(gate,'if',2.2,conditions("={{ $json.result.total > 0 && $json.result.passed === $json.result.total }}"),x+900,-100)
                edge(success,gate,0)
                edge(gate,stop,1)
                previous = [gate]
        workflow = {'id':'pbi-'+slug, 'name':'Predictive BI | '+title, 'active':False,
                    'nodes':nodes,'connections':connections,
                    'settings':{'executionOrder':'v1','timezone':'America/Sao_Paulo','executionTimeout':3600 if include_master and slug=='complete' else 1200},
                    'pinData':{}, 'tags':[]}
        (output/f'{slug}.json').write_text(json.dumps(workflow, ensure_ascii=False,indent=2),encoding='utf-8')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://api:8000')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--include-master',action='store_true')
    args=parser.parse_args()
    print(generate(args.base_url,args.output,args.include_master))
