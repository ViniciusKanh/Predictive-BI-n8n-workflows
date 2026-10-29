export interface Order { order_id:number; order_date:string; customer:string; region:string; product:string; category:string; quantity:number; revenue:number; status:string }
export interface Aggregate { name:string; revenue:number; orders:number }
export interface Monthly { month:string; revenue:number; orders:number; customers:number; ticket:number }
export interface KPI { revenue:number; orders:number; customers:number; ticket:number; cancel_rate:number; repeat_rate:number; monthly_growth:number|null; latest_month:string; latest_month_revenue:number; start:string; end:string; completed_orders:number }
export interface Analytics { empty:boolean; kpis:KPI; monthly:Monthly[]; daily:{order_date:string;revenue:number;orders:number}[]; categories:Aggregate[]; regions:Aggregate[]; products:Aggregate[]; channels:Aggregate[]; heatmap:{month:string;weekday:number;revenue:number}[]; orders:Order[]; table_limit:number }
export interface RegressionMetrics { mae:number; rmse:number; wape:number }
export interface ClassMetrics { roc_auc:number; pr_auc:number; precision:number; recall:number; f1:number; brier:number }
export interface Experiment { mlflow_status:string; mlflow_run_id?:string; reason?:string }
export interface Forecast { selected:string; metrics:RegressionMetrics; baseline_metrics:RegressionMetrics; history:{date:string;actual:number}[]; forecast:{date:string;prediction:number}[]; holdout:{date:string;actual:number;prediction:number;baseline:number}[]; folds:{model:string;train_end:string;test_start:string;test_end:string;wape:number}[]; trained_at:string; experiment:Experiment; interval_note:string }
export interface Customer { customer_id:number; name:string; region:string; recency:number; frequency:number; monetary:number; risk?:number; high_risk?:boolean; cluster?:number }
export interface Churn { selected:string; models:{name:string;test:ClassMetrics;validation:ClassMetrics;threshold:number;experiment:Experiment}[]; threshold:number; customers:Customer[]; high_risk:number; population:number; explanation:{method:string;explained_model?:string;sample_size?:number;features:{feature:string;importance:number}[]}; snapshots:{train:string[];validation:string;test:string;inference:string;label:string}; optional_notes:string[] }
export interface Cluster { cluster:number; name:string; customers:number; recency:number; frequency:number; monetary:number; share:number }
export interface Segments { clusters:Cluster[];customers:Customer[];comparison:{k:number;silhouette:number}[];silhouette:number;as_of:string;experiment:Experiment }
export interface Models { forecast:Forecast; churn:Churn; segments:Segments; models:{tracking:string;trained_at:string}; inference:{inferred_at:string} }
export interface Quality { checks:{name:string;errors:number;status:string}[];passed:number;total:number;checked_at:string;freshness_note:string;source_revenue_cents:number;loaded_revenue_cents:number }
export interface Run { run_id:string;pipeline:string;status:string;started_at:string;finished_at:string;duration_seconds:number;details:Record<string,unknown>;error:string|null }
export interface Insight { mode:string;model:string|null;generated_at:string;limitation:string|null;question:string;findings:{metric_id:string;title:string;text:string;recommendation:string;evidence:{source:string;period:string[];value:number;unit:string}}[];run_id?:string }
export interface Status { database:string;ollama:{available:boolean;model:string|null;reason?:string};manifest:{orders:number;customers:number;products:number;seed:number;start:string;end:string};served_at:string }
