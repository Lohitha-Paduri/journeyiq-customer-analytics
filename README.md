<<<<<<< HEAD
# Customer Journey Analytics & Anomaly Detection

An end-to-end, reproducible hackathon starter project for connecting web, mobile-app, support, and purchase activity; finding journey drop-offs; detecting data-quality anomalies; and evaluating the results against a separate ground-truth file.

## What it does

- Generates linked synthetic data for **Customer, Session, JourneyEvent, Page, Product, Cart, Order, SupportTicket, Experiment, JourneyOutcome**.
- Uses deterministic IDs and a fixed random seed.
- Models event time (`event_ts`) separately from ingestion time (`ingestion_ts`).
- Includes consent-aware identity handling and multi-channel journeys.
- Injects four labelled edge cases: late/out-of-order ingestion, suspicious anonymous identity merge, duplicate conversion, and bot-like activity.
- Keeps injected issue labels in `ground_truth.csv`, separate from event input features.
- Validates primary keys, foreign keys, allowed values, timestamps, and duplicate conversions.
- Calculates funnel conversion/drop-off and detector precision, recall, and F1.
- Includes a Streamlit dashboard and pytest checks.

> This is synthetic data. It contains no real customers or purchases. Detector rules are intentionally explainable baselines, not a trained ML model.

## Quick start

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# Generate a quick dataset (1,000 sessions, approximately 20,000 events)
python -m src.generate_data --sessions 1000 --seed 20261022 --out data/sample

# Run validation, detection, and evaluation
python -m src.pipeline --data data/sample --out reports

# Launch dashboard
streamlit run app.py

# Run tests
pytest -q
```

## Generate the full target scale

The requested scale is 100,000 sessions and approximately 2,000,000 events. Run:

```bash
python -m src.generate_data --sessions 100000 --events 2000000 --seed 20261022 --out data/full
python -m src.pipeline --data data/full --out reports/full
```

The full run may need several GB of free disk space and time. CSVs are written in chunks where practical, but memory requirements depend on the environment. Start with the sample first.

## Project flow

```text
Master data -> sessions and events -> labelled edge-case injection
            -> validation -> rule-based detection -> ground-truth evaluation
            -> funnel/drop-off analysis -> dashboard and reports
```

## Entities and relationships

| Entity | Primary key | Main relationships |
|---|---|---|
| Customer | `customer_id` | 1:N sessions; optional consented identity |
| Session | `session_id` | N:1 customer (optional); 1:N events; 1:1 outcome |
| JourneyEvent | `event_id` | N:1 session; optional customer/page/product/cart/order/ticket |
| Page | `page_id` | 1:N events |
| Product | `product_id` | 1:N events/carts/order lines |
| Cart | `cart_id` | N:1 session; N:M products through `cart_items.csv` |
| Order | `order_id` | N:1 customer/session; N:M products through `order_items.csv` |
| SupportTicket | `ticket_id` | N:1 session; optional customer/order |
| Experiment | `experiment_id` | N:M sessions through `experiment_assignments.csv` |
| JourneyOutcome | `outcome_id` | 1:1 session; outcome is converted/abandoned/support_contact/in_progress |

Supporting bridge tables: `cart_items.csv`, `order_items.csv`, `experiment_assignments.csv`. The sample generator creates compact but linked data. Fields and rules are documented in `docs/DATA_DICTIONARY.md`.

## Business rules

1. A session is one visit with a generated start and end time. This synthetic generator assigns a session ID before generating its events.
2. `event_ts` is when an action occurred; `ingestion_ts` is when the analytics system received it.
3. Funnel stages are `session_start -> product_view -> add_to_cart -> checkout_start -> purchase`. A session reaches a stage if at least one matching event exists.
4. A session is converted when it has a purchase event and an order. An outcome is derived from the event sequence, not randomly assigned.
5. Identity links are only considered valid when `consent_status == "granted"`. Anonymous identifiers are not automatically merged.
6. Ground truth is used only after detector predictions have been made.
7. Anomaly cases are labelled in a separate file and retain `issue_type`; do not use the ground-truth file as detector input.
8. Event history is append-only in the generated output; later state changes are represented as new events or status fields, not overwritten event records.

## Detector caveats

The baseline rules are deliberately interpretable. A duplicate conversion is detected by duplicate purchase/order references; a bot candidate is flagged using an extreme event-rate rule; a late-ingestion case is flagged using ingestion lag; identity merge risk is flagged where an anonymous ID is linked to a customer without consent. Tune thresholds against your generated data and report metrics by anomaly type. A flag means “review this record,” not proof of malicious behavior.

## Reproducibility

Run the generator twice with the same seed and parameters. Compare SHA-256 checksums:

```bash
python -m src.generate_data --sessions 1000 --seed 20261022 --out data/run_a
python -m src.generate_data --sessions 1000 --seed 20261022 --out data/run_b
python -m src.pipeline --data data/run_a --out reports/run_a
python -m src.pipeline --data data/run_b --out reports/run_b
```

Then compare `reports/run_a/checksums.json` and `reports/run_b/checksums.json`. Output files should match when the same code version and parameters are used.

## Suggested hackathon demo

1. Show the funnel and largest drop-off.
2. Select a suspicious record and explain the rule that flagged it.
3. Show precision, recall, and F1 versus `ground_truth.csv`.
4. Show validation results and repeat-run checksum comparison.
5. Explain the limitations and next steps (streaming ingestion, calibrated thresholds, model monitoring, privacy governance).

## Lawful data use

The project defaults to synthetic data. If public data is added later, document its source URL, version, retrieval date, license, attribution, transformations, and discarded fields. Do not bypass access controls or use confidential/personal data.
=======
# journeyiq-customer-analytics
>>>>>>> 0d1c99cf07fdcc0190a9280e1947d853b9cac8f4
