"""Transações PostgreSQL; SQLite explícito para testes e operação degradada."""

import json
import sqlite3
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from backend import settings


def is_postgres():
    return settings.DATABASE_URL.startswith('postgresql')


@contextmanager
def connect():
    if is_postgres():
        con = psycopg.connect(settings.DATABASE_URL.replace('postgresql+psycopg:', 'postgresql:'),
                               row_factory=dict_row, connect_timeout=5)
    else:
        path = settings.DATABASE_URL.removeprefix('sqlite:///')
        con = sqlite3.connect(path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def execute(con, sql, params=()):
    return con.execute(sql.replace('?', '%s') if is_postgres() else sql, params)


def many(con, sql, rows):
    with con.cursor() if is_postgres() else _sqlite_cursor(con) as cur:
        cur.executemany(sql.replace('?', '%s') if is_postgres() else sql, rows)


@contextmanager
def _sqlite_cursor(con):
    yield con.cursor()


def query(sql, params=()):
    with connect() as con:
        return [dict(row) for row in execute(con, sql, params).fetchall()]


def init_db():
    statements = [
        '''CREATE TABLE IF NOT EXISTS dim_customer (
        customer_id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL,
        joined_at TEXT NOT NULL, channel TEXT NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS dim_product (
        product_id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
        price_cents INTEGER NOT NULL CHECK(price_cents>0))''',
        '''CREATE TABLE IF NOT EXISTS dim_date (
        date_id INTEGER PRIMARY KEY, date TEXT NOT NULL UNIQUE, year INTEGER,
        month INTEGER, quarter INTEGER, weekday INTEGER)''',
        '''CREATE TABLE IF NOT EXISTS fact_order (
        order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES dim_customer(customer_id),
        product_id INTEGER NOT NULL REFERENCES dim_product(product_id),
        date_id INTEGER NOT NULL REFERENCES dim_date(date_id), order_date TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity>0), gross_cents BIGINT NOT NULL CHECK(gross_cents>=0),
        discount_cents BIGINT NOT NULL CHECK(discount_cents>=0),
        revenue_cents BIGINT NOT NULL CHECK(revenue_cents>=0), status TEXT NOT NULL,
        updated_at TEXT NOT NULL, row_hash TEXT NOT NULL)''',
        'CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_order(order_date)',
        'CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_order(customer_id,order_date)',
        '''CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY, value TEXT NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS pipeline_run (
        run_id TEXT PRIMARY KEY, pipeline TEXT NOT NULL, status TEXT NOT NULL,
        started_at TEXT NOT NULL, finished_at TEXT, duration_seconds DOUBLE PRECISION,
        details TEXT NOT NULL, error TEXT)''',
    ]
    with connect() as con:
        for statement in statements:
            execute(con, statement)


def set_state(key, value, con=None):
    sql = '''INSERT INTO app_state(key,value) VALUES (?,?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value'''
    if con is not None:
        execute(con, sql, (key, json.dumps(value, ensure_ascii=False, default=str)))
    else:
        with connect() as connection:
            execute(connection, sql, (key, json.dumps(value, ensure_ascii=False, default=str)))


def get_state(key, default=None):
    result = query('SELECT value FROM app_state WHERE key=?', (key,))
    return json.loads(result[0]['value']) if result else default
