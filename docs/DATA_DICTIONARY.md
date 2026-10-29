# Data dictionary

All data is synthetic. Timestamp values are ISO-formatted strings. Blank IDs mean an optional relationship is absent.

## Core entities

### customers.csv — Customer
- `customer_id` (string, PK, required): immutable `CUS-000001` style ID.
- `created_at` (timestamp, required): synthetic account creation time.
- `consent_status` (enum: granted/denied/unknown, required): permission state for identity stitching.
- `loyalty_tier` (enum: standard/silver/gold, required): synthetic segment.

### sessions.csv — Session
- `session_id` (string, PK, required): `SES-2026-000001`.
- `customer_id` (string, FK -> Customer, optional): linked customer when available.
- `anonymous_id` (string, required): pseudonymous browser/device identifier.
- `started_at` (timestamp, required): session start.
- `device` (enum: desktop/mobile/tablet).
- `entry_channel` (enum: web/app).
- `consent_status` (enum: granted/denied/unknown): consent snapshot used for identity rules.

### journey_events.csv — JourneyEvent
- `event_id` (string, PK, required): `EVT-<session-id>-NNNN`; injected duplicate uses `-DUP`.
- `session_id` (FK -> Session, required).
- `customer_id` (FK -> Customer, optional): blank when anonymous; deliberate edge case may violate consent policy.
- `anonymous_id` (string, required).
- `event_type` (enum: session_start/page_view/product_view/add_to_cart/checkout_start/purchase/support_contact/search).
- `event_ts` (timestamp, required): occurrence time.
- `ingestion_ts` (timestamp, required): ingestion time.
- `channel` (enum: web/app/support).
- `page_id` (FK -> Page, required).
- `product_id` (FK -> Product, optional).
- `cart_id` (FK -> Cart, optional).
- `order_id` (FK -> Order, optional).
- `ticket_id` (FK -> SupportTicket, optional).
- `is_bot_candidate` (boolean-like): synthetic bot burst marker for review.

### pages.csv — Page
- `page_id` (PK): `PAG-001` style ID.
- `page_name` (unique, required): home/search/product/cart/checkout/help.
- `page_type` (string): page category.

### products.csv — Product
- `product_id` (PK): `PRD-0001` style ID.
- `product_name` (string, required).
- `category` (enum: home/fashion/electronics/beauty).
- `unit_price` (decimal, synthetic currency units).

### carts.csv — Cart
- `cart_id` (PK), `session_id` (FK -> Session), optional `customer_id`, `created_at`, `status` (converted/abandoned).

### cart_items.csv — CartItem bridge
- Composite logical key (`cart_id`, `product_id`); both are foreign keys; `quantity` is a positive integer.

### orders.csv — Order
- `order_id` (PK), `session_id` (FK -> Session), optional `customer_id`, `ordered_at`, `status`, `total_amount` (nonnegative decimal).

### order_items.csv — OrderItem bridge
- Composite logical key (`order_id`, `product_id`); both are foreign keys; quantity and line amount describe the line item.

### support_tickets.csv — SupportTicket
- `ticket_id` (PK), `session_id` (FK -> Session), optional `customer_id` and `order_id`, `created_at`, `status`.

### experiments.csv — Experiment
- `experiment_id` (PK): `EXP-2026-000001`.
- `experiment_name`, `start_date`, `end_date`, `status`.

### experiment_assignments.csv — bridge
- `experiment_id` (FK -> Experiment), `session_id` (FK -> Session), `variant` (control/treatment), `assigned_at`.

### journey_outcomes.csv — JourneyOutcome
- `outcome_id` (PK): `OUT-<session-id>`.
- `session_id` (unique FK -> Session), `outcome_type` (converted/abandoned/support_contact/in_progress), `is_converted` (boolean), `outcome_ts`.

### ground_truth.csv — evaluation-only labels
- `record_id`: ID of an injected record.
- `entity`: entity name.
- `issue_type`: late_ingestion / identity_merge_without_consent / duplicate_conversion / bot_activity.
- `expected_label`: 1 for injected issue.
- `injection_rule`: human-readable reason. Never use this file to generate predictions.

## Cardinality summary

- Customer 1:N Session (optional customer link).
- Session 1:N JourneyEvent.
- Page 1:N JourneyEvent.
- Product 1:N JourneyEvent; CartItem; OrderItem.
- Session 1:0..1 JourneyOutcome.
- Session 1:N Cart, Order, SupportTicket.
- Experiment N:M Session through ExperimentAssignment.
- Cart N:M Product through CartItem; Order N:M Product through OrderItem.
