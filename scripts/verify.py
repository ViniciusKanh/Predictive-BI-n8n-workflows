"""Consolida evidências sem confundir testes ASGI com acesso HTTP por rede."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from fastapi.testclient import TestClient
    from backend import db
    from backend.main import app
    from backend.runtime_loop import create_loop
    from backend.pipelines import now
    client = TestClient(app, backend_options={'loop_factory': create_loop})
    paths = ['/health','/api/analytics','/api/models','/api/quality','/api/pipelines',
             '/api/insights','/api/status','/docs','/openapi.json','/']
    endpoints = {path:client.get(path).status_code for path in paths}
    test_report = ROOT/'artifacts/test-results.xml'
    tests = {}
    if test_report.exists():
        suites = ET.parse(test_report).getroot()
        for key in ('tests','failures','errors','skipped'):
            tests[key] = sum(int(suite.attrib.get(key,0)) for suite in suites.iter('testsuite'))
    model = db.get_state('models', {})
    forecast = db.get_state('forecast', {})
    churn = db.get_state('churn', {})
    segments = db.get_state('segments', {})
    experiments = [forecast.get('experiment',{}),segments.get('experiment',{})]
    experiments.extend(item.get('experiment',{}) for item in churn.get('models',[]))
    result = {'verified_at':now(),'transport':'ASGI em processo, sem TCP',
              'endpoints':endpoints,'tests':tests,'database':client.get('/health').json(),
              'quality':db.get_state('quality',{}),'models':model,
              'forecast_baseline':db.get_state('forecast',{}).get('baseline_metrics'),
              'insight_mode':db.get_state('insights',{}).get('mode'),
              'workflows':len(list((ROOT/'workflows').glob('*.json'))),
              'build_present':(ROOT/'frontend/dist/index.html').exists(),
              'browser_verified':False,'compose_runtime_verified':False,
              'mlflow_registered':all(item.get('mlflow_status')=='registered' for item in experiments)}
    (ROOT/'artifacts/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if any(code!=200 for code in endpoints.values()):
        raise SystemExit(1)


if __name__=='__main__':
    main()
