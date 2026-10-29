"""Explainable anomaly rules, integrity validation, and business metrics."""
from pathlib import Path
import hashlib, json
import pandas as pd

def detect_anomalies(events: pd.DataFrame) -> pd.DataFrame:
    e=events.copy()
    if e.empty:
        e["predicted_issue"]=""; e["is_anomaly"]=False
        return e
    e["event_ts"]=pd.to_datetime(e["event_ts"],errors="coerce")
    e["ingestion_ts"]=pd.to_datetime(e["ingestion_ts"],errors="coerce")
    e["ingestion_lag_hours"]=(e["ingestion_ts"]-e["event_ts"]).dt.total_seconds()/3600
    e["predicted_issue"]=""
    e.loc[e["ingestion_lag_hours"]>2,"predicted_issue"]="late_ingestion"
    # Consent-aware identity: session consent is joined by session_id.
    if "consent_status" not in e.columns:
        e["consent_status"]="unknown"
    bad_identity=(e["customer_id"].fillna("").ne("")) & e["consent_status"].fillna("unknown").ne("granted")
    e.loc[bad_identity & e["predicted_issue"].eq(""),"predicted_issue"]="identity_merge_without_consent"
    # A repeated purchase event for the same order is a duplicate conversion candidate.
    purch=e[e["event_type"].eq("purchase") & e["order_id"].fillna("").ne("")]
    dup_ids=set(purch[purch.duplicated(["session_id","order_id"],keep="first")]["event_id"].astype(str))
    e.loc[e["event_id"].astype(str).isin(dup_ids),"predicted_issue"]="duplicate_conversion"
    bot=e["is_bot_candidate"].astype(str).str.lower().isin(["true","1","yes"])
    e.loc[bot & e["predicted_issue"].eq(""),"predicted_issue"]="bot_activity"
    e["is_anomaly"]=e["predicted_issue"].ne("")
    return e

def validate_data(data_dir):
    d=Path(data_dir); results=[]
    def add(name, passed, detail): results.append({"check":name,"passed":bool(passed),"detail":str(detail)})
    def read(name): return pd.read_csv(d/name) if (d/name).exists() else pd.DataFrame()
    events=read("journey_events.csv"); sessions=read("sessions.csv"); customers=read("customers.csv")
    pages=read("pages.csv"); products=read("products.csv"); orders=read("orders.csv")
    add("session_primary_key_unique",sessions.session_id.is_unique if len(sessions) else False,f"{sessions.session_id.nunique()}/{len(sessions)} unique")
    add("event_primary_key_unique",events.event_id.is_unique if len(events) else False,f"{events.event_id.nunique()}/{len(events)} unique")
    add("customer_primary_key_unique",customers.customer_id.is_unique if len(customers) else False,f"{customers.customer_id.nunique()}/{len(customers)} unique")
    add("event_session_foreign_keys",events.session_id.isin(set(sessions.session_id)).all() if len(events) else True,"events reference existing sessions")
    add("event_page_foreign_keys",events.page_id.fillna("").isin(set(pages.page_id)|{""}).all() if len(events) else True,"events reference existing pages or blank")
    add("event_product_foreign_keys",events.product_id.fillna("").isin(set(products.product_id)|{""}).all() if len(events) else True,"events reference existing products or blank")
    ev=pd.to_datetime(events.event_ts,errors="coerce") if len(events) else pd.Series(dtype="datetime64[ns]")
    ing=pd.to_datetime(events.ingestion_ts,errors="coerce") if len(events) else pd.Series(dtype="datetime64[ns]")
    add("event_timestamps_parse",bool(ev.notna().all() and ing.notna().all()),f"{ev.notna().sum()}/{len(ev)} event times parse")
    add("allowed_event_types",set(events.event_type).issubset({"session_start","page_view","product_view","add_to_cart","checkout_start","purchase","support_contact","search"}) if len(events) else True,"event taxonomy is documented")
    if len(orders):
        add("order_amount_nonnegative",pd.to_numeric(orders.total_amount,errors="coerce").ge(0).all(),"order totals must be nonnegative")
    else: add("order_amount_nonnegative",True,"no orders in dataset")
    return pd.DataFrame(results)

def funnel_metrics(events):
    funnel=["session_start","product_view","add_to_cart","checkout_start","purchase"]
    if events.empty: return pd.DataFrame(columns=["stage","sessions","drop_off_from_previous","drop_off_pct"])
    counts=events.groupby("event_type").session_id.nunique()
    rows=[]; prev=None
    for stage in funnel:
        count=int(counts.get(stage,0))
        drop=(prev-count) if prev is not None else 0
        pct=(drop/prev*100) if prev else 0.0
        rows.append({"stage":stage,"sessions":count,"drop_off_from_previous":drop,"drop_off_pct":round(pct,2)})
        prev=count
    return pd.DataFrame(rows)

def evaluate(predictions, ground_truth):
    truth=set(ground_truth.loc[ground_truth.expected_label.astype(int)==1,"record_id"].astype(str)) if len(ground_truth) else set()
    pred=set(predictions.loc[predictions.is_anomaly,"event_id"].astype(str)) if len(predictions) else set()
    tp=len(pred & truth); fp=len(pred-truth); fn=len(truth-pred)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"true_positives":tp,"false_positives":fp,"false_negatives":fn,
            "precision":round(precision,4),"recall":round(recall,4),"f1":round(f1,4),
            "predicted_anomalies":len(pred),"ground_truth_anomalies":len(truth)}

def checksums(data_dir):
    result={}
    for p in sorted(Path(data_dir).glob("*.csv")):
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        result[p.name]={"sha256":h,"bytes":p.stat().st_size}
    return result
