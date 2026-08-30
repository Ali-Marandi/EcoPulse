# Changelog

## 2.5.0 — Comprehensive Upgrade: Theme, i18n, Image Export, Import, Shortcuts

### Added

- **Dark/Light Theme Toggle**: Full light theme stylesheet with persistent toggle. Button in sidebar + Settings page. Ctrl+T shortcut. Main dashboard chart updates colors dynamically.
- **Persian (Farsi) i18n**: Complete Persian translation for all 18 sidebar items, buttons, and status labels. RTL layout support. Toggle between English and Persian with Ctrl+Shift+L or sidebar button.
- **PNG/SVG Chart Export**: 34 "Export Image" buttons across all quantitative pages. Uses pyqtgraph's ImageExporter (PNG at 1920px) and SVGExporter. Fallback to widget grab for complex layouts.
- **CSV Data Import**: Import user CSV files with numeric columns for analysis. Accessible from sidebar button. Supports pandas (if installed) or manual CSV parsing fallback. Data available for Time Series Lab.
- **Keyboard Shortcuts**: Ctrl+R (refresh data), Ctrl+T (toggle theme), Ctrl+E (export evidence), Ctrl+W (export chart image), Ctrl+1-9/0 (switch pages), Ctrl+Shift+L (toggle language).
- **Dashboard chart export button** in the top toolbar.
- **`_export_image_btn()` helper**: Generic reusable function for adding PNG/SVG export to any PlotWidget.
- **Settings page**: Theme and language controls with shortcut reference.

### Changed

- `app.py` grew from 1265 to ~1620 lines (+28%): theme system, i18n, shortcuts, import.
- `quant_pages.py` grew from 2575 to ~2640 lines: 34 image export buttons.
- All 82 existing tests still pass.
- `APP_VERSION` bumped to 2.5.0.

## 2.4.0 — Unit Tests & CSV Export

### Added

- **82 unit tests** covering all 21 quant_engine modules (previously 0 unit tests).
  - `tests/test_quant_batch1.py`: 36 tests for macro_models, garch, black_litterman, transfer_entropy, behavioral_finance, political_risk, anomaly_detection, market_microstructure, capital_structure, epidemiological_economics.
  - `tests/test_quant_batch2.py`: 46 tests for interest_rate_models, pca_factors, market_efficiency, regulatory_framework, time_series_advanced, causal_inference, fuzzy_advanced, fuzzy_credit, contagion_network, climate_risk, monte_carlo_risk.
- **CSV Export buttons** on 9 table/data panels: Monte Carlo, Black-Litterman, Basel III, EMH Tests, Transfer Entropy, ICRG Political Risk, Auction Mechanisms, Fuzzy AHP, Fuzzy TOPSIS.
- **`_export_csv_btn()` helper**: generic reusable export function supporting tables (list of rows), dicts (key-value or columnar), and 2D numpy arrays.

### Changed

- Added `QFileDialog`, `csv`, `os` imports to `quant_pages.py`.
- Test coverage: **0 → 82 tests**, all passing in ~5 seconds.

## 2.3.0 — Interactive Controls Upgrade (All 12 Quant Pages)

### Added

- **31 new sliders and 11 new action buttons** across 7 previously static pages, turning display-only panels into interactive analysis tools.
- **Risk Analytics**: GARCH VaR confidence slider, Monte Carlo paths/confidence/steps sliders with Run Simulation button.
- **Information Flow**: Transfer Entropy lag and bins sliders with Compute button, Prospect Theory α/β/λ sliders for real-time value function reshaping.
- **Time Series Lab**: ARIMA (p,d,q) order sliders and forecast horizon slider with Run ARIMA button, PCA variance threshold slider with Run PCA button.
- **Political & Climate**: Sanction severity/duration/trade-dependency sliders, Hotelling initial-price/cost/discount-rate sliders, Bass innovation/imitation coefficient sliders — all with Run buttons.
- **Fuzzy Decision Lab**: Run buttons for Fuzzy AHP and Fuzzy TOPSIS to recompute with fresh random pairwise comparisons.
- **Advanced Markets**: Mechanism Design n_bidders and value_std sliders, Trade-Off Theory bankruptcy-beta and tax-rate sliders with Run buttons.
- **Compliance Suite**: Event Study event-day and abnormal-return-effect sliders, Dodd-Frank trading-revenue and total-revenue sliders with Run buttons.

### Changed

- **Interactive element counts**: Sliders 15→46 (+207%), PushButtons ~10→21 (+110%), Signal connections 10→27 (+170%).
- **All 12 quantitative pages now have interactive controls** (previously 5 of 12 were interactive).

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
