# Business rules and acceptance checklist

- [x] Parent/master data generated before dependent entities.
- [x] IDs are deterministic and zero-padded.
- [x] Cross-channel event records include event and ingestion timestamps.
- [x] Anonymous journeys and consent states represented.
- [x] Outcomes derived from generated event sequences.
- [x] Four labelled anomaly cases stored separately in ground truth.
- [x] Basic primary-key, foreign-key, timestamp, enum, and amount validation.
- [x] Funnel reach/drop-off metrics.
- [x] Precision, recall, and F1 evaluation.
- [x] SHA-256 checksums for generated CSV files.
- [x] Streamlit dashboard and automated tests.
- [ ] Production-grade streaming ingestion / database persistence.
- [ ] Fully optimized memory-bounded generator for the 2M-event target.
- [ ] Strict event-order funnel and advanced identity graph logic.
- [ ] Calibrated bot classifier (current marker is a synthetic baseline).

The unchecked items are explicit limitations, not claims of completed features.
