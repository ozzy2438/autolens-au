# AutoLens AU — Model Monitoring Framework

## Overview

This document describes the model monitoring strategy for AutoLens AU.
The goal is to detect performance degradation early and maintain reliable
valuations over time.

---

## Monitoring Metrics

| Metric | Baseline | Alert Threshold | Action |
|--------|----------|-----------------|--------|
| MAE (overall) | Pending first verified run | >5% above measured baseline | Investigate |
| MAE (overall) | Pending first verified run | >10% above measured baseline | Retrain candidate |
| MdAPE | Pending first verified run | Defined after baseline review | Investigate |
| Coverage (80% PI) | Pending calibration | <75% after calibration | Recalibrate intervals |
| Data freshness | Monthly | >45 days stale | Alert |

---

## Drift Detection Strategy

### Performance Drift
Monthly evaluation of the production model on newly ingested data:
1. Score new listings with current model
2. Compare predicted vs actual (where actuals become available)
3. Compute MAE, MdAPE by segment
4. Compare against baseline stored in `models/artifacts/latest_metrics.json`

### Data Drift
Monitor input feature distributions:
- Brand mix (are new brands appearing?)
- Price distribution shifts
- Geographic distribution changes
- Average vehicle age trends

### Concept Drift
Vehicle pricing fundamentals can shift due to:
- Supply chain disruptions (e.g., COVID-era price spikes)
- Policy changes (EV incentives)
- Interest rate movements
- New model releases

---

## Monthly Monitoring Checklist

```markdown
## Month: [YYYY-MM]

- [ ] Pipeline refresh executed successfully
- [ ] dbt tests all passing
- [ ] Model scored on new data
- [ ] MAE within threshold: ____
- [ ] MdAPE within threshold: ____
- [ ] PI coverage calibrated: ____
- [ ] Data drift check: ____
- [ ] Decision: MONITOR / INVESTIGATE / RETRAIN
- [ ] Changelog updated
```

---

## Monitoring Log

### July 2026 (Pre-launch)
- No model trained
- No baseline metrics established
- Monitoring acceptance criteria documented only
- First monitoring entry is blocked on a verified training run and later labelled snapshot

---

## Retrain Triggers

Automatic retrain is triggered when:
1. MAE degrades >5% from baseline for 2 consecutive months
2. PI coverage drops below 75%
3. New data source is integrated
4. Force-retrain flag set in monthly_refresh workflow

## Retrain Process
1. Full pipeline refresh (latest data)
2. Train new model on expanded dataset
3. Evaluate on held-out test set
4. Compare metrics: new vs current production
5. If improved: deploy new model, update baseline
6. If not: keep current model, investigate data quality
7. Document decision in CHANGELOG.md
