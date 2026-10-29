import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.analytics import detect_anomalies, evaluate, funnel_metrics

def test_late_ingestion_detected():
    e=pd.DataFrame([{"event_id":"e1","session_id":"s1","event_type":"page_view","event_ts":"2026-01-01T00:00:00","ingestion_ts":"2026-01-01T03:00:00","customer_id":"","consent_status":"unknown","order_id":"","is_bot_candidate":False}])
    out=detect_anomalies(e)
    assert out.iloc[0].predicted_issue=="late_ingestion"

def test_duplicate_conversion_detected():
    e=pd.DataFrame([
      {"event_id":"e1","session_id":"s1","event_type":"purchase","event_ts":"2026-01-01","ingestion_ts":"2026-01-01","customer_id":"c","consent_status":"granted","order_id":"o1","is_bot_candidate":False},
      {"event_id":"e2","session_id":"s1","event_type":"purchase","event_ts":"2026-01-01","ingestion_ts":"2026-01-01","customer_id":"c","consent_status":"granted","order_id":"o1","is_bot_candidate":False}])
    out=detect_anomalies(e)
    assert out.loc[out.event_id=="e2","predicted_issue"].iloc[0]=="duplicate_conversion"

def test_evaluation_metrics():
    pred=pd.DataFrame({"event_id":["a","b"],"is_anomaly":[True,True]})
    gt=pd.DataFrame({"record_id":["a","c"],"expected_label":[1,1]})
    m=evaluate(pred,gt)
    assert m["true_positives"]==1 and m["false_positives"]==1 and m["false_negatives"]==1
    assert m["f1"]==0.5

def test_funnel_has_expected_stages():
    e=pd.DataFrame({"event_type":["session_start","product_view"],"session_id":["s1","s1"]})
    assert list(funnel_metrics(e).stage)==["session_start","product_view","add_to_cart","checkout_start","purchase"]
