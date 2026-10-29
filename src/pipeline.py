
"""Run validation, detection, evaluation, and reproducibility manifest."""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.analytics import (
    detect_anomalies,
    validate_data,
    evaluate,
    funnel_metrics,
    checksums,
)


def run(data_dir="data/sample", out="reports"):
    data_path = Path(data_dir)
    output_path = Path(out)
    output_path.mkdir(parents=True, exist_ok=True)

    # Read the large events CSV without chunk-based dtype inference warnings.
    events = pd.read_csv(
        data_path / "journey_events.csv",
        low_memory=False,
    )

    sessions = pd.read_csv(
        data_path / "sessions.csv",
        dtype={"customer_id": str},
        low_memory=False,
    )

    # Bring session consent status into the event data for identity checks.
    events = events.merge(
        sessions[["session_id", "consent_status"]],
        on="session_id",
        how="left",
        suffixes=("", "_session"),
    )

    if "consent_status_session" in events.columns:
        session_consent = events["consent_status_session"]

        if "consent_status" in events.columns:
            events["consent_status"] = session_consent.fillna(
                events["consent_status"]
            )
        else:
            events["consent_status"] = session_consent

        events["consent_status"] = events["consent_status"].fillna(
            "unknown"
        )

    # Detect anomalies and load expected labels when available.
    predictions = detect_anomalies(events)

    ground_truth_path = data_path / "ground_truth.csv"

    if ground_truth_path.exists():
        ground_truth = pd.read_csv(
            ground_truth_path,
            low_memory=False,
        )
    else:
        ground_truth = pd.DataFrame(
            columns=["record_id", "expected_label", "issue_type"]
        )

    # Run validation and analytics.
    validation = validate_data(data_path)
    metrics = evaluate(predictions, ground_truth)
    funnel = funnel_metrics(events)

    # Save all generated reports.
    predictions.to_csv(
        output_path / "anomaly_predictions.csv",
        index=False,
    )

    validation.to_csv(
        output_path / "validation_report.csv",
        index=False,
    )

    funnel.to_csv(
        output_path / "funnel_metrics.csv",
        index=False,
    )

    (output_path / "evaluation_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    (output_path / "checksums.json").write_text(
        json.dumps(checksums(data_path), indent=2),
        encoding="utf-8",
    )

    print("Evaluation:", json.dumps(metrics))
    print(
        f"Validation checks passed: "
        f"{int(validation['passed'].sum())}/{len(validation)}"
    )
    print(f"Reports written to {output_path}")

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Run the customer journey analytics pipeline."
    )

    parser.add_argument(
        "--data",
        default="data/sample",
        help="Directory containing input CSV files.",
    )

    parser.add_argument(
        "--out",
        default="reports",
        help="Directory where output reports will be saved.",
    )

    args = parser.parse_args()
    run(args.data, args.out)


if __name__ == "__main__":
    main()
