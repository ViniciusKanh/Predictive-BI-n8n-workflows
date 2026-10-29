"""Carga, avaliação e inferência reais; fallback local explícito quando a rede é bloqueada."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=['all','etl','train','infer','quality','insights'], default='all')
    parser.add_argument('--allow-sqlite-fallback', action='store_true')
    parser.add_argument('--database-mode', choices=['configured','existing','sqlite'], default='configured')
    args = parser.parse_args()
    from dotenv import dotenv_values
    import psycopg
    config = dotenv_values(ROOT / '.env')
    database = os.getenv('DATABASE_URL', config.get('DATABASE_URL', ''))
    local = ROOT / '.runtime' / 'local.env'
    if args.database_mode == 'existing' and local.exists():
        database = dotenv_values(local).get('DATABASE_URL') or database
    elif args.database_mode == 'sqlite':
        database = 'sqlite:///' + str(ROOT / 'data' / 'demo.db')
    if database.startswith('postgresql'):
        try:
            url = database.replace('postgresql+psycopg:', 'postgresql:')
            admin = url.rsplit('/',1)[0]+'/postgres'
            with psycopg.connect(admin, autocommit=True, connect_timeout=3) as con:
                if not con.execute("SELECT 1 FROM pg_database WHERE datname='predictive_bi'").fetchone():
                    con.execute('CREATE DATABASE predictive_bi')
            with psycopg.connect(url, connect_timeout=3):
                pass
        except Exception as error:
            if not args.allow_sqlite_fallback:
                raise RuntimeError('PostgreSQL inacessível; fallback precisa ser habilitado explicitamente.') from error
            database = 'sqlite:///' + str(ROOT / 'data' / 'demo.db')
            print('Modo degradado explícito: SQLite; PostgreSQL bloqueado: '+type(error).__name__, flush=True)
    if not database:
        raise RuntimeError('Configure DATABASE_URL no .env')
    os.environ['DATABASE_URL'] = database
    if os.getenv('PBI_CONTAINER') != '1':
        (ROOT / '.runtime').mkdir(exist_ok=True)
        (ROOT / '.runtime' / 'local.env').write_text('DATABASE_URL='+database+'\n', encoding='utf-8')
    from backend import db
    from backend.insights import generate_insights
    from backend.ml import infer, train_all
    from backend.pipelines import etl, quality
    db.init_db()
    tasks = {'etl':etl, 'quality':quality, 'train':train_all, 'infer':infer, 'insights':generate_insights}
    report = {'database':'PostgreSQL' if db.is_postgres() else 'SQLite (modo degradado)', 'results':{}}
    names = ['etl','quality','train','infer','insights'] if args.task == 'all' else [args.task]
    for name in names:
        print('Executando: '+name, flush=True)
        result = tasks[name]()
        report['results'][name] = result
        print(json.dumps(result if name not in ('insights',) else {'mode':result['mode']},
                         ensure_ascii=False, default=str), flush=True)
    report_file = 'bootstrap-report.json' if args.task == 'all' else f'operation-{args.task}.json'
    (ROOT / 'artifacts' / report_file).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


if __name__ == '__main__':
    main()
