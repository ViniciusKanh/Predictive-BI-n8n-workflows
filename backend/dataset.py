"""Geração determinística: comércio inteiramente fictício, sem dados pessoais reais."""

import hashlib
import json

import numpy as np
import pandas as pd

from backend.settings import DATA

SEED = 42
START = '2023-01-01'
END = '2026-09-30'


def generate():
    manifest = DATA / 'manifest.json'
    if manifest.exists():
        return json.loads(manifest.read_text(encoding='utf-8'))
    rng = np.random.default_rng(SEED)
    dates = pd.date_range(START, END)
    count = 1200
    joined = rng.integers(0, 650, count)
    joined[:200] = 0
    # Propensão latente usada apenas pelo gerador, nunca entregue como atributo ao ML.
    propensity = rng.lognormal(0, .75, count)
    stop = np.where(rng.random(count) < .45, joined + rng.integers(250, 1050, count), 9999)
    regions = np.array(['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'])
    customers = pd.DataFrame({
        'customer_id': np.arange(1, count + 1),
        'name': [f'Cliente Demo {i:04d}' for i in range(1, count + 1)],
        'region': rng.choice(regions, count, p=[.43, .23, .18, .10, .06]),
        'joined_at': [(dates[0] + pd.Timedelta(days=int(j))).date().isoformat() for j in joined],
        'channel': rng.choice(['E-commerce', 'Consultivo', 'Parceiros'], count, p=[.55, .30, .15]),
    })
    categories = ['Tecnologia', 'Escritório', 'Casa', 'Acessórios', 'Equipamentos']
    products = pd.DataFrame({
        'product_id': np.arange(1, 61),
        'name': [f'{categories[i % 5]} {i+1:02d}' for i in range(60)],
        'category': [categories[i % 5] for i in range(60)],
        'price_cents': rng.integers(4500, 180000, 60),
    })
    orders = []
    for day, date in enumerate(dates):
        seasonal = 1 + .28 * np.cos(2 * np.pi * (date.dayofyear - 325) / 365.25)
        weekly = 1.15 if date.dayofweek < 5 else .65
        amount = rng.poisson(27 * seasonal * weekly * (1 + .00045 * day))
        active = (joined <= day) & (stop > day)
        weights = propensity * active
        buyers = rng.choice(count, amount, p=weights / weights.sum())
        for buyer in buyers:
            product = int(rng.integers(0, 60))
            qty = int(rng.choice([1, 2, 3, 4], p=[.63, .25, .09, .03]))
            gross = int(products.iloc[product].price_cents) * qty
            discount = int(round(gross * float(rng.choice([0, .05, .10, .15], p=[.5, .25, .2, .05]))))
            status = 'cancelled' if rng.random() < .035 else 'completed'
            orders.append((len(orders) + 1, int(buyer) + 1, product + 1, date.date().isoformat(),
                           qty, gross, discount, gross - discount if status == 'completed' else 0,
                           status, date.isoformat()))
    frame = pd.DataFrame(orders, columns=['order_id', 'customer_id', 'product_id', 'order_date',
        'quantity', 'gross_cents', 'discount_cents', 'revenue_cents', 'status', 'updated_at'])
    assert len(frame) >= 10000
    for name, data in [('customers', customers), ('products', products), ('orders', frame)]:
        data.to_csv(DATA / f'{name}.csv', index=False, encoding='utf-8')
    info = {'demonstrative': True, 'seed': SEED, 'start': START, 'end': END,
            'orders': len(frame), 'customers': count, 'products': 60,
            'grain': 'Um pedido contém um produto; receita líquida por competência em BRL.',
            'sha256': hashlib.sha256((DATA / 'orders.csv').read_bytes()).hexdigest()}
    manifest.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    return info
