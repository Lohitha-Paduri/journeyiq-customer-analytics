
"""Deterministic synthetic customer-journey data generator."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


EVENT_TYPES = [
    "session_start",
    "page_view",
    "product_view",
    "add_to_cart",
    "checkout_start",
    "purchase",
    "support_contact",
    "search",
]

PAGES = ["home", "search", "product", "cart", "checkout", "help"]


def make_id(prefix, n, width=6):
    """Create a predictable ID."""
    return f"{prefix}-{n:0{width}d}"


def generate(sessions=1000, events=None, seed=20261022, out="data/sample"):
    """Generate linked synthetic customer-journey CSV files.

    Args:
        sessions: Number of sessions to create.
        events: Target number of events. Defaults to approximately 20 per session.
        seed: Random seed for reproducible output.
        out: Output directory for CSV files and manifest.json.
    """
    n = int(sessions)

    if n < 1:
        raise ValueError("sessions must be at least 1")

    target_events = int(events) if events is not None else n * 20
    if target_events < 1:
        raise ValueError("events must be at least 1 when specified")

    rng = np.random.default_rng(seed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. Customers
    # ---------------------------------------------------------
    n_customers = max(1, int(n * 0.72))

    customers = pd.DataFrame({
        "customer_id": [
            make_id("CUS", i + 1) for i in range(n_customers)
        ],
        "created_at": pd.date_range(
            "2026-01-01", periods=n_customers, freq="min"
        ).astype(str),
        "consent_status": rng.choice(
            ["granted", "denied", "unknown"],
            n_customers,
            p=[0.65, 0.20, 0.15],
        ),
        "loyalty_tier": rng.choice(
            ["standard", "silver", "gold"],
            n_customers,
            p=[0.70, 0.20, 0.10],
        ),
    })

    customer_ids = customers["customer_id"].to_numpy()
    consented_ids = customers.loc[
        customers["consent_status"] == "granted", "customer_id"
    ].to_numpy()

    if len(consented_ids) == 0:
        consented_ids = customer_ids[:1]

    # ---------------------------------------------------------
    # 2. Pages and products
    # ---------------------------------------------------------
    pages = pd.DataFrame({
        "page_id": [
            make_id("PAG", i + 1, 3) for i in range(len(PAGES))
        ],
        "page_name": PAGES,
        "page_type": [
            "landing", "search", "product", "cart", "checkout", "support"
        ],
    })

    page_id_lookup = dict(zip(pages["page_name"], pages["page_id"]))

    products = pd.DataFrame({
        "product_id": [
            make_id("PRD", i + 1, 4) for i in range(100)
        ],
        "product_name": [
            f"Product {i + 1:03d}" for i in range(100)
        ],
        "category": rng.choice(
            ["home", "fashion", "electronics", "beauty"], 100
        ),
        "unit_price": np.round(rng.uniform(5, 500, 100), 2),
    })

    product_ids = products["product_id"].to_numpy()

    # ---------------------------------------------------------
    # 3. Sessions
    # ---------------------------------------------------------
    session_ids = [f"SES-2026-{i + 1:06d}" for i in range(n)]

    starts = (
        pd.Timestamp("2026-10-01")
        + pd.to_timedelta(
            rng.integers(0, 27 * 24 * 60, n), unit="m"
        )
    )

    assigned_customers = [
        rng.choice(consented_ids) if rng.random() < 0.72 else ""
        for _ in range(n)
    ]

    consent_lookup = customers.set_index("customer_id")["consent_status"]

    session_df = pd.DataFrame({
        "session_id": session_ids,
        "customer_id": assigned_customers,
        "anonymous_id": [
            f"ANON-{i + 1:07d}" for i in range(n)
        ],
        "started_at": starts.astype(str),
        "device": rng.choice(
            ["desktop", "mobile", "tablet"],
            n,
            p=[0.35, 0.55, 0.10],
        ),
        "entry_channel": rng.choice(
            ["web", "app"], n, p=[0.68, 0.32]
        ),
        "consent_status": [
            consent_lookup.get(c, "unknown") if c else "unknown"
            for c in assigned_customers
        ],
    })

    # ---------------------------------------------------------
    # 4. Generate realistic event sequences
    # ---------------------------------------------------------
    event_rows = []
    carts = []
    cart_items = []
    orders = []
    order_items = []
    tickets = []
    outcomes = []
    assignments = []

    experiment_id = "EXP-2026-000001"

    experiments = pd.DataFrame([{
        "experiment_id": experiment_id,
        "experiment_name": "Checkout clarity test",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "status": "active",
    }])

    for i, session in session_df.iterrows():
        session_id = session["session_id"]
        customer_id = session["customer_id"] or ""
        start = pd.Timestamp(session["started_at"])

        stages = ["session_start", "page_view"]

        if rng.random() < 0.82:
            stages.append("product_view")

        if "product_view" in stages and rng.random() < 0.56:
            stages.append("add_to_cart")

        if "add_to_cart" in stages and rng.random() < 0.66:
            stages.append("checkout_start")

        converted = (
            "checkout_start" in stages and rng.random() < 0.58
        )

        if converted:
            stages.append("purchase")

        support = not converted and rng.random() < 0.12
        if support:
            stages.append("support_contact")

        local_events = []
        event_time = start

        page_by_event = {
            "session_start": "home",
            "page_view": "search",
            "product_view": "product",
            "add_to_cart": "cart",
            "checkout_start": "checkout",
            "purchase": "checkout",
            "support_contact": "help",
            "search": "search",
        }

        for j, event_type in enumerate(stages):
            event_time += pd.Timedelta(
                seconds=int(rng.integers(8, 900))
            )

            if event_type == "support_contact":
                channel = "support"
            elif rng.random() < 0.78:
                channel = session["entry_channel"]
            else:
                channel = (
                    "app"
                    if session["entry_channel"] == "web"
                    else "web"
                )

            page_id = page_id_lookup[
                page_by_event.get(event_type, "home")
            ]

            product_id = (
                rng.choice(product_ids)
                if event_type in [
                    "product_view", "add_to_cart", "purchase"
                ]
                else ""
            )

            local_events.append({
                "event_id": f"EVT-{session_id}-{j + 1:04d}",
                "session_id": session_id,
                "customer_id": customer_id,
                "anonymous_id": session["anonymous_id"],
                "event_type": event_type,
                "event_ts": event_time,
                "ingestion_ts": event_time + pd.Timedelta(
                    seconds=int(rng.integers(1, 120))
                ),
                "channel": channel,
                "page_id": page_id,
                "product_id": product_id,
                "cart_id": "",
                "order_id": "",
                "ticket_id": "",
                "is_bot_candidate": False,
            })

        # Additional activity is accumulated in a Python list.
        # This avoids slow DataFrame row-by-row insertion.
        extras = int(rng.poisson(3))

        for k in range(extras):
            event_time += pd.Timedelta(
                seconds=int(rng.integers(3, 300))
            )

            event_type = rng.choice([
                "page_view", "search", "product_view"
            ])

            local_events.append({
                "event_id": (
                    f"EVT-{session_id}-{len(local_events) + 1:04d}"
                ),
                "session_id": session_id,
                "customer_id": customer_id,
                "anonymous_id": session["anonymous_id"],
                "event_type": event_type,
                "event_ts": event_time,
                "ingestion_ts": event_time + pd.Timedelta(
                    seconds=int(rng.integers(1, 120))
                ),
                "channel": session["entry_channel"],
                "page_id": (
                    page_id_lookup["product"]
                    if event_type == "product_view"
                    else page_id_lookup["search"]
                    if event_type == "search"
                    else rng.choice(pages["page_id"].to_numpy())
                ),
                "product_id": (
                    rng.choice(product_ids)
                    if event_type == "product_view"
                    else ""
                ),
                "cart_id": "",
                "order_id": "",
                "ticket_id": "",
                "is_bot_candidate": False,
            })

        # Create cart records.
        cart_id = ""
        if "add_to_cart" in stages:
            cart_id = make_id("CRT", i + 1)

            carts.append({
                "cart_id": cart_id,
                "session_id": session_id,
                "customer_id": customer_id,
                "created_at": str(start),
                "status": "converted" if converted else "abandoned",
            })

            cart_items.append({
                "cart_id": cart_id,
                "product_id": rng.choice(product_ids),
                "quantity": 1,
            })

        # Create order records.
        order_id = ""
        if converted:
            order_id = make_id("ORD", len(orders) + 1)
            amount = float(np.round(rng.uniform(10, 650), 2))

            orders.append({
                "order_id": order_id,
                "session_id": session_id,
                "customer_id": customer_id,
                "ordered_at": str(event_time),
                "status": "completed",
                "total_amount": amount,
            })

            order_items.append({
                "order_id": order_id,
                "product_id": rng.choice(product_ids),
                "quantity": 1,
                "line_amount": amount,
            })

        # Create support tickets.
        ticket_id = ""
        if support:
            ticket_id = make_id("TKT", len(tickets) + 1)

            tickets.append({
                "ticket_id": ticket_id,
                "session_id": session_id,
                "customer_id": customer_id,
                "order_id": order_id,
                "created_at": str(event_time),
                "status": "open",
            })

        for event in local_events:
            if event["event_type"] in [
                "add_to_cart", "checkout_start", "purchase"
            ]:
                event["cart_id"] = cart_id

            if event["event_type"] == "purchase":
                event["order_id"] = order_id

            if event["event_type"] == "support_contact":
                event["ticket_id"] = ticket_id

            event_rows.append(event)

        outcome_type = (
            "converted" if converted
            else "support_contact" if support
            else "abandoned" if len(stages) > 1
            else "in_progress"
        )

        outcomes.append({
            "outcome_id": f"OUT-{session_id}",
            "session_id": session_id,
            "outcome_type": outcome_type,
            "is_converted": bool(converted),
            "outcome_ts": str(event_time),
        })

        assignments.append({
            "experiment_id": experiment_id,
            "session_id": session_id,
            "variant": rng.choice(["control", "treatment"]),
            "assigned_at": str(start),
        })

    events_df = pd.DataFrame(event_rows)

    # ---------------------------------------------------------
    # 5. Pad to the requested event count in one batch
    # ---------------------------------------------------------
    extra_count = max(0, target_events - len(events_df))
    extra_rows = []

    for k in range(extra_count):
        session_index = int(rng.integers(0, n))
        session = session_df.iloc[session_index]

        timestamp = pd.Timestamp(session["started_at"]) + pd.Timedelta(
            seconds=int(rng.integers(1, 3600))
        )

        event_type = rng.choice([
            "page_view", "search", "product_view"
        ])

        extra_rows.append({
            "event_id": (
                f"EVT-{session['session_id']}-X{10000 + k:07d}"
            ),
            "session_id": session["session_id"],
            "customer_id": session["customer_id"],
            "anonymous_id": session["anonymous_id"],
            "event_type": event_type,
            "event_ts": timestamp,
            "ingestion_ts": timestamp + pd.Timedelta(
                seconds=int(rng.integers(1, 120))
            ),
            "channel": session["entry_channel"],
            "page_id": (
                page_id_lookup["product"]
                if event_type == "product_view"
                else page_id_lookup["search"]
                if event_type == "search"
                else page_id_lookup["home"]
            ),
            "product_id": (
                rng.choice(product_ids)
                if event_type == "product_view"
                else ""
            ),
            "cart_id": "",
            "order_id": "",
            "ticket_id": "",
            "is_bot_candidate": False,
        })

    if extra_rows:
        events_df = pd.concat(
            [events_df, pd.DataFrame(extra_rows)],
            ignore_index=True,
        )

    # ---------------------------------------------------------
    # 6. Inject traceable anomalies for testing
    # ---------------------------------------------------------
    ground_truth = []

    if not events_df.empty:
        # Late ingestion anomaly.
        product_events = events_df.index[
            events_df["event_type"] == "product_view"
        ]

        if len(product_events):
            index = int(product_events[0])
            event_id = events_df.loc[index, "event_id"]

            events_df.loc[index, "ingestion_ts"] = (
                pd.Timestamp(events_df.loc[index, "event_ts"])
                + pd.Timedelta(hours=8)
            )

            ground_truth.append({
                "record_id": event_id,
                "entity": "JourneyEvent",
                "issue_type": "late_ingestion",
                "expected_label": 1,
                "injection_rule": "ingestion lag exceeds 2 hours",
            })

        # Identity linked without granted consent.
        unknown_index = next(
            (
                index
                for index, row in events_df.iterrows()
                if row["customer_id"] == ""
            ),
            None,
        )

        if unknown_index is not None:
            event_id = events_df.loc[unknown_index, "event_id"]
            events_df.loc[unknown_index, "customer_id"] = (
                customers.iloc[0]["customer_id"]
            )

            ground_truth.append({
                "record_id": event_id,
                "entity": "JourneyEvent",
                "issue_type": "identity_merge_without_consent",
                "expected_label": 1,
                "injection_rule": (
                    "customer linked to event with no granted consent"
                ),
            })

        # Duplicate conversion anomaly.
        purchase_indices = events_df.index[
            events_df["event_type"] == "purchase"
        ]

        if len(purchase_indices):
            index = int(purchase_indices[0])
            duplicate = events_df.loc[index].copy()
            duplicate["event_id"] = (
                str(duplicate["event_id"]) + "-DUP"
            )
            duplicate["ingestion_ts"] = (
                pd.Timestamp(duplicate["ingestion_ts"])
                + pd.Timedelta(seconds=2)
            )

            events_df = pd.concat(
                [events_df, pd.DataFrame([duplicate])],
                ignore_index=True,
            )

            ground_truth.append({
                "record_id": duplicate["event_id"],
                "entity": "JourneyEvent",
                "issue_type": "duplicate_conversion",
                "expected_label": 1,
                "injection_rule": (
                    "second purchase event references same order"
                ),
            })

        # Mark one event in the highest-volume session.
        session_counts = events_df.groupby("session_id").size()

        if not session_counts.empty:
            busiest_session = str(session_counts.idxmax())
            bot_index = int(
                events_df.index[
                    events_df["session_id"] == busiest_session
                ][0]
            )
            bot_event_id = events_df.loc[bot_index, "event_id"]
            events_df.loc[bot_index, "is_bot_candidate"] = True

            ground_truth.append({
                "record_id": bot_event_id,
                "entity": "JourneyEvent",
                "issue_type": "bot_activity",
                "expected_label": 1,
                "injection_rule": (
                    "one event in a high-volume synthetic session "
                    "marked as bot traffic"
                ),
            })

    # ---------------------------------------------------------
    # 7. Standardize timestamps
    # ---------------------------------------------------------
    for column in ["event_ts", "ingestion_ts"]:
        if column in events_df.columns:
            events_df[column] = pd.to_datetime(
                events_df[column]
            ).astype(str)

    # ---------------------------------------------------------
    # 8. Prepare output tables
    # ---------------------------------------------------------
    tables = {
        "customers.csv": customers,
        "sessions.csv": session_df,
        "pages.csv": pages,
        "products.csv": products,
        "journey_events.csv": events_df,
        "carts.csv": pd.DataFrame(
            carts,
            columns=[
                "cart_id", "session_id", "customer_id",
                "created_at", "status",
            ],
        ),
        "cart_items.csv": pd.DataFrame(
            cart_items,
            columns=["cart_id", "product_id", "quantity"],
        ),
        "orders.csv": pd.DataFrame(
            orders,
            columns=[
                "order_id", "session_id", "customer_id",
                "ordered_at", "status", "total_amount",
            ],
        ),
        "order_items.csv": pd.DataFrame(
            order_items,
            columns=[
                "order_id", "product_id", "quantity", "line_amount",
            ],
        ),
        "support_tickets.csv": pd.DataFrame(
            tickets,
            columns=[
                "ticket_id", "session_id", "customer_id",
                "order_id", "created_at", "status",
            ],
        ),
        "experiments.csv": experiments,
        "experiment_assignments.csv": pd.DataFrame(assignments),
        "journey_outcomes.csv": pd.DataFrame(outcomes),
        "ground_truth.csv": pd.DataFrame(
            ground_truth,
            columns=[
                "record_id", "entity", "issue_type",
                "expected_label", "injection_rule",
            ],
        ),
    }

    for filename, dataframe in tables.items():
        dataframe.to_csv(out / filename, index=False)

    manifest = {
        "seed": seed,
        "sessions": n,
        "requested_events": target_events,
        "actual_events": len(events_df),
        "synthetic": True,
        "entities": list(tables.keys()),
        "generator_version": "1.0",
    }

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic customer journey data."
    )
    parser.add_argument("--sessions", type=int, default=1000)
    parser.add_argument("--events", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--out", default="data/sample")

    args = parser.parse_args()

    result = generate(
        sessions=args.sessions,
        events=args.events,
        seed=args.seed,
        out=args.out,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
