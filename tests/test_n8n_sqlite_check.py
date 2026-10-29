"""Verifica diagnóstico do preflight; drivers simulados não contam como integração nativa."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / 'scripts/check_n8n_sqlite.cjs'


def run_check(root):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js indisponível para testar o preflight do n8n')
    return subprocess.run([node, str(CHECKER), str(root)], capture_output=True, text=True,
                          encoding='utf-8', timeout=10)


def driver_fixture(root, implementation):
    # Modela a resolução: o SQLite usado pelo TypeORM pode estar aninhado.
    modules = root/'node_modules'
    (modules/'n8n').mkdir(parents=True)
    (modules/'n8n/package.json').write_text('{"name":"n8n"}', encoding='utf-8')
    driver_root = modules/'@n8n/typeorm'
    driver_root.mkdir(parents=True)
    (driver_root/'package.json').write_text('{"name":"@n8n/typeorm"}', encoding='utf-8')
    (driver_root/'index.js').write_text('// Ponto de entrada para a resolução do pacote.', encoding='utf-8')
    sqlite = driver_root/'node_modules/sqlite3'
    sqlite.mkdir(parents=True)
    (sqlite/'index.js').write_text(implementation, encoding='utf-8')


def test_checker_reports_missing_install_without_claiming_success(tmp_path):
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert json.loads(result.stdout)['code'] == 'N8N_NOT_INSTALLED'


def test_checker_detects_package_present_but_native_binary_missing(tmp_path):
    driver_fixture(tmp_path, "throw new Error('Could not locate the bindings file: node_sqlite3.node');")
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert json.loads(result.stdout)['code'] == 'NATIVE_BINDING_UNAVAILABLE'


def test_checker_queries_the_driver_visible_to_typeorm(tmp_path):
    driver_fixture(tmp_path, """
    exports.VERSION = 'test-double';
    exports.Database = class {
      constructor(name, callback) {
        if (name !== ':memory:') throw new Error('Teste não pode tocar em disco');
        setImmediate(() => callback(null));
      }
      get(sql, callback) { setImmediate(() => callback(null, {ok: 1})); }
      close(callback) { setImmediate(() => callback(null)); }
    };
    """)
    result = run_check(tmp_path)
    assert result.returncode == 0
    assert json.loads(result.stdout)['status'] == 'ok'


def test_checker_does_not_approve_driver_that_fails_query(tmp_path):
    driver_fixture(tmp_path, """
    exports.Database = class {
      constructor(name, callback) { setImmediate(() => callback(null)); }
      get(sql, callback) { setImmediate(() => callback(new Error('SQLITE_CANTOPEN'))); }
      close(callback) { setImmediate(() => callback(null)); }
    };
    """)
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert json.loads(result.stdout)['code'] == 'SQLITE_QUERY_FAILED'
