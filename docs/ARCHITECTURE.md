# Architecture and decisions

## Pipeline
1. **Generate** parent/master entities before dependent records.
2. **Persist** each table as CSV, with explicit primary/foreign keys.
3. **Inject** four labelled negative scenarios after baseline generation.
4. **Validate** key integrity, taxonomy, timestamps, and order arithmetic.
5. **Detect** suspicious events using transparent rules.
6. **Evaluate** predictions against a separate ground-truth file.
7. **Present** business metrics and exceptions in Streamlit.

## Event time vs ingestion time
`event_ts` is when the action occurred; `ingestion_ts` is when the system received it. Late arrival is meaningful only when these are kept separate.

## Identity and consent
Customer identity is optional. An anonymous ID is retained even when customer identity is absent. The identity rule flags links where the session consent snapshot is not `granted`. This is a synthetic compliance check, not legal advice.

## Funnel definition
The canonical funnel is session_start -> product_view -> add_to_cart -> checkout_start -> purchase. Stage counts use distinct session IDs. They are reach counts, not necessarily a strict ordered-sequence funnel; a production version should explicitly validate event order per session.

## Anomaly rules
- Late ingestion: ingestion lag greater than two hours.
- Identity merge without consent: nonblank customer ID while session consent is not granted.
- Duplicate conversion: more than one purchase event references the same session/order pair.
- Bot activity: synthetic `is_bot_candidate` marker, representing a rule-based candidate. In production, use event-rate and behavioral features and calibrate thresholds.

## Key limitations / next steps
- CSV storage is suitable for a hackathon demo; production-scale data should use partitioned Parquet or a database.
- At full scale, optimize generation and analysis with chunking/columnar processing.
- Add strict ordered funnel computation, per-issue confusion matrices, threshold calibration, monitoring, access controls, and documented retention policy.
