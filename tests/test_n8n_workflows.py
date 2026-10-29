"""Contratos dos workflows n8n locais; não substituem execução no motor n8n."""

import json

from scripts.generate_workflows import generate


def test_local_workflows_address_the_selected_api_and_have_no_credentials(tmp_path):
    output = generate('http://127.0.0.1:8101', tmp_path, include_master=True)
    files = list(output.glob('*.json'))
    assert len(files) == 5
    identities = []
    for path in files:
        workflow = json.loads(path.read_text(encoding='utf-8'))
        identities.append(workflow['id'])
        assert workflow['active'] is False
        names = {node['name'] for node in workflow['nodes']}
        assert len(names) == len(workflow['nodes'])
        for node in workflow['nodes']:
            assert 'credentials' not in node
            if node['type'] == 'n8n-nodes-base.httpRequest':
                assert 'http://127.0.0.1:8101/api/jobs' in node['parameters']['url']
                if node['parameters'].get('method') == 'POST':
                    assert node['parameters']['headerParameters']['parameters'][0]['name'] == 'Idempotency-Key'
        for source, connections in workflow['connections'].items():
            assert source in names
            assert all(target['node'] in names for branch in connections['main'] for target in branch)
    assert len(set(identities)) == 5


def test_master_blocks_training_when_quality_is_not_approved(tmp_path):
    generate('http://127.0.0.1:8101', tmp_path, include_master=True)
    workflow = json.loads((tmp_path/'complete.json').read_text(encoding='utf-8'))
    nodes = {node['name']:node for node in workflow['nodes']}
    submissions = sorted([node for node in nodes.values()
                          if node['parameters'].get('method') == 'POST'], key=lambda node:node['position'][0])
    assert [json.loads(node['parameters']['jsonBody'])['pipeline'] for node in submissions] == [
        'etl','quality','train','infer','insights']
    gate = nodes['Qualidade aprovada?']
    assert gate['type'] == 'n8n-nodes-base.if'
    branches = workflow['connections'][gate['name']]['main']
    success = nodes[branches[0][0]['node']]
    failure = nodes[branches[1][0]['node']]
    assert json.loads(success['parameters']['jsonBody'])['pipeline'] == 'train'
    assert failure['type'] == 'n8n-nodes-base.stopAndError'
    assert workflow['settings']['executionTimeout'] >= 5*600


def test_regenerating_local_workflows_preserves_identifiers(tmp_path):
    generate('http://127.0.0.1:8101', tmp_path, include_master=True)
    before = json.loads((tmp_path/'complete.json').read_text(encoding='utf-8'))
    generate('http://127.0.0.1:8102', tmp_path, include_master=True)
    after = json.loads((tmp_path/'complete.json').read_text(encoding='utf-8'))
    assert before['id'] == after['id']
    assert {node['id'] for node in before['nodes']} == {node['id'] for node in after['nodes']}
