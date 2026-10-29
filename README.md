# Customer Journey Analytics & Anomaly Detection

An end-to-end customer analytics project that connects web, mobile app, customer support, and purchase activity to identify customer journey drop-offs, detect data-quality anomalies, and evaluate detection performance using ground-truth data.

## Project Overview

JourneyIQ helps analyze customer behavior across multiple channels, understand where customers abandon their journeys, and identify suspicious or inconsistent analytics events.

The project uses reproducible synthetic data, data validation, explainable anomaly detection rules, funnel analysis, and an interactive Streamlit dashboard.

**Key highlights:**
- Generates linked synthetic data for customers, sessions, journey events, pages, products, carts, orders, support tickets, experiments, and journey outcomes.
- Uses deterministic IDs and fixed random seeds for reproducibility.
- Separates event occurrence time (`event_ts`) from ingestion time (`ingestion_ts`).
- Supports consent-aware identity handling and multi-channel customer journeys.
- Injects four labelled edge cases: late/out-of-order ingestion, suspicious anonymous identity merging, duplicate conversions, and bot-like activity.
- Stores anomaly labels separately in `ground_truth.csv` to prevent data leakage.
- Validates primary keys, foreign keys, allowed values, timestamps, and duplicate conversions.
- Calculates funnel conversion rates, drop-offs, precision, recall, and F1-score.
- Includes an interactive Streamlit dashboard and automated pytest checks.

> **Note:** This project uses synthetic data and contains no real customer or purchase information. The anomaly detectors are explainable rule-based baselines, not a trained machine learning model.

## Technologies Used

- **Programming Language:** Python
- **Data Analysis:** Pandas, NumPy
- **Dashboard:** Streamlit
- **Data Visualization:** Plotly
- **Testing:** Pytest
- **Data Storage:** CSV files
- **Version Control:** Git and GitHub

## Project Architecture

```text
Synthetic Data Generation
          |
          v
Customer Journey Events
          |
          v
Data Validation
          |
          v
Rule-Based Anomaly Detection
          |
          v
Ground-Truth Evaluation
          |
          v
Funnel and Drop-Off Analysis
          |
          v
Streamlit Dashboard and Reports
```

## Data Model

The project generates the following entities:

| Entity | Purpose |
|---|---|
| Customer | Stores synthetic customer information and consent status |
| Session | Represents an individual customer visit |
| JourneyEvent | Records actions performed during a journey |
| Page | Stores page information |
| Product | Represents products viewed or purchased |
| Cart | Represents shopping carts |
| Order | Stores purchase information |
| SupportTicket | Represents customer support interactions |
| Experiment | Represents experiments or A/B tests |
| JourneyOutcome | Records whether a journey converted, was abandoned, involved support, or remains in progress |

Supporting bridge tables include `cart_items.csv`, `order_items.csv`, and `experiment_assignments.csv`.

See `docs/DATA_DICTIONARY.md` for field definitions and data rules.

## Anomaly Detection

The project injects and evaluates four types of edge cases:

1. **Late ingestion:** Events received significantly later than their occurrence time.
2. **Suspicious identity merge:** An anonymous identifier linked to a customer without the required consent.
3. **Duplicate conversion:** Duplicate purchase events or order references.
4. **Bot-like activity:** Unusually high event rates that may indicate automated behavior.

The rules flag suspicious records for review; a flag does not prove malicious activity.

## Customer Journey Funnel Analysis

The funnel tracks these stages:

```text
Session Start
     |
     v
Product View
     |
     v
Add to Cart
     |
     v
Checkout Start
     |
     v
Purchase
```

The analysis identifies