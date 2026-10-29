# 3-minute demo script

1. **Problem (20 sec):** “Customers move between web, app, support, and checkout. If event data is delayed, duplicated, or incorrectly linked, funnel metrics become misleading.”
2. **Data (30 sec):** Show the entity tables and explain that IDs and relationships are generated deterministically from a fixed seed.
3. **Business insight (30 sec):** Open Funnel & journeys. Point out the stage with the largest loss and explain that stage counts are distinct sessions.
4. **Exceptions (40 sec):** Open Anomaly review. Show a late-ingestion or duplicate-conversion candidate and the exact rule behind it.
5. **Evaluation (30 sec):** Show precision/recall/F1 against separate ground truth. Explain that equal counts alone are not proof of correctness.
6. **Trust (20 sec):** Show validation checks, seed, manifest, and checksums.
7. **Limitations (10 sec):** Be honest that this is a synthetic, explainable baseline and identify what would be productionized next.
