"""Indicadores derivados exclusivamente do banco demonstrativo."""

import pandas as pd

from backend import db


def analytics(start=None, end=None, category=None, region=None):
    conditions, params = [], []
    for value, clause in [(start, 'f.order_date>=?'), (end, 'f.order_date<=?'),
                          (category, 'p.category=?'), (region, 'c.region=?')]:
        if value:
            conditions.append(clause)
            params.append(value)
    sql = '''SELECT f.*,c.name AS customer,c.region,c.channel,p.name AS product,p.category
    FROM fact_order f JOIN dim_customer c ON f.customer_id=c.customer_id
    JOIN dim_product p ON f.product_id=p.product_id'''
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    data = pd.DataFrame(db.query(sql, tuple(params)))
    if data.empty:
        return {'empty': True, 'demonstrative': True, 'kpis': {}, 'monthly': [], 'daily': [],
                'categories': [], 'regions': [], 'products': [], 'channels': [], 'heatmap': [], 'orders': []}
    data['revenue'] = data.revenue_cents/100
    data['date'] = pd.to_datetime(data.order_date)
    data['month'] = data.date.dt.to_period('M').astype(str)
    monthly = data.groupby('month').agg(revenue=('revenue', 'sum'), orders=('order_id', 'count'),
                                       customers=('customer_id', 'nunique')).reset_index()
    monthly['ticket'] = monthly.revenue / monthly.orders
    latest, before = monthly.iloc[-1], monthly.iloc[-2] if len(monthly)>1 else None
    growth = float((latest.revenue / before.revenue - 1)*100) if before is not None and before.revenue else None
    paid = data[data.status == 'completed']
    repeat = paid.groupby('customer_id').size()
    kpis = {'revenue': float(data.revenue.sum()), 'orders': len(data),
            'customers': int(data.customer_id.nunique()),
            'ticket': float(paid.revenue.mean()) if len(paid) else 0,
            'cancel_rate': float((data.status=='cancelled').mean()*100),
            'repeat_rate': float((repeat>1).mean()*100) if len(repeat) else 0,
            'monthly_growth': growth, 'latest_month': str(latest.month),
            'latest_month_revenue': float(latest.revenue),
            'start': str(data.order_date.min()), 'end': str(data.order_date.max()),
            'completed_orders': len(paid)}
    def aggregate(column):
        grouped = data.groupby(column).agg(revenue=('revenue','sum'), orders=('order_id','count'))
        return grouped.sort_values('revenue',ascending=False).reset_index().rename(columns={column:'name'}).to_dict('records')
    daily = data.groupby('order_date').agg(revenue=('revenue','sum'),orders=('order_id','count')).reset_index()
    data['weekday'] = data.date.dt.dayofweek
    heat = data.groupby(['month','weekday']).revenue.sum().reset_index()
    sample = data.sort_values(['order_date','order_id'],ascending=False).head(2000)
    return {'empty': False, 'demonstrative': True, 'kpis': kpis,
            'monthly': monthly.to_dict('records'), 'daily': daily.to_dict('records'),
            'categories': aggregate('category'), 'regions': aggregate('region'),
            'products': aggregate('product'), 'channels': aggregate('channel'),
            'heatmap': heat.to_dict('records'),
            'orders': sample[['order_id','order_date','customer','region','product','category',
                              'quantity','revenue','status']].to_dict('records'),
            'table_limit': 2000, 'filters': {'start': start,'end': end,'category': category,'region': region}}
