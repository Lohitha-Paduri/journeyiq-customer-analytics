
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import (
    detect_anomalies,
    evaluate,
    funnel_metrics,
    validate_data,
)

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="JourneyIQ | Customer Journey Analytics",
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 JourneyIQ")
st.caption(
    "Customer Journey Analytics, Explainable Anomaly Detection "
    "and Data Quality"
)

# ---------------------------------------------------------
# Navigation and dataset selection
# ---------------------------------------------------------
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a page",
    [
        "Funnel & Journey",
        "Anomaly Review",
        "Evaluation",
        "Data Quality",
    ],
)

data_dir = st.sidebar.text_input(
    "Dataset folder",
    "data/sample",
)

data_path = Path(data_dir)

st.sidebar.divider()
st.sidebar.caption("JourneyIQ • Synthetic analytics project")

required_files = [
    "journey_events.csv",
    "sessions.csv",
]

missing = [
    filename
    for filename in required_files
    if not (data_path / filename).exists()
]

if missing:
    st.error(
        f"Missing required files in `{data_path}`: "
        f"{', '.join(missing)}"
    )
    st.code(
        "python src/generate_data.py --sessions 100 --events 2000"
    )
    st.stop()


# ---------------------------------------------------------
# Data loading
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_table(folder, filename):
    path = Path(folder) / filename

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


@st.cache_data(show_spinner="Loading customer journey data...")
def load_data(folder):
    events = read_table(folder, "journey_events.csv")
    sessions = read_table(folder, "sessions.csv")
    customers = read_table(folder, "customers.csv")
    orders = read_table(folder, "orders.csv")
    ground_truth = read_table(folder, "ground_truth.csv")

    # Attach session-level consent information to events.
    if (
        not events.empty
        and not sessions.empty
        and "session_id" in events.columns
        and "session_id" in sessions.columns
        and "consent_status" in sessions.columns
    ):
        consent = sessions[
            ["session_id", "consent_status"]
        ].drop_duplicates("session_id")

        if "consent_status" in events.columns:
            events = events.drop(columns=["consent_status"])

        events = events.merge(
            consent,
            on="session_id",
            how="left",
            validate="many_to_one",
        )

    predictions = detect_anomalies(events)

    return (
        events,
        sessions,
        customers,
        orders,
        ground_truth,
        predictions,
    )


(
    events,
    sessions,
    customers,
    orders,
    ground_truth,
    predictions,
) = load_data(str(data_path))


def metric_value(frame, column):
    """Return the number of unique nonempty values in a column."""
    if frame.empty or column not in frame.columns:
        return 0

    values = frame[column].fillna("").astype(str)
    return int(values[values.ne("")].nunique())


def format_percent(value):
    return f"{value:.2f}%"


def get_flagged_records(frame):
    if "is_anomaly" not in frame.columns:
        return frame.iloc[0:0].copy()

    return frame[frame["is_anomaly"].fillna(False)].copy()


def calculate_issue_metrics(predicted, truth):
    """Calculate record-level metrics separately for each issue type."""
    rows = []

    if truth.empty or "record_id" not in truth.columns:
        return pd.DataFrame()

    truth_positive = truth.copy()

    if "expected_label" in truth_positive.columns:
        truth_positive = truth_positive[
            pd.to_numeric(
                truth_positive["expected_label"],
                errors="coerce",
            ).fillna(0).eq(1)
        ]

    truth_positive["record_id"] = (
        truth_positive["record_id"].astype(str)
    )

    if "issue_type" not in truth_positive.columns:
        return pd.DataFrame()

    flagged = get_flagged_records(predicted)

    if "event_id" not in flagged.columns:
        return pd.DataFrame()

    flagged["event_id"] = flagged["event_id"].astype(str)

    for issue in sorted(
        truth_positive["issue_type"].dropna().astype(str).unique()
    ):
        actual_ids = set(
            truth_positive.loc[
                truth_positive["issue_type"].astype(str).eq(issue),
                "record_id",
            ]
        )

        predicted_ids = set(
            flagged.loc[
                flagged["predicted_issue"].astype(str).eq(issue),
                "event_id",
            ]
        )

        tp = len(actual_ids & predicted_ids)
        fp = len(predicted_ids - actual_ids)
        fn = len(actual_ids - predicted_ids)

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

        rows.append({
            "anomaly_type": issue,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "ground_truth_records": len(actual_ids),
            "predicted_records": len(predicted_ids),
        })

    return pd.DataFrame(rows)


# =========================================================
# PAGE 1: FUNNEL & JOURNEY
# =========================================================
if page == "Funnel & Journey":
    st.header("Funnel & Customer Journey")
    st.write(
        "Understand how customers move through the shopping journey, "
        "where sessions drop off, and which paths occur most frequently."
    )

    session_count = metric_value(sessions, "session_id")
    event_count = len(events)
    order_count = metric_value(orders, "order_id")

    purchase_sessions = (
        metric_value(
            events.loc[
                events["event_type"].eq("purchase")
            ],
            "session_id",
        )
        if "event_type" in events.columns
        else 0
    )

    conversion_rate = (
        purchase_sessions / session_count * 100
        if session_count
        else 0.0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", f"{session_count:,}")
    c2.metric("Events", f"{event_count:,}")
    c3.metric("Orders", f"{order_count:,}")
    c4.metric(
        "Session conversion",
        format_percent(conversion_rate),
    )

    st.divider()
    st.subheader("Conversion funnel")

    funnel = funnel_metrics(events)

    if funnel.empty:
        st.info("No events are available to calculate the funnel.")
    else:
        # Add an explicit stage-to-stage retention metric.
        funnel = funnel.copy()
        funnel["previous_stage_sessions"] = (
            funnel["sessions"].shift(1)
        )

        funnel["retention_pct"] = funnel.apply(
            lambda row: (
                row["sessions"]
                / row["previous_stage_sessions"]
                * 100
                if pd.notna(row["previous_stage_sessions"])
                and row["previous_stage_sessions"] > 0
                else 100.0 if row.name == 0 else 0.0
            ),
            axis=1,
        ).round(2)

        funnel["drop_off_pct"] = pd.to_numeric(
            funnel["drop_off_pct"],
            errors="coerce",
        ).fillna(0)

        fig = px.bar(
            funnel,
            x="stage",
            y="sessions",
            text="sessions",
            title="Unique sessions reaching each stage",
            labels={
                "stage": "Journey stage",
                "sessions": "Unique sessions",
            },
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Unique sessions",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Stage counts are based on unique sessions containing each "
            "event type. They are not necessarily a strictly sequential "
            "cohort funnel."
        )

        st.dataframe(
            funnel,
            use_container_width=True,
            hide_index=True,
        )

        if len(funnel) > 1:
            # Compare consecutive stage counts and identify the largest
            # absolute drop. This is separate from percentage drop-off.
            comparisons = funnel.iloc[1:].copy()
            biggest = comparisons.sort_values(
                "drop_off_from_previous",
                ascending=False,
            ).iloc[0]

            st.info(
                f"Largest absolute stage drop: **{biggest['stage']}**, "
                f"with {int(biggest['drop_off_from_previous']):,} "
                f"fewer sessions than the preceding stage "
                f"({float(biggest['drop_off_pct']):.2f}% drop-off)."
            )

    st.divider()
    st.subheader("Event volume by channel")

    if (
        not events.empty
        and {"channel", "event_type"}.issubset(events.columns)
    ):
        channel_data = (
            events.groupby(["channel", "event_type"])
            .size()
            .reset_index(name="event_count")
        )

        channel_fig = px.bar(
            channel_data,
            x="channel",
            y="event_count",
            color="event_type",
            barmode="stack",
            title="Events grouped by channel",
        )
        st.plotly_chart(
            channel_fig,
            use_container_width=True,
        )
    else:
        st.info("Channel or event-type information is unavailable.")

    st.divider()
    st.subheader("Most common customer journey paths")

    if (
        not events.empty
        and {"session_id", "event_type"}.issubset(events.columns)
    ):
        ordered = events.copy()

        if "event_ts" in ordered.columns:
            ordered["event_ts"] = pd.to_datetime(
                ordered["event_ts"],
                errors="coerce",
            )
            ordered = ordered.sort_values(
                ["session_id", "event_ts"]
            )

        ordered["event_type"] = (
            ordered["event_type"].fillna("unknown").astype(str)
        )

        paths = (
            ordered.groupby("session_id")["event_type"]
            .agg(lambda values: " → ".join(values.tolist()[:8]))
            .value_counts()
            .head(10)
            .rename_axis("journey_path")
            .reset_index(name="sessions")
        )

        st.dataframe(
            paths,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Journey event details are unavailable.")


# =========================================================
# PAGE 2: ANOMALY REVIEW
# =========================================================
elif page == "Anomaly Review":
    st.header("Anomaly Review")
    st.write(
        "Inspect records flagged by the detector. A flagged record is "
        "a candidate for investigation, not proof of fraud."
    )

    flagged = get_flagged_records(predictions)
    total_flagged = len(flagged)

    issue_counts = (
        flagged["predicted_issue"].value_counts()
        if (
            not flagged.empty
            and "predicted_issue" in flagged.columns
        )
        else pd.Series(dtype="int64")
    )

    a, b, c = st.columns(3)
    a.metric("Flagged records", f"{total_flagged:,}")
    b.metric("Anomaly types", f"{len(issue_counts):,}")
    c.metric(
        "Share of event records",
        format_percent(
            total_flagged / len(events) * 100 if len(events) else 0
        ),
    )

    st.subheader("Anomaly categories")

    if not issue_counts.empty:
        category_df = (
            issue_counts.rename_axis("anomaly_type")
            .reset_index(name="records")
        )

        fig = px.bar(
            category_df,
            x="anomaly_type",
            y="records",
            text="records",
            title="Flagged records by detected issue",
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No records are currently flagged.")

    st.subheader("Filter and inspect records")

    if total_flagged:
        issue_options = [
            "All types",
            *sorted(
                flagged["predicted_issue"]
                .dropna()
                .astype(str)
                .unique()
            ),
        ]

        selected_issue = st.selectbox(
            "Filter by anomaly type",
            issue_options,
        )

        filtered = flagged.copy()

        if selected_issue != "All types":
            filtered = filtered[
                filtered["predicted_issue"].astype(str).eq(
                    selected_issue
                )
            ]

        columns_to_show = [
            column
            for column in [
                "event_id",
                "session_id",
                "customer_id",
                "event_type",
                "channel",
                "predicted_issue",
                "ingestion_lag_hours",
                "order_id",
                "is_bot_candidate",
            ]
            if column in filtered.columns
        ]

        st.dataframe(
            filtered[columns_to_show],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download filtered anomaly records",
            data=filtered[columns_to_show].to_csv(
                index=False
            ).encode("utf-8"),
            file_name="anomaly_review.csv",
            mime="text/csv",
        )

        selected_record = st.selectbox(
            "Inspect one event",
            filtered["event_id"].astype(str).tolist(),
        )

        record = filtered[
            filtered["event_id"].astype(str).eq(selected_record)
        ]

        if not record.empty:
            st.markdown("**Selected record details**")
            st.json(
                record.iloc[0].where(
                    pd.notna(record.iloc[0]), None
                ).to_dict()
            )
    else:
        st.info(
            "No flagged records are available. Confirm that the data "
            "was generated and that anomaly detection ran successfully."
        )

    st.caption(
        "Ground-truth labels are intended for evaluation. They should "
        "not be used as inputs to the anomaly detector."
    )


# =========================================================
# PAGE 3: EVALUATION
# =========================================================
elif page == "Evaluation":
    st.header("Detection Evaluation")
    st.write(
        "Compare predicted anomaly records with the separate ground-truth "
        "labels supplied by the synthetic data generator."
    )

    if ground_truth.empty:
        st.warning(
            "ground_truth.csv is missing or empty. Generate the dataset "
            "with ground-truth labels to evaluate detection performance."
        )
        st.stop()

    metrics = evaluate(predictions, ground_truth)
    per_issue = calculate_issue_metrics(
        predictions,
        ground_truth,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Precision",
        f"{metrics['precision']:.3f}",
    )
    m2.metric(
        "Recall",
        f"{metrics['recall']:.3f}",
    )
    m3.metric(
        "F1 score",
        f"{metrics['f1']:.3f}",
    )
    m4.metric(
        "Ground-truth anomalies",
        f"{metrics['ground_truth_anomalies']:,}",
    )

    st.subheader("Overall confusion counts")

    confusion = pd.DataFrame([
        {
            "metric": "True positives",
            "count": metrics["true_positives"],
            "meaning": "Predicted anomaly record is labelled anomalous",
        },
        {
            "metric": "False positives",
            "count": metrics["false_positives"],
            "meaning": "Predicted anomaly record is not labelled anomalous",
        },
        {
            "metric": "False negatives",
            "count": metrics["false_negatives"],
            "meaning": "Ground-truth anomaly was not detected",
        },
    ])

    st.dataframe(
        confusion,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Performance by anomaly type")

    if not per_issue.empty:
        st.dataframe(
            per_issue,
            use_container_width=True,
            hide_index=True,
        )

        chart_data = per_issue.melt(
            id_vars="anomaly_type",
            value_vars=["precision", "recall", "f1_score"],
            var_name="metric",
            value_name="score",
        )

        fig = px.bar(
            chart_data,
            x="anomaly_type",
            y="score",
            color="metric",
            barmode="group",
            title="Detection performance by anomaly type",
            range_y=[0, 1],
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(
            "Per-type evaluation could not be calculated from the "
            "available ground-truth columns."
        )

    st.subheader("Ground-truth records")

    truth_columns = [
        column
        for column in [
            "record_id",
            "entity",
            "issue_type",
            "expected_label",
            "injection_rule",
        ]
        if column in ground_truth.columns
    ]

    st.dataframe(
        ground_truth[truth_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download evaluation by anomaly type",
        data=(
            per_issue.to_csv(index=False).encode("utf-8")
            if not per_issue.empty
            else b""
        ),
        file_name="evaluation_by_anomaly_type.csv",
        mime="text/csv",
        disabled=per_issue.empty,
    )

    st.warning(
        "Important: perfect scores on a small synthetic dataset do not "
        "prove that a detector will perform equally well on real-world "
        "customer data. Review each anomaly type and test on additional "
        "data before drawing that conclusion."
    )


# =========================================================
# PAGE 4: DATA QUALITY
# =========================================================
elif page == "Data Quality":
    st.header("Data Quality & Integrity")
    st.write(
        "Review validation results, dataset sizes, and key integrity "
        "checks for the current dataset."
    )

    with st.spinner("Running validation checks..."):
        quality = validate_data(data_path)

    passed_count = (
        int(quality["passed"].sum())
        if not quality.empty and "passed" in quality.columns
        else 0
    )
    total_checks = len(quality)
    failed_count = total_checks - passed_count

    q1, q2, q3 = st.columns(3)
    q1.metric("Checks passed", f"{passed_count}/{total_checks}")
    q2.metric("Checks failed", f"{failed_count}")
    q3.metric("Events inspected", f"{len(events):,}")

    if failed_count == 0:
        st.success("All available validation checks passed.")
    else:
        st.warning(
            f"{failed_count} validation check(s) failed. "
            "Review the details below."
        )

    st.subheader("Validation results")

    if not quality.empty:
        st.dataframe(
            quality,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download validation report",
            data=quality.to_csv(index=False).encode("utf-8"),
            file_name="data_quality_report.csv",
            mime="text/csv",
        )
    else:
        st.info("No validation results were returned.")

    st.subheader("Dataset overview")

    table_names = [
        "customers.csv",
        "sessions.csv",
        "pages.csv",
        "products.csv",
        "journey_events.csv",
        "carts.csv",
        "cart_items.csv",
        "orders.csv",
        "order_items.csv",
        "support_tickets.csv",
        "experiments.csv",
        "experiment_assignments.csv",
        "journey_outcomes.csv",
        "ground_truth.csv",
    ]

    overview_rows = []

    for filename in table_names:
        table = read_table(str(data_path), filename)

        overview_rows.append({
            "table": filename,
            "rows": len(table),
            "status": "Available" if (data_path / filename).exists()
            else "Missing",
        })

    overview = pd.DataFrame(overview_rows)

    st.dataframe(
        overview,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Data quality interpretation")

    st.markdown(
        """
        - **Primary-key checks:** verify that record identifiers are unique.
        - **Foreign-key checks:** verify that event references point to
          existing parent records.
        - **Timestamp checks:** verify that event timestamps can be parsed.
        - **Business-rule checks:** verify that event types and order
          amounts follow documented rules.
        """
    )

    st.caption(
        "The displayed checks are only the checks implemented by the "
        "current validation function. A passing report does not prove "
        "that every possible data-quality issue has been ruled out."
    )
