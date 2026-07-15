# AutoLens AU — Model Card

## Model Overview

| Field | Value |
|-------|-------|
| **Model Name** | AutoLens AU Hedonic Pricing Model |
| **Version** | 1.0 implementation; no verified trained artifact yet |
| **Type** | Regression (LightGBM Gradient Boosted Trees) |
| **Target** | log(price_aud) — reverted to AUD at prediction time |
| **Framework** | scikit-learn pipeline + LightGBM |
| **Last Trained** | Never |
| **Author** | Osman Orka |

---

## Intended Use

- **Primary**: Estimate market value of used vehicles in Australia
- **Secondary**: Support depreciation analysis and residual value projections
- **Users**: Dashboard visitors, API consumers, automotive analysts
- **Out of scope**: New vehicle pricing, fleet management, insurance claims

---

## Training Data

| Property | Detail |
|----------|--------|
| Source | Kaggle Australian Vehicle Prices dataset |
| Records | 0 verified training rows; source dataset is expected to contain ~16,700 listings |
| Geography | Australia-wide (all states) |
| Time period | Primarily 2023 listings |
| Validation | Snapshot OOT when ≥2 usable snapshots exist; explicitly labelled random holdout otherwise |

---

## Features

### Numeric
| Feature | Description |
|---------|-------------|
| age | Current year minus manufacture year |
| kilometres | Odometer reading |
| doors | Number of doors |
| seats | Number of seats |
| cylinders | Engine cylinder count |
| age_km_interaction | age × kilometres / 10000 |

### Categorical
| Feature | Description |
|---------|-------------|
| brand | Vehicle manufacturer |
| model | Vehicle model |
| variant | Badge/trim when supplied; Unknown otherwise |
| body_type | Sedan, SUV, Hatchback, etc. |
| fuel_type | Petrol, Diesel, Hybrid, Electric |
| transmission | Automatic, Manual |
| drive_type | FWD, RWD, AWD, 4WD |
| condition | New, Used, Demo |
| state | Australian state/territory |

---

## Performance Metrics

### Overall

| Metric | Value |
|--------|-------|
| MAE | Not measured |
| MdAPE | Not measured |
| R² | Not measured |
| Coverage (80% PI) | Not measured |

### By Price Segment

No segment metrics exist yet. This section will be generated from the first verified model artifact
rather than populated with targets.

---

## Known Limitations

1. **Condition granularity**: Public data lacks detailed condition scoring
2. **Variant/badge detail**: Model strings don't always distinguish trim levels
3. **Geographic bias**: Metro areas overrepresented vs regional
4. **Temporal**: Training data primarily from 2023; market shifts may not be captured
5. **Options/features**: Individual vehicle options (sunroof, leather, etc.) not modelled
6. **Temporal validation**: A single listing snapshot cannot support genuine out-of-time testing;
   refreshes must accumulate first
7. **Intervals/explanations**: The implementation requires a held-out split-conformal calibration
   quantile and computes local TreeSHAP values. No interval coverage or explanation is presented
   until a calibrated bundle has been trained.

---

## Ethical Considerations

- Model does not use protected characteristics (race, gender, religion)
- Location is used at state level only (no postcode-level socioeconomic proxy)
- All predictions include uncertainty bands to communicate limitations
- No claims of accuracy beyond documented metrics

---

## Monitoring

- Monthly MAE evaluation will begin after fresh labelled snapshots exist
- Drift evaluation only runs on snapshots later than the artifact's training boundary; with no new
  snapshot it records `no_new_snapshot` instead of claiming that drift was absent
- All monitoring logged in docs/MONITORING.md
- Retrain decisions documented in CHANGELOG.md
