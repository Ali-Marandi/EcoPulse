# Changelog

## 2.2.0 — Quality, Documentation & CI Improvements

### Fixed

- **Fuzzy Black-Scholes crash**: added `numpy` and `scipy` to `requirements.txt` — the fuzzy BS panel uses `scipy.stats.norm` and would fail at runtime without it.
- **Stale docstring**: `quant_pages.py` module docstring correctly documents all 12 page-builder functions.

### Changed

- **Smoke tests expanded**: validate all 12 quantitative page construction functions in CI, not just the 6 core pages.
- **CI workflow trigger**: added `pull_request` trigger so Windows validation runs on every PR, not just on tags.
- **README updated**: full documentation of the 12 quantitative analysis pages, quant_engine architecture, and updated module table.

## 2.1.0 — Full Quantitative Engine UI Coverage

### Added

- **12 quantitative analysis pages** exposing all 40+ classes from the `quant_engine` module (23 Python files, ~14,000 lines).
- **5 new interactive panels** in this release:
  - **Instrumental Variables (2SLS)** — Two-Stage Least Squares with weak-instrument F-statistic diagnostic.
  - **Double/Debiased ML** — Cross-fitted orthogonal moment ATE estimation with ridge regression base learner.
  - **Propensity Score Matching** — ATT estimation with caliper-constrained matching and histogram overlay.
  - **Fuzzy Black-Scholes** — Option pricing with triangular fuzzy volatility TFN, sensitivity curve and defuzzified centroid.
  - **Mechanism Design Analyzer** — Winner's Curse bid shading estimation and Revenue Equivalence Theorem check.

### Pages (18 total)

| # | Page | Models |
|---|------|--------|
| 7 | Macro Simulator | DSGE, Taylor Rule, Phillips Curve, Minsky Cycle, Kondratiev Wave |
| 8 | Risk Analytics | GARCH(1,1), Monte Carlo VaR/CVaR, Black-Litterman |
| 9 | Information Flow | Transfer Entropy, Prospect Theory, Disposition Effect |
| 10 | Time Series Lab | PCA, ARIMA, VAR, Granger Causality, CUSUM |
| 11 | Network & Anomaly | Financial Contagion, DebtRank, Beneish M-Score, Altman Z-Score |
| 12 | Political & Climate | ICRG, Sanctions, Climate VaR, Hotelling Rule, Innovation S-Curve |
| 13 | Markets & Pricing | Black-Scholes, Vasicek, CIR, Akerlof Lemons, Market Maker |
| 14 | Regulatory & EMH | Basel III, MiFID II, Dodd-Frank, EMH Tests, Fuzzy Credit |
| 15 | Causal & Epidemic | Causal DAG, DID, IV/2SLS, Double ML, PSM, SIR Model |
| 16 | Fuzzy Decision Lab | Fuzzy AHP, Fuzzy TOPSIS, ANFIS, Fuzzy BS, Fuzzy Portfolio |
| 17 | Advanced Markets | Spence Signalling, RS Screening, Auctions, Hull-White, Mechanism Design |
| 18 | Compliance Suite | MiFID II, Dodd-Frank, Event Study |

### Validation

- AST syntax: all files parse cleanly.
- Import verification: all 40+ quant_engine classes import successfully.
- Page count invariant: 18 addWidget = 18 sidebar items = 18 context labels.

## 1.1.0 — Commercial Evidence Foundations

### Added

- **Data Health lens** for each active indicator, including live/fallback state, observation count and transparent readiness score.
- **Scenario Library** displaying saved scenarios with country, shock summary and save time from local workspace.
- **Decision Evidence Pack** in JSON format with data lineage, data health, latest observations, scenario, alerts, audit events and SHA-256 integrity checksum.
- **Local Guardrails Manifest** documenting current desktop boundaries, active controls and required enterprise control plane.
- Smoke test coverage for persistence, Data Health, Scenario Library and Evidence Pack integrity.

### Fixed

- SQLite connections now explicitly commit and close after each operation to prevent `WinError 32` cleanup issues on Windows runners.

### Changed

- Application version bumped to `1.1.0`.
- Dynamic tables correctly detach from parent after refresh to prevent visual overlap in Workspace, Audit, Benchmark and Scenario Studio.
- Product documentation updated to clarify local-only limitations and exact Enterprise boundaries.
