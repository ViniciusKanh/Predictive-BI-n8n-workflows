"""ETL incremental transacional, auditoria e qualidade do dataset demonstrativo."""

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import RLock
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend import db
from backend.dataset import generate
from backend.settings import DATA

PIPELINE_LOCK = RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def audited(name):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with PIPELINE_LOCK:
                run_id, start, tick = uuid4().hex, now(), time.monotonic()
                with db.connect() as con:
                    db.execute(con, '''INSERT INTO pipeline_run
                    (run_id,pipeline,status,started_at,details) VALUES (?,?,?,?,?)''',
                               (run_id, name, 'running', start, '{}'))
                try:
                    result = function(*args, **kwargs)
                    result['run_id'] = run_id
                    with db.connect() as con:
                        db.execute(con, '''UPDATE pipeline_run SET status=?,finished_at=?,
                        duration_seconds=?,details=? WHERE run_id=?''',
                                   ('success', now(), round(time.monotonic()-tick, 3),
                                    json.dumps(result, default=str, ensure_ascii=False), run_id))
                    return result
                except Exception as error:
                    with db.connect() as con:
                        db.execute(con, '''UPDATE pipeline_run SET status=?,finished_at=?,
                        duration_seconds=?,error=? WHERE run_id=?''',
                                   ('failed', now(), round(time.monotonic()-tick, 3),
                                    type(error).__name__, run_id))
                    raise
        return wrapper
    return decorator


class Order(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    order_date: str
    quantity: int = Field(gt=0)
    gross_cents: int = Field(ge=0)
    discount_cents: int = Field(ge=0)
    revenue_cents: int = Field(ge=0)
    status: str
    updated_at: str

    @model_validator(mode='after')
    def verify(self):
        datetime.fromisoformat(self.order_date)
        datetime.fromisoformat(self.updated_at)
        if self.status not in ('completed', 'cancelled'):
            raise ValueError('Status inválido')
        expected = self.gross_cents - self.discount_cents if self.status == 'completed' else 0
        if self.discount_cents > self.gross_cents or self.revenue_cents != expected:
            raise ValueError('Receita inconsistente')
        return self


@audited('ETL')
def etl():
    manifest = generate()
    customers = pd.read_csv(DATA / 'customers.csv')
    products = pd.read_csv(DATA / 'products.csv')
    orders = pd.read_csv(DATA / 'orders.csv')
    if customers.customer_id.duplicated().any() or products.product_id.duplicated().any():
        raise ValueError('Dimensão contém chave duplicada')
    duplicate_count = int(orders.order_id.duplicated().sum())
    if duplicate_count:
        raise ValueError('Pedidos duplicados na origem; carga abortada sem avançar watermark')
    valid_customers, valid_products = set(customers.customer_id), set(products.product_id)
    watermark = db.get_state('etl_watermark')
    candidates = orders
    if watermark:
        lower = (datetime.fromisoformat(watermark['updated_at']) - timedelta(days=7)).isoformat()
        candidates = orders[orders.updated_at >= lower]
    validated = []
    for record in candidates.to_dict('records'):
        order = Order.model_validate(record)
        if order.customer_id not in valid_customers or order.product_id not in valid_products:
            raise ValueError('Pedido órfão na origem')
        row = order.model_dump()
        row['row_hash'] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        validated.append(row)
    with db.connect() as con:
        # Serializa concorrência entre processos PostgreSQL, além do lock desta aplicação.
        if db.is_postgres():
            db.execute(con, 'SELECT pg_advisory_xact_lock(7142042)')
        db.many(con, '''INSERT INTO dim_customer VALUES (?,?,?,?,?) ON CONFLICT(customer_id)
        DO UPDATE SET name=excluded.name,region=excluded.region,joined_at=excluded.joined_at,
        channel=excluded.channel''', list(customers.itertuples(index=False, name=None)))
        db.many(con, '''INSERT INTO dim_product VALUES (?,?,?,?) ON CONFLICT(product_id)
        DO UPDATE SET name=excluded.name,category=excluded.category,price_cents=excluded.price_cents''',
                list(products.itertuples(index=False, name=None)))
        dates = pd.date_range(manifest['start'], manifest['end'])
        db.many(con, '''INSERT INTO dim_date VALUES (?,?,?,?,?,?)
        ON CONFLICT(date_id) DO NOTHING''',
                [(int(d.strftime('%Y%m%d')), d.date().isoformat(), d.year, d.month,
                  d.quarter, d.dayofweek) for d in dates])
        existing = {r['order_id']: r['row_hash'] for r in
                    db.execute(con, 'SELECT order_id,row_hash FROM fact_order').fetchall()}
        changed = [r for r in validated if existing.get(r['order_id']) != r['row_hash']]
        columns = ['order_id', 'customer_id', 'product_id', 'date_id', 'order_date', 'quantity',
                   'gross_cents', 'discount_cents', 'revenue_cents', 'status', 'updated_at', 'row_hash']
        for record in changed:
            record['date_id'] = int(record['order_date'].replace('-', ''))
        db.many(con, '''INSERT INTO fact_order VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(order_id) DO UPDATE SET customer_id=excluded.customer_id,
        product_id=excluded.product_id,date_id=excluded.date_id,order_date=excluded.order_date,
        quantity=excluded.quantity,gross_cents=excluded.gross_cents,discount_cents=excluded.discount_cents,
        revenue_cents=excluded.revenue_cents,status=excluded.status,
        updated_at=excluded.updated_at,row_hash=excluded.row_hash''',
                [tuple(record[c] for c in columns) for record in changed])
        last = orders.sort_values(['updated_at', 'order_id']).iloc[-1]
        checkpoint = {'updated_at': str(last.updated_at), 'order_id': int(last.order_id)}
        db.set_state('etl_watermark', checkpoint, con)
        db.set_state('manifest', manifest, con)
    return {'read': len(orders), 'validated': len(validated), 'inserted': sum(
        r['order_id'] not in existing for r in changed), 'updated': sum(
        r['order_id'] in existing for r in changed), 'unchanged': len(validated)-len(changed),
        'watermark': checkpoint, 'demonstrative': True}


@audited('Data Quality')
def quality():
    checks = []
    statements = {
        'Integridade cliente': '''SELECT COUNT(*) AS errors FROM fact_order f LEFT JOIN
        dim_customer d ON f.customer_id=d.customer_id WHERE d.customer_id IS NULL''',
        'Integridade produto': '''SELECT COUNT(*) AS errors FROM fact_order f LEFT JOIN
        dim_product d ON f.product_id=d.product_id WHERE d.product_id IS NULL''',
        'Integridade calendário': '''SELECT COUNT(*) AS errors FROM fact_order f LEFT JOIN
        dim_date d ON f.date_id=d.date_id WHERE d.date_id IS NULL''',
        'Receita e descontos': '''SELECT COUNT(*) AS errors FROM fact_order WHERE revenue_cents<0
        OR discount_cents>gross_cents OR (status='completed' AND revenue_cents<>gross_cents-discount_cents)
        OR (status='cancelled' AND revenue_cents<>0)''',
        'Pedidos únicos': '''SELECT COUNT(*)-COUNT(DISTINCT order_id) AS errors FROM fact_order''',
        'Quantidades positivas': 'SELECT COUNT(*) AS errors FROM fact_order WHERE quantity<=0',
    }
    for name, sql in statements.items():
        errors = int(db.query(sql)[0]['errors'])
        checks.append({'name': name, 'errors': errors, 'status': 'passed' if errors == 0 else 'failed'})
    raw = pd.read_csv(DATA / 'orders.csv')
    source_total = int(raw.revenue_cents.sum())
    loaded_total = int(db.query('SELECT COALESCE(SUM(revenue_cents),0) AS total FROM fact_order')[0]['total'])
    for name, errors in [('Duplicidade na origem', int(raw.order_id.duplicated().sum())),
                         ('Campos ausentes na origem', int(raw.isna().sum().sum())),
                         ('Reconciliação receita em centavos', abs(source_total-loaded_total))]:
        checks.append({'name': name, 'errors': errors, 'status': 'passed' if not errors else 'failed'})
    result = {'checks': checks, 'passed': sum(c['status']=='passed' for c in checks),
              'total': len(checks), 'checked_at': now(), 'source_revenue_cents': source_total,
              'loaded_revenue_cents': loaded_total, 'demonstrative': True,
              'freshness_note': 'Dataset histórico fixo: até 30/09/2026; não é uma fonte em tempo real.'}
    db.set_state('quality', result)
    return result
