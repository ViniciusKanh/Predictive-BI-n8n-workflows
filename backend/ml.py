"""Modelos avaliados temporalmente; nenhum atributo usa informações futuras."""

import hashlib
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score,
                             mean_absolute_error, precision_score, recall_score,
                             roc_auc_score, silhouette_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend import db
from backend.pipelines import audited, now
from backend.settings import ARTIFACTS, MLFLOW_URI

FEATURES = ['recency', 'frequency', 'monetary', 'tenure', 'avg_ticket', 'frequency_previous']


def orders():
    frame = pd.DataFrame(db.query('SELECT * FROM fact_order'))
    if frame.empty:
        raise ValueError('Execute a carga inicial antes de treinar')
    frame['date'] = pd.to_datetime(frame.order_date)
    return frame


def track(name, params, metrics, artifact):
    """Usa MLflow real quando disponível e sinaliza fallback sem fingir registro."""
    manifest = db.get_state('manifest', {})
    params = {'seed':42, 'dataset_sha256':manifest.get('sha256','unknown'),
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              **params}
    info = {'name': name, 'params': params, 'metrics': metrics, 'artifact': str(artifact),
            'artifact_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
            'recorded_at': now(), 'mlflow_status': 'pending'}
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_URI)
        mlflow.set_experiment('Predictive BI Demonstrativo')
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params(params)
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
            mlflow.log_artifact(str(artifact))
            mlflow.set_tags({'demonstrative': 'true', 'seed': '42', 'validation': 'temporal'})
            info.update(mlflow_status='registered', mlflow_run_id=run.info.run_id)
    except Exception as error:
        info['reason'] = type(error).__name__
    (ARTIFACTS / f'{name}-experiment.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return info


def calendar_features(index):
    index = pd.DatetimeIndex(index)
    t = (index - pd.Timestamp('2023-01-01')).days.to_numpy() / 365.25
    return np.column_stack([t, np.sin(2*np.pi*t), np.cos(2*np.pi*t),
                            np.sin(4*np.pi*t), np.cos(4*np.pi*t)])


def error_metrics(actual, pred):
    actual, pred = np.asarray(actual), np.asarray(pred)
    return {'mae': float(mean_absolute_error(actual, pred)),
            'rmse': float(np.sqrt(np.mean((actual-pred)**2))),
            'wape': float(np.abs(actual-pred).sum()/np.abs(actual).sum())}


def train_forecast(frame):
    daily = frame.groupby('date').revenue_cents.sum().reindex(
        pd.date_range(frame.date.min(), frame.date.max()), fill_value=0) / 100
    weekly = daily.resample('W-MON', label='left', closed='left').sum()
    sizes = daily.resample('W-MON', label='left', closed='left').count()
    weekly = weekly[sizes == 7]
    x, y = calendar_features(weekly.index), weekly.to_numpy()
    candidates = {'Ridge sazonal': Ridge(alpha=1.0),
                  'Random Forest': RandomForestRegressor(n_estimators=120, max_depth=7,
                                                         random_state=42, n_jobs=2)}
    # Validação em duas janelas anteriores ao teste final intocado.
    folds, scores = [], {}
    for name, estimator in candidates.items():
        values = []
        for end in (len(y)-16, len(y)-8):
            start = end-8
            estimator.fit(x[:start], y[:start])
            prediction = np.maximum(0, estimator.predict(x[start:end]))
            values.append(error_metrics(y[start:end], prediction)['wape'])
            folds.append({'model': name, 'train_end': str(weekly.index[start-1].date()),
                          'test_start': str(weekly.index[start].date()),
                          'test_end': str(weekly.index[end-1].date()), 'wape': values[-1]})
        scores[name] = float(np.mean(values))
    # Baseline sazonal disponível no instante de cada previsão.
    seasonal_val = []
    for end in (len(y)-16, len(y)-8):
        start = end-8
        seasonal_val.append(error_metrics(y[start:end], y[start-52:end-52])['wape'])
    scores['Baseline sazonal 52 semanas'] = float(np.mean(seasonal_val))
    selected = min(scores, key=scores.get)
    split = len(y)-8
    baseline_pred = y[split-52:len(y)-52]
    if selected in candidates:
        model = candidates[selected]
        model.fit(x[:split], y[:split])
        pred = np.maximum(0, model.predict(x[split:]))
    else:
        model = None
        pred = baseline_pred.copy()
    metrics = error_metrics(y[split:], pred)
    baseline = error_metrics(y[split:], baseline_pred)
    history = [{'date': str(d.date()), 'actual': round(float(v), 2)} for d, v in weekly.items()]
    holdout = [{'date': str(weekly.index[split+i].date()), 'actual': float(y[split+i]),
                'prediction': float(v), 'baseline': float(baseline_pred[i])} for i, v in enumerate(pred)]
    future = pd.date_range(weekly.index[-1]+pd.Timedelta(days=7), periods=8, freq='7D')
    if model is not None:
        model.fit(x, y)
        forecast = np.maximum(0, model.predict(calendar_features(future)))
    else:
        forecast = y[-52:-44]
    path = ARTIFACTS / 'revenue.joblib'
    joblib.dump({'model': model, 'selected': selected, 'last_week': weekly.index[-1],
                 'series': weekly, 'features': 'Calendário e tendência; sem atributos futuros'}, path)
    experiment = track('revenue', {'selected': selected, 'horizon_weeks': 8,
                                  'validation_folds': 2, 'test_weeks': 8}, metrics, path)
    result = {'selected': selected, 'metrics': metrics, 'baseline_metrics': baseline,
              'validation_scores': scores, 'folds': folds, 'holdout': holdout, 'history': history,
              'forecast': [{'date': str(d.date()), 'prediction': round(float(v), 2)}
                           for d, v in zip(future, forecast)], 'experiment': experiment,
              'frequency': 'Semana completa iniciada na segunda-feira',
              'interval_note': 'Sem intervalo de confiança validado; previsão pontual.',
              'trained_at': now(), 'demonstrative': True}
    db.set_state('forecast', result)
    return result


def churn_snapshot(frame, cutoff, labels=True):
    cutoff = pd.Timestamp(cutoff)
    paid = frame[frame.status == 'completed']
    past = paid[paid.date <= cutoff]
    recent = past[past.date > cutoff-pd.Timedelta(days=180)]
    previous = past[(past.date > cutoff-pd.Timedelta(days=360)) &
                    (past.date <= cutoff-pd.Timedelta(days=180))]
    lifetime = past.groupby('customer_id').agg(last=('date', 'max'), first=('date', 'min'))
    rfm = recent.groupby('customer_id').agg(frequency=('order_id', 'count'), monetary=('revenue_cents', 'sum'))
    data = lifetime.join(rfm).fillna({'frequency': 0, 'monetary': 0})
    data['recency'] = (cutoff-data['last']).dt.days
    data['tenure'] = (cutoff-data['first']).dt.days
    data['monetary'] = data.monetary/100
    data['avg_ticket'] = data.monetary / data.frequency.clip(lower=1)
    data['frequency_previous'] = previous.groupby('customer_id').size().reindex(data.index, fill_value=0)
    data['as_of'] = cutoff.date().isoformat()
    if labels:
        if cutoff+pd.Timedelta(days=90) > frame.date.max():
            raise ValueError('Rótulos ainda não amadureceram')
        future = paid[(paid.date > cutoff) & (paid.date <= cutoff+pd.Timedelta(days=90))]
        data['churn'] = (~data.index.isin(future.customer_id.unique())).astype(int)
    return data.reset_index()[['customer_id', *FEATURES, 'as_of'] + (['churn'] if labels else [])]


def classifier_metrics(actual, probability, threshold):
    pred = probability >= threshold
    return {'roc_auc': float(roc_auc_score(actual, probability)),
            'pr_auc': float(average_precision_score(actual, probability)),
            'precision': float(precision_score(actual, pred, zero_division=0)),
            'recall': float(recall_score(actual, pred, zero_division=0)),
            'f1': float(f1_score(actual, pred, zero_division=0)),
            'brier': float(brier_score_loss(actual, probability))}


def train_churn(frame):
    train = pd.concat([churn_snapshot(frame, d) for d in ('2024-06-30', '2024-12-31')])
    valid = churn_snapshot(frame, '2025-06-30')
    test = churn_snapshot(frame, '2026-03-31')
    models = {'Regressão logística': make_pipeline(StandardScaler(), LogisticRegression(
        max_iter=1000, random_state=42)),
        'Random Forest': RandomForestClassifier(n_estimators=120, max_depth=7,
                                                min_samples_leaf=8, random_state=42, n_jobs=2)}
    optional = []
    try:
        from xgboost import XGBClassifier
        models['XGBoost'] = XGBClassifier(n_estimators=120, max_depth=3, learning_rate=.05,
                                         random_state=42, n_jobs=2, eval_metric='logloss')
    except ImportError:
        optional.append('XGBoost indisponível; mantidos dois classificadores scikit-learn.')
    evaluated = []
    for name, model in models.items():
        model.fit(train[FEATURES], train.churn)
        prob = model.predict_proba(valid[FEATURES])[:, 1]
        threshold = max(np.arange(.15, .86, .05), key=lambda t: f1_score(valid.churn, prob>=t))
        val_metrics = classifier_metrics(valid.churn, prob, threshold)
        test_metrics = classifier_metrics(test.churn, model.predict_proba(test[FEATURES])[:, 1], threshold)
        path = ARTIFACTS / f'churn-{len(evaluated)}.joblib'
        joblib.dump(model, path)
        experiment = track(f'churn-{len(evaluated)}', {'model': name, 'threshold': float(threshold),
                           'train_end': '2024-12-31', 'validation': '2025-06-30',
                           'test': '2026-03-31', 'horizon_days': 90}, test_metrics, path)
        evaluated.append({'name': name, 'validation': val_metrics, 'test': test_metrics,
                          'threshold': float(threshold), 'experiment': experiment})
    best = max(evaluated, key=lambda item: item['validation']['pr_auc'])
    chosen = models[best['name']]
    explanation = {'method': 'indisponível', 'features': []}
    try:
        import shap
        tree = models.get('XGBoost', models['Random Forest'])
        sample = test[FEATURES].head(128)
        shap_values = np.asarray(shap.TreeExplainer(tree).shap_values(sample))
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 1]
        impacts = np.abs(shap_values).mean(axis=0)
        explanation = {'method': 'SHAP TreeExplainer', 'explained_model':
                       'XGBoost' if 'XGBoost' in models else 'Random Forest',
                       'sample_size': len(sample), 'features': sorted(
                           [{'feature': f, 'importance': float(v)} for f, v in zip(FEATURES, impacts)],
                           key=lambda item: -item['importance'])}
    except Exception as error:
        optional.append('SHAP: ' + type(error).__name__)
    # Reajuste para servir após avaliação; o teste permanece registrado para o modelo anterior.
    chosen.fit(pd.concat([train, valid, test])[FEATURES], pd.concat([train, valid, test]).churn)
    joblib.dump({'model': chosen, 'features': FEATURES, 'threshold': best['threshold']},
                ARTIFACTS / 'churn-serving.joblib')
    current = churn_snapshot(frame, frame.date.max(), labels=False)
    current['risk'] = chosen.predict_proba(current[FEATURES])[:, 1]
    current['high_risk'] = current.risk >= best['threshold']
    names = pd.DataFrame(db.query('SELECT customer_id,name,region FROM dim_customer'))
    current = current.merge(names, on='customer_id')
    records = current.sort_values('risk', ascending=False).to_dict('records')
    prevalence = float(train.churn.mean())
    baseline = classifier_metrics(test.churn, np.full(len(test), prevalence), .5)
    result = {'selected': best['name'], 'models': evaluated, 'threshold': best['threshold'],
              'customers': records, 'high_risk': int(current.high_risk.sum()),
              'population': len(current), 'baseline': baseline, 'explanation': explanation,
              'snapshots': {'train': ['2024-06-30', '2024-12-31'], 'validation': '2025-06-30',
                            'test': '2026-03-31', 'inference': str(frame.date.max().date()),
                            'label': 'Sem compra concluída nos 90 dias seguintes'},
              'optional_notes': optional, 'trained_at': now(), 'demonstrative': True}
    db.set_state('churn', result)
    return result


def train_segments(frame):
    snapshot = churn_snapshot(frame, frame.date.max(), labels=False)
    x = np.log1p(snapshot[['recency', 'frequency', 'monetary']])
    scaler = StandardScaler().fit(x)
    normalized = scaler.transform(x)
    comparisons, fitted = [], {}
    for k in (3, 4, 5):
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        clusters = model.fit_predict(normalized)
        score = float(silhouette_score(normalized, clusters, sample_size=min(1000, len(x)), random_state=42))
        comparisons.append({'k': k, 'silhouette': score})
        fitted[k] = model
    best = max(comparisons, key=lambda row: row['silhouette'])
    model = fitted[best['k']]
    snapshot['cluster'] = model.labels_.astype(int)
    names = pd.DataFrame(db.query('SELECT customer_id,name,region FROM dim_customer'))
    snapshot = snapshot.merge(names, on='customer_id')
    groups = snapshot.groupby('cluster').agg(customers=('customer_id', 'count'),
        recency=('recency', 'mean'), frequency=('frequency', 'mean'), monetary=('monetary', 'mean'))
    groups['share'] = groups.customers / len(snapshot)
    summaries = []
    for cluster, row in groups.iterrows():
        profile = 'Inativos' if row.recency > 180 else ('Recorrentes' if row.frequency > groups.frequency.median()
                                                       else 'Ocasionais')
        summaries.append({'cluster': int(cluster), 'name': f'{profile} · {int(cluster)+1}',
                          **row.to_dict()})
    path = ARTIFACTS / 'segmentation.joblib'
    joblib.dump({'model': model, 'scaler': scaler}, path)
    experiment = track('segmentation', {'k': best['k'], 'transform': 'log1p + StandardScaler'},
                       {'silhouette': best['silhouette']}, path)
    result = {'clusters': summaries, 'customers': snapshot.to_dict('records'),
              'comparison': comparisons, 'silhouette': best['silhouette'], 'experiment': experiment,
              'as_of': str(frame.date.max().date()), 'trained_at': now(), 'demonstrative': True}
    db.set_state('segments', result)
    return result


@audited('Predictive Analytics')
def train_all():
    frame = orders()
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes()).hexdigest()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=FutureWarning)
        forecast = train_forecast(frame)
        churn = train_churn(frame)
        segments = train_segments(frame)
    result = {'fingerprint': fingerprint, 'orders': len(frame), 'forecast': forecast['metrics'],
              'churn': next(m['test'] for m in churn['models'] if m['name']==churn['selected']),
              'silhouette': segments['silhouette'], 'trained_at': now(),
              'tracking': forecast['experiment']['mlflow_status']}
    db.set_state('models', result)
    return result


@audited('Inference')
def infer():
    artifact = joblib.load(ARTIFACTS / 'revenue.joblib')
    model, series = artifact['model'], artifact['series']
    dates = pd.date_range(series.index[-1]+pd.Timedelta(days=7), periods=8, freq='7D')
    values = np.maximum(0, model.predict(calendar_features(dates))) if model is not None else series.to_numpy()[-52:-44]
    result = {'model': artifact['selected'], 'forecast': [{'date': str(d.date()), 'prediction': round(float(v), 2)}
                                                        for d, v in zip(dates, values)],
              'inferred_at': now(), 'demonstrative': True}
    db.set_state('inference', result)
    forecast = db.get_state('forecast', {})
    if forecast:
        forecast.update(forecast=result['forecast'], inferred_at=result['inferred_at'])
        db.set_state('forecast', forecast)
    return result
