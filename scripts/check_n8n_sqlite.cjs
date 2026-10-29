// Verifica o mesmo driver carregado pelo TypeORM do n8n, sem tocar em bancos existentes.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

function failure(code, error) {
  console.log(JSON.stringify({ status: 'error', code, detail: String(error.message || error).split('\n')[0] }));
  process.exitCode = 1;
}

async function check(toolRoot) {
  const anchor = path.join(path.resolve(toolRoot), 'node_modules', 'n8n', 'package.json');
  if (!fs.existsSync(anchor)) {
    failure('N8N_NOT_INSTALLED', 'O pacote n8n não foi encontrado nessa instalação.');
    return;
  }
  let sqlite;
  try {
    const n8nRequire = createRequire(anchor);
    const typeormRequire = createRequire(n8nRequire.resolve('@n8n/typeorm'));
    sqlite = typeormRequire('sqlite3');
  } catch (error) {
    const nativeMissing = /bindings file|node_sqlite3|NODE_MODULE_VERSION|ERR_DLOPEN_FAILED/i.test(String(error.stack));
    failure(nativeMissing ? 'NATIVE_BINDING_UNAVAILABLE' : 'DRIVER_UNAVAILABLE', error);
    return;
  }
  let database;
  try {
    database = await new Promise((resolve, reject) => {
      const connection = new sqlite.Database(':memory:', error => error ? reject(error) : resolve(connection));
    });
    const row = await new Promise((resolve, reject) => {
      database.get('SELECT 1 AS ok', (error, value) => error ? reject(error) : resolve(value));
    });
    if (row?.ok !== 1) throw new Error('Resultado inesperado na consulta de verificação.');
    console.log(JSON.stringify({ status: 'ok', sqlite_version: sqlite.VERSION, query: 'SELECT 1 AS ok' }));
  } catch (error) {
    failure('SQLITE_QUERY_FAILED', error);
  } finally {
    if (database) {
      await new Promise(resolve => database.close(error => {
        if (error) failure('SQLITE_CLOSE_FAILED', error);
        resolve();
      }));
    }
  }
}

check(process.argv[2] || path.join(__dirname, '..', '.runtime', 'n8n-tool')).catch(error => failure('CHECK_FAILED', error));
