# AutoLens AU — Model Card

## Model Overview

| Field | Value |
|-------|-------|
| **Model Name** | AutoLens AU Hedonic Pricing Model |
| **Version** | 1.0.0 |
| **Type** | Regression (LightGBM Gradient Boosted Trees) |
| **Target** | log(price_aud) — reverted to AUD at prediction time |
| **Framework** | scikit-learn pipeline + LightGBM |
| **Last Trained** | July 2026 |
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
| Records | ~16,700 vehicle listings |
| Geography | Australia-wide (all states) |
| Time period | Primarily 2023 listings |
| Validation | Out-of-time split (train ≤ 2021, test > 2021) |

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
| body_type | Sedan, SUV, Hatchback, etc. |
| fuel_type | Petrol, Diesel, Hybrid, Electric |
| transmission | Automatic, Manual |
| drive_type | FWD, RWD, AWD, 4WD |
| condition | New, Used, Demo |
| state | Australian state/territory |

---

## Performance Metrics

### Overall (Out-of-Time Test Set)

| Metric | Value |
|--------|-------|
| MAE | ~$2,500 (target) |
| MdAPE | ~8% (target) |
| R² | ~0.85 (target) |
| Coverage (80% PI) | ~80% (target) |

### By Price Segment

| Segment | Expected MAE | Expected MdAPE |
|---------|-------------|----------------|
| Budget (<$15k) | ~$1,500 | ~12% |
| Mid ($15k-$40k) | ~$2,200 | ~7% |
| Premium ($40k-$80k) | ~$3,500 | ~6% |
| Luxury (>$80k) | ~$6,000 | ~8% |

*Note: These are target ranges. Actual metrics will be populated after first training run.*

---

## Known Limitations

1. **Condition granularity**: Public data lacks detailed condition scoring
2. **Variant/badge detail**: Model strings don't always distinguish trim levels
3. **Geographic bias**: Metro areas overrepresented vs regional
4. **Temporal**: Training data primarily from 2023; market shifts may not be captured
5. **Options/features**: Individual vehicle options (sunroof, leather, etc.) not modelled

---

## Ethical Considerations

- Model does not use protected characteristics (race, gender, religion)
- Location is used at state level only (no postcode-level socioeconomic proxy)
- All predictions include uncertainty bands to communicate limitations
- No claims of accuracy beyond documented metrics

---

## Monitoring

- Monthly MAE evaluation on fresh data
- Drift threshold: 5% MAE degradation triggers retrain
- All monitoring logged in docs/MONITORING.md
- Retrain decisions documented in CHANGELOG.md
