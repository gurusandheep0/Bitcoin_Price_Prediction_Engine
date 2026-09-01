# Model governance

## Decision rule

Candidate selection and final evidence serve different purposes:

1. Elastic Net, Random Forest, and Histogram Gradient Boosting are compared using five expanding time splits inside the older training window.
2. The lowest average CV MAE chooses the candidate. The final holdout is not used for this choice.
3. The selected candidate is compared with the persistence baseline on the untouched later holdout.
4. The deployment label is `challenger_beats_baseline` only when the selected model's holdout MAE is lower.
5. Otherwise, the label is `research_only_baseline_leads`.

## Current model card

| Property | Value |
|---|---|
| Selected candidate | Random Forest |
| Selection metric | expanding-window CV MAE |
| Final evidence window | 2025-05-08 through 2026-08-31 |
| Holdout samples | 481 |
| Model holdout MAE | $1,359.95 |
| Persistence holdout MAE | $1,340.47 |
| Relative improvement | -1.453% |
| Governance state | `research_only_baseline_leads` |

The project does not switch to Elastic Net after observing that it has a slightly lower holdout error. Doing so would use final evidence for model selection and weaken the independence of the report.

## Interpreting the metrics

- **MAE** is the primary final comparison because its USD scale is easy to interpret.
- **RMSE** gives larger misses more weight.
- **MAPE** normalizes error by the actual close but can still be misleading across regimes.
- **R²** is reported but is not a deployment criterion; persistent price levels can create a high R² without useful excess predictive value.
- **Directional agreement** checks only whether the predicted and actual moves have the same sign.
- **Interval coverage** is retrospective empirical coverage, not a guaranteed probability for the next observation.

## Intended use

- Educational time-series forecasting
- Regression and baseline comparison
- Reproducible model-evaluation demonstrations
- API and dashboard delivery examples

## Prohibited or unsupported use

- Autonomous trading
- Investment advice
- Return guarantees
- High-frequency or intraday decisions
- Claims of production readiness based only on these metrics
