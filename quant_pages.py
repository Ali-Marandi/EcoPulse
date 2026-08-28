"""EcoPulse Quant Pages — advanced quantitative model panels.

Three page-builder functions that expose the quant_engine models through the
customary EcoPulse dark-theme UI patterns (frame, make_table, SectionTitle,
pyqtgraph charts wrapped in QScrollArea).
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app import (
    ACCENT,
    ACCENT_DARK,
    AMBER,
    BLUE,
    CANVAS,
    DANGER,
    MUTED,
    SURFACE,
    TEXT,
    frame,
    make_table,
    SectionTitle,
)
from quant_engine import (
    TaylorRule,
    PhillipsCurve,
    DSGESimple,
    MinskyCycle,
    KondratievWave,
    GARCH11,
    MonteCarloRiskEngine,
    BlackLittermanModel,
    BlView,
    transfer_entropy,
    ProspectTheory,
    # New imports for expanded pages
    PCAFactorExtractor,
    fit_arima,
    fit_var,
    granger_causality_test,
    cusum_change_detection,
    FinancialNetwork,
    CorrelationNetwork,
    DebtRank,
    PriceManipulationDetector,
    AccountingFraudDetector,
    PoliticalRiskScore,
    SanctionImpactModel,
    ClimateVaR,
    HotellingRule,
    InnovationSCurve,
    BlackScholesModel,
    VasicekModel,
    CIRModel,
    MarketMakerModel,
    AkerlofLemonsModel,
    ModiglianiMiller,
    WACCCalculator,
    BaselIIICapital,
    BaselIIICompliance,
    WeakFormEMHTests,
    FuzzyCreditScorer,
    # Phase 2: remaining modules
    CausalDAG,
    DoubleML,
    DifferenceInDifferences,
    PropensityScoreMatching,
    SIRModel,
    EconomicImpactSIR,
    TFN,
    FuzzyAHP,
    FuzzyTOPSIS,
    FuzzyPortfolioOptimizer,
    FuzzyBlackScholes,
    SimplifiedANFIS,
    SpenceSignallingModel,
    RothschildStiglitzScreening,
    AuctionMechanism,
    HullWhiteModel,
    TradeOffTheory,
    PeckingOrderModel,
    MiFIDIIAnalyzer,
    DoddFrankAnalyzer,
    EventStudy,
    InstrumentalVariables,
    MechanismDesignAnalyzer,
)


# ------------------------------------------------------------------ helpers


def _styled_plot(min_height: int = 260) -> pg.PlotWidget:
    """Return a PlotWidget pre-configured with the EcoPulse dark theme."""
    pw = pg.PlotWidget()
    pw.setMinimumHeight(min_height)
    pw.setBackground(SURFACE)
    pw.showGrid(x=True, y=True, alpha=0.14)
    pw.getAxis("left").setTextPen(pg.mkPen(MUTED))
    pw.getAxis("bottom").setTextPen(pg.mkPen(MUTED))
    pw.getAxis("left").setPen(pg.mkPen("#2A3850"))
    pw.getAxis("bottom").setPen(pg.mkPen("#2A3850"))
    pw.setMouseEnabled(x=True, y=False)
    pw.addLegend(offset=(10, 10), labelTextColor=TEXT)
    return pw


def _slider_row(label: str, min_val: int, max_val: int, default: int, layout: QVBoxLayout, divisor: float = 1.0) -> tuple[QSlider, QLabel]:
    """Build a labeled slider row inside *layout* and return (slider, value_label)."""
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setObjectName("scenarioLabel")
    val_lbl = QLabel(f"{default / divisor:.2f}" if divisor != 1 else str(default))
    val_lbl.setObjectName("scenarioValue")
    val_lbl.setFixedWidth(60)
    row.addWidget(lbl)
    row.addStretch()
    row.addWidget(val_lbl)
    layout.addLayout(row)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(min_val, max_val)
    slider.setValue(default)
    slider.setTickInterval(max(1, (max_val - min_val) // 4))
    layout.addWidget(slider)

    def _update(v: int) -> None:
        val_lbl.setText(f"{v / divisor:.2f}" if divisor != 1 else str(v))

    slider.valueChanged.connect(_update)
    return slider, val_lbl


def _scroll_wrapper() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    inner.setObjectName("page")
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(0, 0, 4, 0)
    layout.setSpacing(18)
    scroll.setWidget(inner)
    return scroll, inner, layout


def _extract_values(data: dict, key: str) -> np.ndarray:
    """Extract values array from current_data dict."""
    pts = data.get(key, [])
    return np.array([p.value for p in pts]) if pts else np.array([])


# ======================================================================
# Page 1: Macro Simulator
# ======================================================================


def build_macro_simulator_page(parent: QWidget) -> QWidget:
    """Interactive macro simulation dashboard: Taylor Rule, Phillips Curve,
    DSGE shocks, Minsky Cycle, Kondratiev Wave."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Quantitative models",
        "Macro Simulator",
        "Explore macroeconomic models interactively: Taylor Rule, Phillips Curve, DSGE shock response, Minsky Financial Instability Hypothesis and long-wave Kondratiev cycles.",
    ))

    # ---- Panel 1: Taylor Rule Calculator ----
    tr_panel, tr_lay = frame("Taylor Rule Calculator", "i_t = r* + π* + φ_π(π_t − π*) + φ_y(y_t). Adjust parameters and observe the implied policy rate.")
    s_nr, _ = _slider_row("Neutral rate r* (%)", 0, 100, 20, tr_lay, divisor=10)
    s_phi_pi, _ = _slider_row("φ_π (inflation response)", 5, 30, 15, tr_lay, divisor=10)
    s_phi_y, _ = _slider_row("φ_y (output gap response)", 0, 10, 5, tr_lay, divisor=10)
    s_infl, _ = _slider_row("Current inflation π_t (%)", 0, 200, 30, tr_lay, divisor=10)
    s_gap, _ = _slider_row("Output gap y_t (%)", -50, 50, 0, tr_lay, divisor=10)
    tr_result = QLabel("—")
    tr_result.setObjectName("metricValue")
    tr_result.setStyleSheet(f"color: {ACCENT};")
    tr_lay.addWidget(tr_result)
    tr_lay.addStretch()

    def _update_taylor() -> None:
        try:
            rate = TaylorRule(
                neutral_rate=s_nr.value() / 10,
                inflation_target=2.0,
                phi_pi=s_phi_pi.value() / 10,
                phi_y=s_phi_y.value() / 10,
            ).predict_rate(s_infl.value() / 10, s_gap.value() / 10)
            tr_result.setText(f"Implied policy rate: {float(rate):.2f}%")
        except Exception:
            tr_result.setText("Error computing rate")

    for s in (s_nr, s_phi_pi, s_phi_y, s_infl, s_gap):
        s.valueChanged.connect(_update_taylor)
    _update_taylor()
    root.addWidget(tr_panel)

    # ---- Panel 2: Phillips Curve ----
    pc_panel, pc_lay = frame("Phillips Curve", "π_t = π^e − α(u_t − u*) + supply_shock. Predict inflation from unemployment dynamics.")
    s_pi_exp, _ = _slider_row("Expected inflation π^e (%)", 0, 150, 25, pc_lay, divisor=10)
    s_u_nat, _ = _slider_row("Natural unemployment u* (%)", 0, 150, 50, pc_lay, divisor=10)
    s_u_cur, _ = _slider_row("Current unemployment u_t (%)", 0, 200, 50, pc_lay, divisor=10)
    pc_result = QLabel("—")
    pc_result.setObjectName("metricValue")
    pc_result.setStyleSheet(f"color: {AMBER};")
    pc_lay.addWidget(pc_result)
    pc_lay.addStretch()

    def _update_pc() -> None:
        try:
            pi = PhillipsCurve(
                expected_inflation=s_pi_exp.value() / 10,
                natural_unemployment=s_u_nat.value() / 10,
                alpha=0.5,
            ).predict_inflation(s_u_cur.value() / 10)
            pc_result.setText(f"Predicted inflation: {float(pi):.2f}%")
        except Exception:
            pc_result.setText("Error computing inflation")

    for s in (s_pi_exp, s_u_nat, s_u_cur):
        s.valueChanged.connect(_update_pc)
    _update_pc()
    root.addWidget(pc_panel)

    # ---- Panel 3: DSGE Shock Simulation ----
    dsge_panel, dsge_lay = frame("DSGE Shock Simulation", "3-equation New Keynesian DSGE model. Apply monetary, demand or supply shocks and observe the dynamic response.")
    btn_row = QHBoxLayout()
    btn_m = QPushButton("Monetary Shock (+0.5%)")
    btn_m.setObjectName("secondaryButton")
    btn_d = QPushButton("Demand Shock (−1%)")
    btn_d.setObjectName("secondaryButton")
    btn_s = QPushButton("Supply Shock (+1%)")
    btn_s.setObjectName("secondaryButton")
    btn_row.addWidget(btn_m)
    btn_row.addWidget(btn_d)
    btn_row.addWidget(btn_s)
    dsge_lay.addLayout(btn_row)
    dsge_plot = _styled_plot(300)
    dsge_lay.addWidget(dsge_plot, 1)
    dsge_lay.addStretch()
    root.addWidget(dsge_panel)

    def _run_dsge(shock_type: str) -> None:
        try:
            periods = 40
            model = DSGESimple()
            ms = np.zeros(periods)
            ds = np.zeros(periods)
            ss = np.zeros(periods)
            if shock_type == "monetary":
                ms[5] = 0.5
            elif shock_type == "demand":
                ds[5] = -1.0
            else:
                ss[5] = 1.0
            res = model.simulate_shocks(ms, ds, ss, periods)
            x = np.arange(periods)
            dsge_plot.clear()
            dsge_plot.plot(x, res["output_gap"], pen=pg.mkPen(ACCENT, width=2), name="Output gap")
            dsge_plot.plot(x, res["inflation"], pen=pg.mkPen(AMBER, width=2), name="Inflation")
            dsge_plot.plot(x, res["interest_rate"], pen=pg.mkPen(BLUE, width=2), name="Interest rate")
            dsge_plot.setLabel("left", "%")
            dsge_plot.setLabel("bottom", "Period")
            dsge_plot.setTitle(f"DSGE Response · {shock_type.title()} Shock", color=TEXT, size="12pt")
        except Exception as exc:
            dsge_plot.clear()
            dsge_plot.setTitle(f"Error: {exc}", color=DANGER, size="12pt")

    btn_m.clicked.connect(lambda: _run_dsge("monetary"))
    btn_d.clicked.connect(lambda: _run_dsge("demand"))
    btn_s.clicked.connect(lambda: _run_dsge("supply"))

    # ---- Panel 4: Minsky Cycle Indicator ----
    minsky_panel, minsky_lay = frame("Minsky Cycle Indicator", "Financial Instability Hypothesis: Hedge → Speculative → Ponzi → Crisis cycle with credit and leverage dynamics.")
    minsky_plot = _styled_plot(300)
    minsky_lay.addWidget(minsky_plot, 1)
    # Phase legend
    phase_row = QHBoxLayout()
    phase_colors = {"HEDGE": ACCENT, "SPECULATIVE": AMBER, "PONZI": DANGER, "CRISIS": "#8B0000"}
    for name, color in phase_colors.items():
        lbl = QLabel(f"● {name}")
        lbl.setStyleSheet(f"color: {color}; font-weight: 700;")
        phase_row.addWidget(lbl)
    phase_row.addStretch()
    minsky_lay.addLayout(phase_row)
    minsky_lay.addStretch()
    root.addWidget(minsky_panel)

    try:
        mc = MinskyCycle()
        sim = mc.simulate(credit_growth_initial=0.03, periods=60)
        x = np.arange(60)
        credit = np.array([float(r[0]) for r in sim])
        leverage = np.array([float(r[1]) for r in sim])
        phases = [str(r[2]) for r in sim]
        minsky_plot.clear()
        minsky_plot.addLegend(offset=(10, 10), labelTextColor=TEXT)
        minsky_plot.plot(x, credit, pen=pg.mkPen(BLUE, width=2), name="Credit")
        minsky_plot.plot(x, leverage * 100, pen=pg.mkPen(AMBER, width=2), name="Leverage (×100)")
        # Shade phase regions
        phase_start = 0
        current_phase = phases[0]
        for t in range(1, len(phases)):
            if phases[t] != current_phase or t == len(phases) - 1:
                end = t if phases[t] != current_phase else t + 1
                color = phase_colors.get(current_phase, MUTED)
                minsky_plot.addItem(
                    pg.LinearRegionItem(
                        [phase_start, end],
                        brush=pg.mkBrush(QColor(color).darker(350)),
                        movable=False,
                    )
                )
                phase_start = t
                current_phase = phases[t]
        minsky_plot.setLabel("left", "Level")
        minsky_plot.setLabel("bottom", "Period")
        minsky_plot.setTitle("Minsky Financial Instability Cycle", color=TEXT, size="12pt")
    except Exception as exc:
        minsky_plot.setTitle(f"Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 5: Kondratiev Wave ----
    kw_panel, kw_lay = frame("Kondratiev Wave", "Long-wave ~54-year economic cycles driven by innovation waves and creative destruction, spanning 120 years.")
    kw_plot = _styled_plot(300)
    kw_lay.addWidget(kw_plot, 1)
    kw_lay.addStretch()
    root.addWidget(kw_panel)

    try:
        kw = KondratievWave()
        res = kw.generate_wave(start_year=1900, end_year=2020)
        kw_plot.clear()
        kw_plot.plot(res["years"], res["wave"], pen=pg.mkPen(ACCENT, width=2), name="K-Wave")
        # Shade phases
        phase_colors_kw = {"Prosperity": ACCENT, "Stagnation": AMBER, "Recession": DANGER}
        prev_phase = str(res["phase"][0])
        seg_start = int(res["years"][0])
        for i in range(1, len(res["years"])):
            yr = int(res["years"][i])
            ph = str(res["phase"][i])
            if ph != prev_phase or i == len(res["years"]) - 1:
                end_yr = yr if ph != prev_phase else yr + 1
                c = phase_colors_kw.get(prev_phase, MUTED)
                kw_plot.addItem(
                    pg.LinearRegionItem(
                        [seg_start, end_yr],
                        brush=pg.mkBrush(QColor(c).darker(400)),
                        movable=False,
                    )
                )
                seg_start = yr
                prev_phase = ph
        kw_plot.setLabel("left", "Normalised wave")
        kw_plot.setLabel("bottom", "Year")
        kw_plot.setTitle("Kondratiev Long-Wave Cycle (1900–2020)", color=TEXT, size="12pt")
    except Exception as exc:
        kw_plot.setTitle(f"Error: {exc}", color=DANGER, size="12pt")

    root.addStretch()
    return scroll


# ======================================================================
# Page 2: Risk Analytics
# ======================================================================


def build_risk_analytics_page(parent: QWidget) -> QWidget:
    """Risk analytics: GARCH volatility, Monte Carlo simulation,
    Black-Litterman portfolio optimisation."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Risk quantification",
        "Risk Analytics",
        "Volatility modelling with GARCH(1,1), Monte Carlo portfolio simulation with VaR/CVaR, and Black-Litterman Bayesian portfolio allocation.",
    ))

    # ---- Panel 1: GARCH Volatility ----
    garch_panel, garch_lay = frame("GARCH(1,1) Volatility Model", "Fit GARCH(1,1) to GDP growth data. Shows conditional volatility, VaR and CVaR at 95% confidence.")
    garch_plot = _styled_plot(280)
    garch_lay.addWidget(garch_plot, 1)
    garch_info = QLabel("Computing…")
    garch_info.setObjectName("panelSubtitle")
    garch_info.setWordWrap(True)
    garch_lay.addWidget(garch_info)
    garch_lay.addStretch()
    root.addWidget(garch_panel)

    try:
        data = parent.current_data if parent.current_data else {}
        gdp_values = _extract_values(data, "gdp")
        if len(gdp_values) >= 12:
            returns = np.diff(gdp_values) / np.abs(gdp_values[:-1]) * 100
            returns = returns - np.mean(returns)  # demean
            garch = GARCH11(returns).fit()
            sigma_cond = np.sqrt(garch.conditional_sigma2)
            var95 = garch.var(confidence=0.95)
            cvar95 = garch.cvar(confidence=0.95)
            x = np.arange(len(returns))
            garch_plot.clear()
            garch_plot.plot(x, returns, pen=pg.mkPen(BLUE, width=1.5), name="GDP returns")
            garch_plot.plot(x, sigma_cond, pen=pg.mkPen(AMBER, width=2), name="Cond. volatility σ")
            garch_plot.plot(x, -sigma_cond, pen=pg.mkPen(AMBER, width=2))
            garch_plot.addLine(y=var95, pen=pg.mkPen(DANGER, width=1, style=Qt.PenStyle.DashLine), label=f"VaR(95%)={var95:.4f}")
            garch_plot.setLabel("left", "%")
            garch_plot.setLabel("bottom", "Period")
            garch_plot.setTitle("GARCH(1,1) Conditional Volatility", color=TEXT, size="12pt")
            persistence = garch.alpha + garch.beta
            garch_info.setText(
                f"ω = {garch.omega:.6f}  ·  α = {garch.alpha:.4f}  ·  β = {garch.beta:.4f}  ·  "
                f"Persistence (α+β) = {persistence:.4f}  ·  VaR(95%) = {var95:.4f}  ·  CVaR(95%) = {cvar95:.4f}"
            )
        else:
            garch_plot.clear()
            garch_plot.setTitle("Insufficient data — need ≥ 12 GDP observations", color=AMBER, size="12pt")
            garch_info.setText("Load a country dataset via the top bar to enable GARCH fitting.")
    except Exception as exc:
        garch_plot.clear()
        garch_plot.setTitle(f"GARCH Error: {exc}", color=DANGER, size="12pt")
        garch_info.setText(str(exc))

    # ---- Panel 2: Monte Carlo Portfolio Simulation ----
    mc_panel, mc_lay = frame("Monte Carlo Portfolio Simulation", "Simulate 50 correlated GBM paths for a 4-asset portfolio. Shows VaR, CVaR and portfolio standard deviation.")
    mc_plot = _styled_plot(300)
    mc_lay.addWidget(mc_plot, 1)
    mc_info = QLabel("Computing…")
    mc_info.setObjectName("panelSubtitle")
    mc_info.setWordWrap(True)
    mc_lay.addWidget(mc_info)
    mc_lay.addStretch()
    root.addWidget(mc_panel)

    try:
        data = parent.current_data if parent.current_data else {}
        gdp_v = _extract_values(data, "gdp")
        infl_v = _extract_values(data, "inflation")
        unemp_v = _extract_values(data, "unemployment")
        inv_v = _extract_values(data, "investment")

        # Seed the portfolio with actual data stats where available, otherwise synthetic
        def _safe_mu(arr, default, scale=0.05):
            if len(arr) >= 4:
                return np.mean(np.diff(arr) / 100) * 252 if np.mean(np.abs(arr)) > 10 else np.mean(arr) / 100
            return default

        def _safe_sigma(arr, default):
            if len(arr) >= 4:
                return max(np.std(arr) / 100, 0.05)
            return default

        mu_vec = np.array([
            _safe_mu(gdp_v, 0.08),
            _safe_mu(infl_v, 0.03),
            _safe_mu(unemp_v, 0.02),
            _safe_mu(inv_v, 0.05),
        ])
        # Ensure reasonable drift
        mu_vec = np.clip(mu_vec, -0.05, 0.15)
        sigmas = np.array([
            _safe_sigma(gdp_v, 0.15),
            _safe_sigma(infl_v, 0.08),
            _safe_sigma(unemp_v, 0.06),
            _safe_sigma(inv_v, 0.12),
        ])
        # Build covariance matrix
        corr = np.array([
            [1.0, 0.3, -0.4, 0.5],
            [0.3, 1.0, 0.2, 0.1],
            [-0.4, 0.2, 1.0, -0.1],
            [0.5, 0.1, -0.1, 1.0],
        ])
        cov = np.outer(sigmas, sigmas) * corr
        weights = np.array([0.4, 0.2, 0.15, 0.25])

        engine = MonteCarloRiskEngine(weights, mu_vec, cov)
        sim = engine.simulate(T=1.0, n_steps=50, n_paths=50, seed=42)
        paths = sim["portfolio_paths"]  # (50, 51)

        mc_plot.clear()
        for i in range(min(50, paths.shape[0])):
            alpha_val = 80 if i < 10 else 30
            mc_plot.plot(np.arange(paths.shape[1]), paths[i], pen=pg.mkPen(BLUE, width=1))
        mc_plot.setLabel("left", "Portfolio value")
        mc_plot.setLabel("bottom", "Step")
        mc_plot.setTitle("50 Monte Carlo Portfolio Paths", color=TEXT, size="12pt")

        # Compute risk metrics
        report = engine.risk_report(confidence=0.95, n_paths=5000, seed=42)
        mc_var = report["monte_carlo"]["var"]
        mc_cvar = report["monte_carlo"]["cvar"]
        mc_std = report["monte_carlo"]["std_return"]
        mc_info.setText(
            f"VaR(95%) = {mc_var:.4f}  ·  CVaR(95%) = {mc_cvar:.4f}  ·  Portfolio Std = {mc_std:.4f}  ·  "
            f"Mean return = {report['monte_carlo']['mean_return']:.4f}"
        )
    except Exception as exc:
        mc_plot.clear()
        mc_plot.setTitle(f"Monte Carlo Error: {exc}", color=DANGER, size="12pt")
        mc_info.setText(str(exc))

    # ---- Panel 3: Black-Litterman Portfolio ----
    bl_panel, bl_lay = frame("Black-Litterman Portfolio", "Bayesian portfolio model combining market equilibrium with investor views. Shows implied vs. posterior expected returns.")
    bl_table = make_table(
        ["Asset", "Mkt Weight", "Implied μ", "View", "Posterior μ", "Δ"],
        [["Computing…", "", "", "", "", ""]],
    )
    bl_lay.addWidget(bl_table)
    bl_lay.addStretch()
    root.addWidget(bl_panel)

    try:
        tickers = ["Equity", "Bonds", "Commodities", "Real Estate"]
        N = len(tickers)
        w_mkt = np.array([0.45, 0.30, 0.12, 0.13])
        A = np.array([
            [0.040, 0.005, 0.010, 0.015],
            [0.005, 0.010, 0.002, 0.003],
            [0.010, 0.002, 0.025, 0.008],
            [0.015, 0.003, 0.008, 0.020],
        ])
        views = [
            BlView(asset="Equity", view_return=0.06, confidence=0.6),
            BlView(asset="Commodities", view_return=0.04, confidence=0.5),
            BlView(asset="Bonds", view_return=0.01, confidence=0.4, relative_to="Real Estate"),
        ]
        bl = BlackLittermanModel(market_cap_weights=w_mkt, covariance_matrix=A, risk_aversion=2.5, tau=0.05)
        result = bl.run(views, tickers)

        rows: list[list[str]] = []
        view_labels = ["+6% abs", "+4% abs", "+1% vs RE", "—"]
        for i, t in enumerate(tickers):
            imp = result["implied_returns"][i]
            post = result["posterior_returns"][i]
            delta = post - imp
            sign = "+" if delta >= 0 else ""
            rows.append([
                t,
                f"{w_mkt[i]:.1%}",
                f"{imp:.4%}",
                view_labels[i] if i < len(views) else "—",
                f"{post:.4%}",
                f"{sign}{delta:.4%}",
            ])
        new_bl_table = make_table(
            ["Asset", "Mkt Weight", "Implied μ", "View", "Posterior μ", "Δ"],
            rows,
        )
        parent_layout = bl_table.parentWidget().layout()
        parent_layout.replaceWidget(bl_table, new_bl_table)
        bl_table.hide()
        bl_table.setParent(None)
        bl_table.deleteLater()
    except Exception:
        pass

    root.addStretch()
    return scroll


# ======================================================================
# Page 3: Information Flow
# ======================================================================


def build_information_flow_page(parent: QWidget) -> QWidget:
    """Information flow analysis: Transfer Entropy matrix, bar chart,
    and Prospect Theory value function."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Behavioural & information models",
        "Information Flow",
        "Transfer entropy reveals directional information flow between macro indicators. Prospect theory models decision-making under risk.",
    ))

    # ---- Panel 1: Transfer Entropy Matrix ----
    te_panel, te_lay = frame("Transfer Entropy Matrix", "Measures directional information transfer between GDP, Inflation, Unemployment and Investment. Rows = target, columns = source.")
    names = ["GDP", "Inflation", "Unemployment", "Investment"]
    keys = ["gdp", "inflation", "unemployment", "investment"]
    data = parent.current_data if parent.current_data else {}
    has_data = all(len(data.get(k, [])) >= 12 for k in keys)

    if has_data:
        try:
            series_matrix = np.column_stack([_extract_values(data, k) for k in keys]).T  # (4, T)
            te_matrix = np.zeros((4, 4))
            for i in range(4):
                for j in range(4):
                    if i != j:
                        res = transfer_entropy(series_matrix[j], series_matrix[i], lag=1, bins=8)
                        te_matrix[i, j] = res["te"]

            # Build table rows with highlighting for column leaders
            te_rows: list[list[str]] = []
            for i in range(4):
                row: list[str] = []
                for j in range(4):
                    if i == j:
                        row.append("—")
                    else:
                        val = te_matrix[i, j]
                        # Check if this is the max in column j (leader→follower)
                        col_vals = [te_matrix[ii, j] for ii in range(4) if ii != j]
                        is_leader = val == max(col_vals) and val > 0
                        prefix = "▶ " if is_leader else "  "
                        row.append(f"{prefix}{val:.4f}")
                te_rows.append(row)
            te_table = make_table(["Target → Source"] + names, te_rows)
            te_lay.addWidget(te_table)

            # Explanation label
            te_note = QLabel("▶ marks the strongest information source for each target variable (highest TE in each column).")
            te_note.setObjectName("panelSubtitle")
            te_note.setWordWrap(True)
            te_lay.addWidget(te_note)
        except Exception as exc:
            te_lay.addWidget(QLabel(f"TE computation error: {exc}"))
    else:
        te_lay.addWidget(QLabel("No data loaded. Refresh a country dataset from the top bar to compute transfer entropy."))
    te_lay.addStretch()
    root.addWidget(te_panel)

    # ---- Panel 2: Information Flow Bar Chart ----
    bar_panel, bar_lay = frame("Information Flow Chart", "Bar chart of transfer entropy values. Taller bars indicate stronger directional information flow.")
    bar_plot = _styled_plot(280)
    bar_lay.addWidget(bar_plot, 1)
    bar_lay.addStretch()
    root.addWidget(bar_panel)

    if has_data:
        try:
            bar_plot.clear()
            # Show TE as grouped bars: for each target (group), show TE from each source
            n_pairs = 12  # 4x4 minus diagonal
            labels = []
            values = []
            colors = []
            color_map = [ACCENT, AMBER, BLUE, DANGER]
            idx = 0
            for i in range(4):
                for j in range(4):
                    if i == j:
                        continue
                    labels.append(f"{names[j][:3]}→{names[i][:3]}")
                    values.append(te_matrix[i, j])
                    colors.append(color_map[i])
                    idx += 1
            # Create bar chart
            bg = pg.BarGraphItem(x=np.arange(len(values)), height=values, width=0.7,
                                 brushes=[pg.mkBrush(QColor(c).darker(250)) for c in colors])
            bar_plot.addItem(bg)
            axis = bar_plot.getAxis("bottom")
            axis.setTicks([[(i, labels[i]) for i in range(len(labels))]])
            axis.setStyle(tickFont=QFont("Segoe UI", 7))
            bar_plot.setLabel("left", "TE (bits)")
            bar_plot.setTitle("Pairwise Transfer Entropy", color=TEXT, size="12pt")
        except Exception:
            bar_plot.setTitle("Could not render bar chart", color=AMBER, size="12pt")
    else:
        bar_plot.setTitle("No data available", color=AMBER, size="12pt")

    # ---- Panel 3: Prospect Theory Value Function ----
    pt_panel, pt_lay = frame("Prospect Theory Value Function", "Kahneman–Tversky S-shaped value function: v(x) = x^β for gains, v(x) = −λ|x|^α for losses. Note the kink at the origin (loss aversion).")
    pt_plot = _styled_plot(300)
    pt_lay.addWidget(pt_plot, 1)

    # Parameter display
    pt_params = QLabel("α = 0.88  ·  β = 0.88  ·  λ = 2.25")
    pt_params.setObjectName("panelSubtitle")
    pt_params.setStyleSheet(f"color: {ACCENT};")
    pt_lay.addWidget(pt_params)
    pt_lay.addStretch()
    root.addWidget(pt_panel)

    try:
        pt = ProspectTheory(alpha=0.88, beta=0.88, lambda_=2.25)
        x = np.linspace(-10, 10, 500)
        v = pt.value_function(x)
        pt_plot.clear()
        # Separate gains and losses for coloring
        mask_gain = x >= 0
        mask_loss = x < 0
        pt_plot.plot(x[mask_gain], v[mask_gain], pen=pg.mkPen(ACCENT, width=3), name="Gains")
        pt_plot.plot(x[mask_loss], v[mask_loss], pen=pg.mkPen(DANGER, width=3), name="Losses")
        # Reference line at origin
        pt_plot.addItem(
            pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        )
        pt_plot.addItem(
            pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        )
        # Expected utility line for comparison
        pt_plot.plot(x, x, pen=pg.mkPen("#555555", width=1, style=Qt.PenStyle.DotLine), name="EU (linear)")
        pt_plot.setLabel("left", "Subjective value v(x)")
        pt_plot.setLabel("bottom", "Outcome x")
        pt_plot.setTitle("Prospect Theory Value Function (loss aversion kink at origin)", color=TEXT, size="12pt")
    except Exception as exc:
        pt_plot.setTitle(f"Error: {exc}", color=DANGER, size="12pt")

    root.addStretch()
    return scroll


# ======================================================================
# Page 4: Time Series Lab
# ======================================================================


def build_time_series_lab_page(parent: QWidget) -> QWidget:
    """Time series analysis: PCA factors, ARIMA forecasting, Granger
    causality, CUSUM structural break detection."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Time series analysis",
        "Time Series Lab",
        "PCA factor extraction, ARIMA forecasting, Granger causality testing and CUSUM change-point detection on macro indicator data.",
    ))

    data = parent.current_data if parent.current_data else {}
    keys = ["gdp", "inflation", "unemployment", "investment"]
    names = ["GDP", "Inflation", "Unemployment", "Investment"]
    has_data = all(len(data.get(k, [])) >= 14 for k in keys)

    # ---- Panel 1: PCA Factor Extraction ----
    pca_panel, pca_lay = frame("PCA Factor Extraction", "Principal Component Analysis on macro indicator returns. Extracts dominant drivers of co-movement across GDP, Inflation, Unemployment and Investment.")
    pca_plot = _styled_plot(280)
    pca_lay.addWidget(pca_plot, 1)
    pca_info = QLabel("Waiting for data…")
    pca_info.setObjectName("panelSubtitle")
    pca_info.setWordWrap(True)
    pca_lay.addWidget(pca_info)
    pca_lay.addStretch()
    root.addWidget(pca_panel)

    if has_data:
        try:
            values = np.column_stack([_extract_values(data, k) for k in keys])
            returns = np.diff(values, axis=0) / (np.abs(values[:-1]) + 1e-8)
            pca = PCAFactorExtractor(n_components=0.90)
            result = pca.fit_transform(returns, asset_names=names)
            n_factors = len(result["factor_names"])
            x = np.arange(returns.shape[0])
            pca_plot.clear()
            colors_pca = [ACCENT, AMBER, BLUE, DANGER]
            for i in range(min(n_factors, 4)):
                pca_plot.plot(x, result["factors"][:, i], pen=pg.mkPen(colors_pca[i], width=2),
                              name=f"PC{i+1} ({result['explained_variance_ratio'][i]:.1%})")
            pca_plot.setLabel("left", "Factor value")
            pca_plot.setLabel("bottom", "Period")
            pca_plot.setTitle(f"PCA Factors — {n_factors} components explain {sum(result['explained_variance_ratio'][:n_factors]):.1%} of variance", color=TEXT, size="12pt")
            ev_text = "  ".join([f"PC{i+1}={result['explained_variance_ratio'][i]:.1%}" for i in range(n_factors)])
            pca_info.setText(f"Explained variance: {ev_text}")
        except Exception as exc:
            pca_plot.setTitle(f"PCA Error: {exc}", color=DANGER, size="12pt")
            pca_info.setText(str(exc))
    else:
        pca_plot.setTitle("Insufficient data — need ≥ 14 observations per indicator", color=AMBER, size="12pt")
        pca_info.setText("Load a country dataset via the top bar to enable PCA.")

    # ---- Panel 2: ARIMA Forecast ----
    arima_panel, arima_lay = frame("ARIMA Forecast (GDP)", "Fit ARIMA(1,1,1) to GDP growth data and produce a 10-step ahead forecast with 95% confidence interval.")
    arima_plot = _styled_plot(280)
    arima_lay.addWidget(arima_plot, 1)
    arima_info = QLabel("Waiting for data…")
    arima_info.setObjectName("panelSubtitle")
    arima_info.setWordWrap(True)
    arima_lay.addWidget(arima_info)
    arima_lay.addStretch()
    root.addWidget(arima_panel)

    gdp_vals = _extract_values(data, "gdp")
    if len(gdp_vals) >= 14:
        try:
            res = fit_arima(gdp_vals, order=(1, 1, 1), forecast_steps=10)
            hist_len = len(gdp_vals)
            fc_mean = res["forecast_mean"]
            fc_lo = res["forecast_ci"][:, 0]
            fc_hi = res["forecast_ci"][:, 1]
            x_all = np.arange(hist_len + 10)
            arima_plot.clear()
            arima_plot.plot(np.arange(hist_len), gdp_vals, pen=pg.mkPen(BLUE, width=2), name="Historical GDP")
            arima_plot.plot(np.arange(hist_len - 1, hist_len + 10), fc_mean, pen=pg.mkPen(ACCENT, width=2), name="Forecast")
            ci_region = pg.FillBetweenItem(
                pg.PlotDataItem(np.arange(hist_len - 1, hist_len + 10), fc_hi),
                pg.PlotDataItem(np.arange(hist_len - 1, hist_len + 10), fc_lo),
                brush=pg.mkBrush(QColor(ACCENT).darker(400)),
            )
            arima_plot.addItem(ci_region)
            arima_plot.setLabel("left", "%")
            arima_plot.setLabel("bottom", "Period")
            arima_plot.setTitle("ARIMA(1,1,1) GDP Forecast", color=TEXT, size="12pt")
            arima_info.setText(
                f"AIC = {res['aic']:.2f}  ·  BIC = {res['bic']:.2f}  ·  "
                f"σ²(residuals) = {np.var(res['residuals']):.4f}"
            )
        except Exception as exc:
            arima_plot.setTitle(f"ARIMA Error: {exc}", color=DANGER, size="12pt")
            arima_info.setText(str(exc))
    else:
        arima_plot.setTitle("Insufficient data — need ≥ 14 GDP observations", color=AMBER, size="12pt")
        arima_info.setText("Load a country dataset via the top bar.")

    # ---- Panel 3: Granger Causality Matrix ----
    gc_panel, gc_lay = frame("Granger Causality Matrix", "Tests whether each indicator Granger-causes every other indicator (lag=2, 5% significance). Directional predictive relationships revealed.")
    if has_data:
        try:
            gc_rows = []
            for i, target_k in enumerate(keys):
                row: list[str] = []
                for j, source_k in enumerate(keys):
                    if i == j:
                        row.append("—")
                    else:
                        res_gc = granger_causality_test(
                            _extract_values(data, target_k),
                            _extract_values(data, source_k),
                            maxlag=2, significance=0.05,
                        )
                        marker = "Yes" if res_gc["is_significant"] else "No"
                        p_str = f"{res_gc.get('f_pvalue', 0):.3f}" if 'f_pvalue' in res_gc else "N/A"
                        row.append(f"{marker} (p={p_str})")
                gc_rows.append(row)
            gc_lay.addWidget(make_table(["Target \u2192 Source"] + [n[:4] for n in names], gc_rows))
            gc_lay.addWidget(QLabel("Yes = Granger-causes at 5% significance (F-test).  No = no evidence of causality."))
        except Exception as exc:
            gc_lay.addWidget(QLabel(f"Granger error: {exc}"))
    else:
        gc_lay.addWidget(QLabel("No data loaded. Refresh a country dataset to compute Granger causality."))
    gc_lay.addStretch()
    root.addWidget(gc_panel)

    # ---- Panel 4: CUSUM Change Detection ----
    cusum_panel, cusum_lay = frame("CUSUM Structural Break Detection", "Detect structural breaks in the GDP growth series using the CUSUM statistic.")
    cusum_plot = _styled_plot(250)
    cusum_lay.addWidget(cusum_plot, 1)
    cusum_info = QLabel("Waiting…")
    cusum_info.setObjectName("panelSubtitle")
    cusum_info.setWordWrap(True)
    cusum_lay.addWidget(cusum_info)
    cusum_lay.addStretch()
    root.addWidget(cusum_panel)

    if len(gdp_vals) >= 14:
        try:
            res_cu = cusum_change_detection(gdp_vals, threshold=1.0)
            x_cu = np.arange(len(gdp_vals))
            cusum_plot.clear()
            cusum_plot.plot(x_cu, res_cu["cusum_stat"], pen=pg.mkPen(ACCENT, width=2), name="CUSUM")
            cusum_plot.addLine(y=1.0, pen=pg.mkPen(DANGER, width=1, style=Qt.PenStyle.DashLine), label="Threshold")
            cusum_plot.addLine(y=-1.0, pen=pg.mkPen(DANGER, width=1, style=Qt.PenStyle.DashLine))
            for cp in res_cu.get("change_points", []):
                cusum_plot.addItem(pg.InfiniteLine(pos=cp, angle=90, pen=pg.mkPen(AMBER, width=1.5, style=Qt.PenStyle.DotLine)))
            cusum_plot.setLabel("bottom", "Period")
            cusum_plot.setTitle(f"CUSUM Test — {len(res_cu.get('change_points', []))} change point(s) detected", color=TEXT, size="12pt")
            cps = res_cu.get("change_points", [])
            cusum_info.setText(f"Change points at indices: {cps}  ·  In-control mean: {res_cu.get('in_control_mean', 0):.2f}")
        except Exception as exc:
            cusum_plot.setTitle(f"CUSUM Error: {exc}", color=DANGER, size="12pt")
            cusum_info.setText(str(exc))
    else:
        cusum_plot.setTitle("Insufficient data", color=AMBER, size="12pt")

    root.addStretch()
    return scroll


# ======================================================================
# Page 5: Network & Anomaly
# ======================================================================


def build_network_anomaly_page(parent: QWidget) -> QWidget:
    """Financial contagion networks, anomaly detection and fraud scoring."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Network risk & anomaly detection",
        "Network & Anomaly",
        "Systemic contagion via DebtRank, correlation-based community detection, price manipulation signals and Beneish/Altman fraud scores.",
    ))

    # ---- Panel 1: Financial Contagion ----
    contagion_panel, contagion_lay = frame("Financial Contagion Simulation", "Erdos-Renyi interbank network with cascading default simulation. Shock one bank and observe systemic propagation via DebtRank.")
    contagion_plot = _styled_plot(300)
    contagion_lay.addWidget(contagion_plot, 1)
    contagion_info = QLabel("Computing…")
    contagion_info.setObjectName("panelSubtitle")
    contagion_info.setWordWrap(True)
    contagion_lay.addWidget(contagion_info)

    btn_row_c = QHBoxLayout()
    btn_shock0 = QPushButton("Shock Bank 0")
    btn_shock0.setObjectName("secondaryButton")
    btn_shock1 = QPushButton("Shock Bank 3")
    btn_shock1.setObjectName("secondaryButton")
    btn_shock2 = QPushButton("Shock Bank 6")
    btn_shock2.setObjectName("secondaryButton")
    btn_row_c.addWidget(btn_shock0)
    btn_row_c.addWidget(btn_shock1)
    btn_row_c.addWidget(btn_shock2)
    contagion_lay.addLayout(btn_row_c)
    contagion_lay.addStretch()
    root.addWidget(contagion_panel)

    net_cache = {"network": None}

    def _ensure_network():
        if net_cache["network"] is None:
            net_cache["network"] = FinancialNetwork(n_banks=10, connectivity_prob=0.2, seed=42)
        return net_cache["network"]

    def _run_contagion(bank_idx: int) -> None:
        try:
            net = _ensure_network()
            result = net.simulate_contagion(initial_shock_bank=bank_idx, threshold=0.5)
            metrics = net.systemic_risk_metrics()
            n_def = result["n_defaults"]
            contagion_plot.clear()
            losses = np.array(result["losses"])
            colors_bars = [DANGER if d else BLUE for d in result["defaulted_mask"]]
            bg = pg.BarGraphItem(x=np.arange(len(losses)), height=losses, width=0.6,
                                 brushes=[pg.mkBrush(QColor(c).darker(200)) for c in colors_bars])
            contagion_plot.addItem(bg)
            contagion_plot.setLabel("left", "Loss")
            contagion_plot.setLabel("bottom", "Bank")
            contagion_plot.setTitle(f"Contagion from Bank {bank_idx} — {n_def} default(s)", color=TEXT, size="12pt")
            contagion_info.setText(
                f"Defaults: {n_def}/10  ·  Total loss: {sum(losses):.2f}  ·  "
                f"Avg degree centrality: {np.mean(metrics.get('degree_centrality', [0])):.3f}"
            )
        except Exception as exc:
            contagion_plot.setTitle(f"Contagion error: {exc}", color=DANGER, size="12pt")

    btn_shock0.clicked.connect(lambda: _run_contagion(0))
    btn_shock1.clicked.connect(lambda: _run_contagion(3))
    btn_shock2.clicked.connect(lambda: _run_contagion(6))
    _run_contagion(0)

    # ---- Panel 2: Price Anomaly Detection ----
    anomaly_panel, anomaly_lay = frame("Price Manipulation Detection", "Multi-signal anomaly detector: volume spikes, price velocity, painting-the-tape and spoofing signals.")
    anomaly_plot = _styled_plot(280)
    anomaly_lay.addWidget(anomaly_plot, 1)
    anomaly_info = QLabel("Computing…")
    anomaly_info.setObjectName("panelSubtitle")
    anomaly_info.setWordWrap(True)
    anomaly_lay.addWidget(anomaly_info)
    anomaly_lay.addStretch()
    root.addWidget(anomaly_panel)

    try:
        np.random.seed(123)
        n_pts = 120
        prices = 100 + np.cumsum(np.random.normal(0.05, 1.2, n_pts))
        volumes = np.random.lognormal(3.0, 0.5, n_pts).astype(float)
        # Inject anomalies
        volumes[40:45] *= 4.0
        prices[80] += 8.0
        detector = PriceManipulationDetector()
        result_det = detector.detect_all(prices, volumes)
        x_det = np.arange(n_pts)
        anomaly_plot.clear()
        anomaly_plot.plot(x_det, prices, pen=pg.mkPen(BLUE, width=1.5), name="Price")
        # Highlight anomalies
        if "volume_anomaly" in result_det and result_det["volume_anomaly"].get("anomalies"):
            for idx in result_det["volume_anomaly"]["anomalies"]:
                anomaly_plot.addItem(pg.ScatterPlotItem([idx], [prices[idx]], pen=pg.mkPen(None),
                                                        brush=pg.mkBrush(DANGER), size=10))
        if "price_velocity" in result_det and result_det["price_velocity"].get("anomalies"):
            for idx in result_det["price_velocity"]["anomalies"]:
                anomaly_plot.addItem(pg.ScatterPlotItem([idx], [prices[idx]], pen=pg.mkPen(None),
                                                        brush=pg.mkBrush(AMBER), size=10))
        anomaly_plot.setLabel("left", "Price")
        anomaly_plot.setLabel("bottom", "Period")
        anomaly_plot.setTitle(f"Anomaly Scan — {result_det.get('anomaly_count', 0)} signal(s)", color=TEXT, size="12pt")
        anomaly_info.setText(
            f"Combined score: {result_det.get('combined_score', 0):.2f}  ·  "
            f"Volume anomalies: {len(result_det.get('volume_anomaly', {}).get('anomalies', []))}  ·  "
            f"Velocity anomalies: {len(result_det.get('price_velocity', {}).get('anomalies', []))}"
        )
    except Exception as exc:
        anomaly_plot.setTitle(f"Anomaly error: {exc}", color=DANGER, size="12pt")
        anomaly_info.setText(str(exc))

    # ---- Panel 3: Beneish M-Score & Altman Z-Score ----
    fraud_panel, fraud_lay = frame("Accounting Fraud Detection", "Beneish M-Score for earnings manipulation probability. Altman Z-Score for bankruptcy risk.")
    m_result = QLabel("Computing…")
    m_result.setObjectName("metricValue")
    m_result.setStyleSheet(f"color: {DANGER};")
    m_result.setWordWrap(True)
    fraud_lay.addWidget(m_result)

    z_result = QLabel("Computing…")
    z_result.setObjectName("metricValue")
    z_result.setStyleSheet(f"color: {AMBER};")
    z_result.setWordWrap(True)
    fraud_lay.addWidget(z_result)
    fraud_lay.addStretch()
    root.addWidget(fraud_panel)

    try:
        fraud_det = AccountingFraudDetector()
        m_score_res = fraud_det.compute_m_score({
            "DSRI": 1.15, "GMI": 0.95, "AQI": 1.10,
            "SGI": 1.25, "DEPI": 1.08, "SGAI": 1.05,
            "TATA": 0.04, "LVGI": 1.12,
        })
        m_result.setText(
            f"Beneish M-Score: {m_score_res['m_score']:.4f}  ·  "
            f"Manipulation prob: {m_score_res['probability']:.1%}  ·  {m_score_res['interpretation']}"
        )
        z_res = fraud_det.altman_z_score(
            working_capital=300, total_assets=2000, retained_earnings=400,
            ebit=250, market_cap=1500, total_liabilities=800, sales=3000,
        )
        z_result.setText(
            f"Altman Z-Score: {z_res['z_score']:.2f}  ·  Zone: {z_res['zone']}  ·  "
            f"Bankruptcy prob: {z_res.get('bankruptcy_prob', 'N/A')}"
        )
    except Exception as exc:
        m_result.setText(f"Fraud detection error: {exc}")

    root.addStretch()
    return scroll


# ======================================================================
# Page 6: Political & Climate Risk
# ======================================================================


def build_political_climate_page(parent: QWidget) -> QWidget:
    """Political risk scoring, sanction impact, climate risk and
    Hotelling resource economics."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Political & climate risk",
        "Political & Climate",
        "ICRG political risk scoring, sanction GDP impact modelling, Climate VaR, Hotelling resource extraction and Bass innovation diffusion.",
    ))

    # ---- Panel 1: ICRG Political Risk ----
    icrg_panel, icrg_lay = frame("ICRG Political Risk Score", "Composite political risk assessment (0-100) based on economic, political and financial sub-indices.")
    icrg_table = make_table(
        ["Component", "Score", "Weight", "Contribution"],
        [["Computing…", "", "", ""]],
    )
    icrg_lay.addWidget(icrg_table)
    icrg_rating = QLabel("—")
    icrg_rating.setObjectName("metricValue")
    icrg_rating.setStyleSheet(f"color: {ACCENT};")
    icrg_lay.addWidget(icrg_rating)
    icrg_lay.addStretch()
    root.addWidget(icrg_panel)

    try:
        scorer = PoliticalRiskScore()
        icrg_res = scorer.compute(
            economic_indicators={"gdp_growth": 2.5, "inflation": 3.0, "budget_balance": -2.5, "current_account": 1.0},
            political_indicators={"stability": 7, "corruption": 5, "law_order": 6, "bureaucracy": 4},
            financial_indicators={"foreign_debt": 35, "exchange_rate_stability": 6, "credit_rating": 5},
        )
        comp_rows = []
        sub_scores = icrg_res.get("sub_scores", {})
        for name, score_val in sub_scores.items():
            w = 1.0 / max(len(sub_scores), 1)
            comp_rows.append([name.title(), f"{score_val:.1f}", f"{w:.1%}", f"{score_val * w:.2f}"])
        new_table = make_table(["Component", "Score", "Weight", "Contribution"], comp_rows)
        parent_layout = icrg_table.parentWidget().layout()
        parent_layout.replaceWidget(icrg_table, new_table)
        icrg_table.hide()
        icrg_table.setParent(None)
        icrg_table.deleteLater()
        icrg_rating.setText(f"Composite Risk Score: {icrg_res['composite_score']:.1f}/100 — {icrg_res.get('risk_rating', 'N/A')}")
    except Exception as exc:
        icrg_rating.setText(f"ICRG Error: {exc}")

    # ---- Panel 2: Sanction Impact ----
    sanc_panel, sanc_lay = frame("Sanction GDP Impact Model", "Estimate cumulative GDP loss from sanctions with exponential adaptation.")
    sanc_plot = _styled_plot(260)
    sanc_lay.addWidget(sanc_plot, 1)
    sanc_info = QLabel("Computing…")
    sanc_info.setObjectName("panelSubtitle")
    sanc_info.setWordWrap(True)
    sanc_lay.addWidget(sanc_info)
    sanc_lay.addStretch()
    root.addWidget(sanc_panel)

    try:
        sanc_model = SanctionImpactModel()
        sanc_res = sanc_model.estimate_gdp_impact(
            trade_dependency=0.25, sanction_severity=0.7, duration=10, adaptation_rate=0.1,
        )
        years = np.arange(len(sanc_res["gdp_loss_path"]))
        sanc_plot.clear()
        sanc_plot.plot(years, np.array(sanc_res["gdp_loss_path"]) * 100, pen=pg.mkPen(DANGER, width=2), name="GDP loss (%)")
        sanc_plot.addLine(y=0, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        sanc_plot.setLabel("left", "%")
        sanc_plot.setLabel("bottom", "Year")
        sanc_plot.setTitle("Sanction GDP Impact Path", color=TEXT, size="12pt")
        sanc_info.setText(
            f"Total GDP loss: {sanc_res['total_loss']:.2%}  ·  Annual avg: {np.mean(sanc_res['gdp_loss_path']):.2%}"
        )
    except Exception as exc:
        sanc_plot.setTitle(f"Sanction error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 3: Climate VaR ----
    climate_panel, climate_lay = frame("Climate Value-at-Risk", "Physical climate risk VaR under temperature scenarios.")
    climate_plot = _styled_plot(260)
    climate_lay.addWidget(climate_plot, 1)
    climate_info = QLabel("Computing…")
    climate_info.setObjectName("panelSubtitle")
    climate_info.setWordWrap(True)
    climate_lay.addWidget(climate_info)
    climate_lay.addStretch()
    root.addWidget(climate_panel)

    try:
        cv = ClimateVaR()
        np.random.seed(7)
        asset_vals = np.array([500.0, 300.0, 200.0, 400.0, 350.0])
        temp_scenarios = {"+1.5C": 1.5, "+2.0C": 2.0, "+3.0C": 3.0}
        scenario_colors = {"+1.5C": ACCENT, "+2.0C": AMBER, "+3.0C": DANGER}
        heights = []
        for name, temp in temp_scenarios.items():
            res_cl = cv.physical_risk(asset_vals, np.array([temp]), damage_function="nordhaus")
            heights.append(res_cl["var_95"])
        climate_plot.clear()
        x_bars = np.arange(len(temp_scenarios))
        bg_cl = pg.BarGraphItem(x=x_bars, height=heights, width=0.5,
                                brushes=[pg.mkBrush(QColor(scenario_colors[n]).darker(200)) for n in temp_scenarios])
        climate_plot.addItem(bg_cl)
        axis_cl = climate_plot.getAxis("bottom")
        axis_cl.setTicks([[(i, list(temp_scenarios.keys())[i]) for i in range(len(temp_scenarios))]])
        climate_plot.setLabel("left", "VaR (95%)")
        climate_plot.setTitle("Climate VaR by Temperature Scenario", color=TEXT, size="12pt")
        climate_info.setText("  ".join([f"{n}: VaR(95%)={h:.1f}" for n, h in zip(temp_scenarios, heights)]))
    except Exception as exc:
        climate_plot.setTitle(f"Climate VaR error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 4: Hotelling Rule ----
    hotelling_panel, hot_lay = frame("Hotelling Rule — Optimal Resource Extraction", "Hotelling (1931) optimal extraction pricing: net price rises at the rate of interest.")
    hot_plot = _styled_plot(260)
    hot_lay.addWidget(hot_plot, 1)
    hot_lay.addStretch()
    root.addWidget(hotelling_panel)

    try:
        hr = HotellingRule()
        hr_res = hr.optimal_price_path(initial_price=100, extraction_cost=30, discount_rate=0.05, reserves=1000, periods=50)
        x_hr = np.arange(50)
        hot_plot.clear()
        hot_plot.plot(x_hr, hr_res["prices"], pen=pg.mkPen(ACCENT, width=2), name="Price P_t")
        hot_plot.plot(x_hr, hr_res["net_prices"], pen=pg.mkPen(AMBER, width=2), name="Net price (P-c)")
        hot_plot.addLine(y=30, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine), label="Extraction cost")
        hot_plot.setLabel("left", "Price")
        hot_plot.setLabel("bottom", "Period")
        hot_plot.setTitle("Hotelling Optimal Extraction Path", color=TEXT, size="12pt")
    except Exception as exc:
        hot_plot.setTitle(f"Hotelling error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 5: Innovation S-Curve ----
    bass_panel, bass_lay = frame("Bass Innovation Diffusion S-Curve", "Bass (1969) diffusion model: new adopters = (p + q*F(t))(1 - F(t)).")
    bass_plot = _styled_plot(260)
    bass_lay.addWidget(bass_plot, 1)
    bass_info = QLabel("")
    bass_info.setObjectName("panelSubtitle")
    bass_info.setWordWrap(True)
    bass_lay.addWidget(bass_info)
    bass_lay.addStretch()
    root.addWidget(bass_panel)

    try:
        isc = InnovationSCurve()
        bass_res = isc.adoption_curve(market_size=1000, innovation_coefficient=0.03, imitation_coefficient=0.38, periods=50)
        x_bass = np.arange(50)
        bass_plot.clear()
        bass_plot.plot(x_bass, bass_res["cumulative_adopters"], pen=pg.mkPen(ACCENT, width=2), name="Cumulative adopters")
        bass_plot.plot(x_bass, np.array(bass_res["new_adopters"]) * 10, pen=pg.mkPen(AMBER, width=2), name="New adopters (x10)")
        bass_plot.setLabel("left", "Count")
        bass_plot.setLabel("bottom", "Period")
        bass_plot.setTitle("Bass Diffusion S-Curve", color=TEXT, size="12pt")
        bass_info.setText(f"Peak adoption at period {bass_res['peak_period']}  ·  p=0.03  q=0.38")
    except Exception as exc:
        bass_plot.setTitle(f"Bass error: {exc}", color=DANGER, size="12pt")

    root.addStretch()
    return scroll


# ======================================================================
# Page 7: Markets & Pricing
# ======================================================================


def build_markets_pricing_page(parent: QWidget) -> QWidget:
    """Option pricing, interest rate models, market microstructure and
    capital structure."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Markets & pricing models",
        "Markets & Pricing",
        "Black-Scholes option pricing with Greeks, Vasicek/CIR yield curves, Avellaneda-Stoikov market making, Akerlof lemons and Modigliani-Miller capital structure.",
    ))

    # ---- Panel 1: Black-Scholes Greeks ----
    bs_panel, bs_lay = frame("Black-Scholes Option Pricing & Greeks", "European call/put pricing with full Greeks sensitivity. Interactive strike and maturity sliders.")
    s_strike, _ = _slider_row("Strike K", 50, 200, 100, bs_lay)
    s_maturity, _ = _slider_row("Maturity T (years, x10)", 1, 100, 10, bs_lay, divisor=10)
    s_vol, _ = _slider_row("Volatility sigma (x10)", 5, 80, 20, bs_lay, divisor=10)
    bs_table = make_table(
        ["Metric", "Value"],
        [["Computing…", ""]],
    )
    bs_lay.addWidget(bs_table)
    bs_lay.addStretch()
    root.addWidget(bs_panel)

    def _update_bs() -> None:
        try:
            K = s_strike.value()
            T = s_maturity.value() / 10
            sigma = s_vol.value() / 10
            bs = BlackScholesModel(S0=100, r=0.05, sigma=sigma)
            call = bs.call_price(K, T)
            put = bs.put_price(K, T)
            gr = bs.greeks(K, T)
            rows_bs = [
                ["Call Price", f"{call:.4f}"],
                ["Put Price", f"{put:.4f}"],
                ["Delta (call)", f"{gr['delta']:.4f}"],
                ["Gamma", f"{gr['gamma']:.6f}"],
                ["Vega", f"{gr['vega']:.4f}"],
                ["Theta (call)", f"{gr['theta']:.4f}"],
                ["Rho (call)", f"{gr['rho']:.4f}"],
                ["Put-Call Parity", f"{call - put - 100 + K * np.exp(-0.05 * T):.6f}"],
            ]
            new_t = make_table(["Metric", "Value"], rows_bs)
            for i in range(bs_lay.count()):
                w = bs_lay.itemAt(i).widget()
                if isinstance(w, QTableWidget):
                    old_table = w
                    break
            else:
                return
            bs_lay.replaceWidget(old_table, new_t)
            old_table.hide()
            old_table.setParent(None)
            old_table.deleteLater()
        except Exception:
            pass

    for s in (s_strike, s_maturity, s_vol):
        s.valueChanged.connect(_update_bs)
    _update_bs()

    # ---- Panel 2: Volatility Smile ----
    smile_panel, smile_lay = frame("Volatility Smile", "Implied volatility surface across strikes.")
    smile_plot = _styled_plot(260)
    smile_lay.addWidget(smile_plot, 1)
    smile_lay.addStretch()
    root.addWidget(smile_panel)

    try:
        bs2 = BlackScholesModel(S0=100, r=0.05, sigma=0.20)
        smile_res = bs2.volatility_smile(T=1.0, strikes=np.arange(70, 131, 5))
        smile_plot.clear()
        smile_plot.plot(smile_res["strikes"], smile_res["implied_vols"], pen=pg.mkPen(ACCENT, width=2), name="IV")
        smile_plot.addLine(y=0.20, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine), label="ATM vol=20%")
        smile_plot.setLabel("left", "Implied Vol")
        smile_plot.setLabel("bottom", "Strike")
        smile_plot.setTitle("Volatility Smile / Skew", color=TEXT, size="12pt")
    except Exception as exc:
        smile_plot.setTitle(f"Smile error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 3: Vasicek & CIR Yield Curves ----
    yc_panel, yc_lay = frame("Vasicek & CIR Yield Curves", "Mean-reverting short-rate models with analytical zero-coupon yield curves.")
    yc_plot = _styled_plot(280)
    yc_lay.addWidget(yc_plot, 1)
    yc_lay.addStretch()
    root.addWidget(yc_panel)

    try:
        vas = VasicekModel(kappa=0.5, theta=0.05, sigma=0.01, r0=0.03)
        cir = CIRModel(kappa=0.5, theta=0.05, sigma=0.10, r0=0.03)
        vas_res = vas.yield_curve(maturities=np.linspace(0.1, 30, 100))
        cir_res = cir.yield_curve(maturities=np.linspace(0.1, 30, 100))
        yc_plot.clear()
        yc_plot.plot(vas_res["maturities"], np.array(vas_res["yields"]) * 100, pen=pg.mkPen(ACCENT, width=2), name="Vasicek")
        yc_plot.plot(cir_res["maturities"], np.array(cir_res["yields"]) * 100, pen=pg.mkPen(AMBER, width=2), name="CIR")
        yc_plot.setLabel("left", "Yield (%)")
        yc_plot.setLabel("bottom", "Maturity (years)")
        yc_plot.setTitle("Zero-Coupon Yield Curves", color=TEXT, size="12pt")
    except Exception as exc:
        yc_plot.setTitle(f"Yield curve error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 4: Market Maker Simulation ----
    mm_panel, mm_lay = frame("Avellaneda-Stoikov Market Maker", "Inventory-based market making: reservation price adjusts with inventory risk.")
    mm_plot = _styled_plot(280)
    mm_lay.addWidget(mm_plot, 1)
    mm_info = QLabel("")
    mm_info.setObjectName("panelSubtitle")
    mm_info.setWordWrap(True)
    mm_lay.addWidget(mm_info)
    mm_lay.addStretch()
    root.addWidget(mm_panel)

    try:
        mm = MarketMakerModel(sigma=0.2, gamma=0.1, T=1/252, kappa=1.0, A=0.5)
        mm_res = mm.inventory_trajectory(S0=100, q0=0, n_steps=100, seed=42)
        t_mm = mm_res["time"]
        mm_plot.clear()
        mm_plot.plot(t_mm, mm_res["mid_price"], pen=pg.mkPen(BLUE, width=1.5), name="Mid")
        mm_plot.plot(t_mm, mm_res["bid"], pen=pg.mkPen(ACCENT, width=1), name="Bid")
        mm_plot.plot(t_mm, mm_res["ask"], pen=pg.mkPen(DANGER, width=1), name="Ask")
        mm_plot.setLabel("left", "Price")
        mm_plot.setLabel("bottom", "Time")
        mm_plot.setTitle("Market Maker Quotes & Inventory", color=TEXT, size="12pt")
        final_pnl = mm_res["pnl"][-1] if mm_res["pnl"] else 0
        mm_info.setText(f"Final inventory: {mm_res['inventory'][-1]:.0f}  ·  Final PnL: {final_pnl:.2f}")
    except Exception as exc:
        mm_plot.setTitle(f"MM error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 5: Akerlof Lemons Model ----
    akerlof_panel, akerlof_lay = frame("Akerlof Lemons Market", "Adverse selection in asymmetric information markets.")
    akerlof_plot = _styled_plot(260)
    akerlof_lay.addWidget(akerlof_plot, 1)
    akerlof_info = QLabel("")
    akerlof_info.setObjectName("panelSubtitle")
    akerlof_info.setWordWrap(True)
    akerlof_lay.addWidget(akerlof_info)
    akerlof_lay.addStretch()
    root.addWidget(akerlof_panel)

    try:
        ak = AkerlofLemonsModel(q_min=0, q_max=100, buyer_premium=1.5, n_price_points=200)
        ak_res = ak.quality_vs_price_curve()
        akerlof_plot.clear()
        akerlof_plot.plot(ak_res["price"], ak_res["average_quality"], pen=pg.mkPen(ACCENT, width=2), name="Avg quality")
        akerlof_plot.plot(ak_res["price"], ak_res["buyer_willingness"], pen=pg.mkPen(AMBER, width=2), name="Buyer WTP")
        akerlof_plot.plot(ak_res["price"], ak_res["price"], pen=pg.mkPen("#555555", width=1, style=Qt.PenStyle.DotLine), name="P=Q ref")
        akerlof_plot.setLabel("left", "Value")
        akerlof_plot.setLabel("bottom", "Price")
        eq = ak.find_equilibrium()
        status = "COLLAPSED" if eq["market_collapsed"] else f"P* = {eq['equilibrium_price']:.1f}"
        akerlof_plot.setTitle(f"Akerlof Lemons — Market: {status}", color=TEXT, size="12pt")
        akerlof_info.setText(f"Equilibrium price: {eq['equilibrium_price']:.1f}  ·  Trades: {eq['trades']:.1f}")
    except Exception as exc:
        akerlof_plot.setTitle(f"Akerlof error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 6: Modigliani-Miller ----
    mm2_panel, mm2_lay = frame("Modigliani-Miller Capital Structure", "MM Proposition I with taxes: V_L = V_U + T_c * D.")
    mm2_plot = _styled_plot(260)
    mm2_lay.addWidget(mm2_plot, 1)
    mm2_lay.addStretch()
    root.addWidget(mm2_panel)

    try:
        mm2 = ModiglianiMiller(EBIT=100, r_a=0.10, r_d=0.06, T_c=0.25)
        sweep = mm2.leverage_sweep(n_points=100)
        mm2_plot.clear()
        mm2_plot.plot(sweep["debt"], sweep["V_levered"], pen=pg.mkPen(ACCENT, width=2), name="V_L (with tax)")
        mm2_plot.plot(sweep["debt"], sweep["tax_shield"], pen=pg.mkPen(AMBER, width=1.5), name="Tax shield")
        vu = mm2.prop1_no_tax(0)["V_unlevered"]
        mm2_plot.addLine(y=vu, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine), label="V_U")
        mm2_plot.setLabel("left", "Value")
        mm2_plot.setLabel("bottom", "Debt D")
        mm2_plot.setTitle("Modigliani-Miller with Corporate Tax", color=TEXT, size="12pt")
    except Exception as exc:
        mm2_plot.setTitle(f"MM error: {exc}", color=DANGER, size="12pt")

    root.addStretch()
    return scroll


# ======================================================================
# Page 8: Regulatory & EMH
# ======================================================================


def build_regulatory_emh_page(parent: QWidget) -> QWidget:
    """Basel III compliance, EMH efficiency tests and fuzzy credit scoring."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Regulatory compliance & market efficiency",
        "Regulatory & EMH",
        "Basel III capital adequacy with stress testing, weak-form EMH tests and Mamdani fuzzy credit scoring.",
    ))

    # ---- Panel 1: Basel III Compliance ----
    basel_panel, basel_lay = frame("Basel III Capital Adequacy", "CET1, Tier 1, Total Capital, Leverage, LCR and NSFR ratios with compliance assessment and stress testing.")
    basel_table = make_table(
        ["Ratio", "Value", "Requirement", "Status"],
        [["Computing…", "", "", ""]],
    )
    basel_lay.addWidget(basel_table)
    basel_info = QLabel("")
    basel_info.setObjectName("metricValue")
    basel_info.setStyleSheet(f"color: {ACCENT};")
    basel_info.setWordWrap(True)
    basel_lay.addWidget(basel_info)

    btn_stress = QPushButton("Run Stress Test (-15% RWA, -20% HQLA, -30% outflows)")
    btn_stress.setObjectName("secondaryButton")
    basel_lay.addWidget(btn_stress)
    basel_lay.addStretch()
    root.addWidget(basel_panel)

    def _render_basel(stressed: bool = False) -> None:
        try:
            cap = BaselIIICapital(
                common_equity_tier1=120, additional_tier1=30, tier2=50,
                total_assets=5000, risk_weighted_assets=2500,
                total_exposure=3000, hqla=600,
                net_cash_outflows_30d=400,
                available_stable_funding=2200, required_stable_funding=2000,
            )
            if stressed:
                import dataclasses
                fields = {f.name: getattr(cap, f.name) for f in dataclasses.fields(cap)}
                fields["risk_weighted_assets"] *= 1.15
                fields["hqla"] *= 0.80
                fields["net_cash_outflows_30d"] *= 1.30
                cap = BaselIIICapital(**fields)
            compliance = BaselIIICompliance()
            result = compliance.compliance_check(cap)
            rows_b = []
            for key in ["cet1_ratio", "tier1_ratio", "total_ratio", "leverage_ratio", "lcr", "nsfr"]:
                val = result["ratios"].get(key, 0)
                req = result["requirements"].get(key, 0)
                status = "PASS" if result["compliant"] and val >= req else "FAIL"
                rows_b.append([key.replace("_", " ").title(), f"{val:.2%}", f"{req:.2%}", status])
            new_bt = make_table(["Ratio", "Value", "Requirement", "Status"], rows_b)
            for i in range(basel_lay.count()):
                w = basel_lay.itemAt(i).widget()
                if isinstance(w, QTableWidget):
                    old_bt = w
                    break
            else:
                return
            basel_lay.replaceWidget(old_bt, new_bt)
            old_bt.hide()
            old_bt.setParent(None)
            old_bt.deleteLater()
            label = "STRESSED" if stressed else "BASELINE"
            basel_info.setText(f"{label}: {'COMPLIANT' if result['compliant'] else 'NON-COMPLIANT'}  ·  Max payout: {result.get('max_payout_ratio', 0):.1%}")
        except Exception as exc:
            basel_info.setText(f"Error: {exc}")

    _render_basel()
    btn_stress.clicked.connect(lambda: _render_basel(stressed=True))

    # ---- Panel 2: EMH Tests ----
    emh_panel, emh_lay = frame("Weak-Form EMH Tests", "Runs test, Variance Ratio test and Ljung-Box autocorrelation test on GDP returns.")
    emh_table = make_table(
        ["Test", "Statistic", "P-value", "Reject H0", "Conclusion"],
        [["Computing…", "", "", "", ""]],
    )
    emh_lay.addWidget(emh_table)
    emh_summary = QLabel("")
    emh_summary.setObjectName("metricValue")
    emh_summary.setWordWrap(True)
    emh_lay.addWidget(emh_summary)
    emh_lay.addStretch()
    root.addWidget(emh_panel)

    data = parent.current_data if parent.current_data else {}
    gdp_v = _extract_values(data, "gdp")
    if len(gdp_v) >= 20:
        try:
            returns_emh = np.diff(gdp_v) / (np.abs(gdp_v[:-1]) + 1e-8)
            emh = WeakFormEMHTests(returns_emh)
            report = emh.full_report()
            rows_emh = []
            rt = report["runs_test"]
            rows_emh.append(["Runs", f"z={rt['z_statistic']:.3f}", f"{rt['p_value']:.4f}",
                              "Yes" if rt["reject_h0"] else "No", "Not random" if rt["reject_h0"] else "Random"])
            for q_val, vr_res in report.get("variance_ratio_tests", {}).items():
                rows_emh.append([f"VR(q={q_val})", f"VR={vr_res['vr']:.3f}", f"{vr_res['p_value']:.4f}",
                                  "Yes" if vr_res["reject_h0"] else "No", vr_res.get("evidence_of", "")])
            ac = report["autocorrelation_test"]
            rows_emh.append(["Ljung-Box", f"Q={ac['q_statistic']:.3f}", f"{ac['p_value']:.4f}",
                              "Yes" if ac["reject_h0"] else "No",
                              f"Sig. lags: {ac.get('significant_lags_95', [])}"])
            new_emh_t = make_table(["Test", "Statistic", "P-value", "Reject H0", "Conclusion"], rows_emh)
            for i in range(emh_lay.count()):
                w = emh_lay.itemAt(i).widget()
                if isinstance(w, QTableWidget):
                    old_emh = w
                    break
            else:
                return
            emh_lay.replaceWidget(old_emh, new_emh_t)
            old_emh.hide()
            old_emh.setParent(None)
            old_emh.deleteLater()
            summary = report.get("summary", {})
            emh_summary.setText(
                f"Tests rejecting efficiency: {summary.get('tests_rejecting_efficiency', 0)}  ·  "
                f"Market appears efficient: {summary.get('market_appears_efficient', 'N/A')}  ·  {summary.get('conclusion', '')}"
            )
            emh_summary.setStyleSheet(f"color: {ACCENT if summary.get('market_appears_efficient') else DANGER};")
        except Exception as exc:
            emh_summary.setText(f"EMH error: {exc}")
            emh_summary.setStyleSheet(f"color: {DANGER};")
    else:
        emh_summary.setText("Need >= 20 GDP observations. Load data from top bar.")

    # ---- Panel 3: Fuzzy Credit Scoring ----
    fuzzy_panel, fuzzy_lay = frame("Fuzzy Credit Scoring (Mamdani FIS)", "24-rule Mamdani fuzzy inference system with 4 inputs: income, debt ratio, payment history, employment years.")
    s_income, _ = _slider_row("Income ($K)", 20, 200, 60, fuzzy_lay)
    s_debt, _ = _slider_row("Debt ratio (% x10)", 0, 80, 30, fuzzy_lay, divisor=10)
    s_payment, _ = _slider_row("Payment history (0-100)", 0, 100, 70, fuzzy_lay)
    s_employ, _ = _slider_row("Employment years", 0, 40, 10, fuzzy_lay)
    fuzzy_result = QLabel("—")
    fuzzy_result.setObjectName("metricValue")
    fuzzy_result.setStyleSheet(f"color: {ACCENT}; font-size: 16pt;")
    fuzzy_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
    fuzzy_lay.addWidget(fuzzy_result)
    fuzzy_lay.addStretch()
    root.addWidget(fuzzy_panel)

    def _update_fuzzy() -> None:
        try:
            scorer = FuzzyCreditScorer()
            res_f = scorer.evaluate(
                income=s_income.value() / 1000.0,
                debt_ratio=s_debt.value() / 10,
                payment_history=s_payment.value(),
                employment_years=s_employ.value(),
            )
            score = res_f["credit_score"]
            color = ACCENT if score >= 70 else (AMBER if score >= 40 else DANGER)
            fuzzy_result.setText(f"Credit Score: {score:.1f}/100")
            fuzzy_result.setStyleSheet(f"color: {color}; font-size: 16pt;")
        except Exception:
            fuzzy_result.setText("Error computing score")

    for s in (s_income, s_debt, s_payment, s_employ):
        s.valueChanged.connect(_update_fuzzy)
    _update_fuzzy()

    root.addStretch()
    return scroll


# ======================================================================
# Page 9: Causal & Epidemiological
# ======================================================================


def build_causal_epidemiological_page(parent: QWidget) -> QWidget:
    """Causal inference (DAG, DID, PSM) and SIR epidemiological economic
    impact modelling."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Causal inference & epidemic economics",
        "Causal & Epidemic",
        "Causal DAG with backdoor adjustment, Difference-in-Differences, Propensity Score Matching and SIR epidemic-economic impact modelling.",
    ))

    # ---- Panel 1: Causal DAG ----
    dag_panel, dag_lay = frame("Causal DAG — Macro Policy", "Build a causal graph and find valid backdoor adjustment sets. Example: does monetary policy Granger-cause GDP?" )
    dag_info = QLabel("Building DAG…")
    dag_info.setObjectName("panelSubtitle")
    dag_info.setWordWrap(True)
    dag_lay.addWidget(dag_info)
    dag_table = make_table(
        ["Variable", "Role"],
        [["—", "—"]],
    )
    dag_lay.addWidget(dag_table)
    dag_lay.addStretch()
    root.addWidget(dag_panel)

    try:
        dag = CausalDAG()
        for v in ["InterestRate", "Inflation", "GDP", "Unemployment", "Investment"]:
            dag.add_node(v)
        dag.add_edges([
            ("InterestRate", "Inflation"),
            ("Inflation", "GDP"),
            ("GDP", "Unemployment"),
            ("Unemployment", "InterestRate"),
            ("Investment", "GDP"),
            ("InterestRate", "Investment"),
        ])
        adj = dag.find_adjustment_set("InterestRate", "GDP")
        dag_info.setText(
            f"Treatment: InterestRate → Outcome: GDP  |  "
            f"Adjustment set: {adj['adjustment_set']}  |  "
            f"Valid: {adj['is_valid']}  |  Backdoor paths: {len(adj.get('backdoor_paths', []))}"
        )
        rows_dag = []
        roles = {"InterestRate": "Treatment", "GDP": "Outcome",
                 "Inflation": "Mediator", "Unemployment": "Confounder", "Investment": "Confounder"}
        for v in ["InterestRate", "Inflation", "GDP", "Unemployment", "Investment"]:
            rows_dag.append([v, roles.get(v, "—")])
        new_dt = make_table(["Variable", "Role"], rows_dag)
        for i in range(dag_lay.count()):
            w = dag_lay.itemAt(i).widget()
            if isinstance(w, QTableWidget):
                old_dt = w
                break
        else:
            return scroll
        dag_lay.replaceWidget(old_dt, new_dt)
        old_dt.hide()
        old_dt.setParent(None)
        old_dt.deleteLater()
    except Exception as exc:
        dag_info.setText(f"DAG Error: {exc}")

    # ---- Panel 2: Difference-in-Differences ----
    did_panel, did_lay = frame("Difference-in-Differences Estimator", "Synthetic DID example: policy treatment effect estimation with parallel trends test.")
    did_info = QLabel("Computing…")
    did_info.setObjectName("panelSubtitle")
    did_info.setWordWrap(True)
    did_lay.addWidget(did_info)
    did_plot = _styled_plot(250)
    did_lay.addWidget(did_plot, 1)
    did_lay.addStretch()
    root.addWidget(did_panel)

    try:
        np.random.seed(42)
        n = 50
        Y_pre_t = np.random.normal(10, 2, n)
        Y_post_t = Y_pre_t + np.random.normal(3, 1, n)  # +3 treatment effect
        Y_pre_c = np.random.normal(10, 2, n)
        Y_post_c = Y_pre_c + np.random.normal(0.2, 1, n)  # +0.2 control trend
        did = DifferenceInDifferences()
        res_did = did.estimate(Y_pre_t, Y_post_t, Y_pre_c, Y_post_c)
        pt_res = did.parallel_trends_test(Y_pre_t, Y_pre_c)
        did_plot.clear()
        x_did = np.arange(2)
        groups = ["Treatment", "Control"]
        means_pre = [np.mean(Y_pre_t), np.mean(Y_pre_c)]
        means_post = [np.mean(Y_post_t), np.mean(Y_post_c)]
        for gi, (g, mp, mo) in enumerate(zip(groups, means_pre, means_post)):
            did_plot.plot([gi, gi + 0.3], [mp, mo], pen=pg.mkPen(ACCENT if gi == 0 else BLUE, width=2), name=g)
        did_plot.addLine(y=0, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        did_plot.setLabel("bottom", "")
        did_plot.setTitle(f"DID: ATT = {res_did['att']:.3f} (t={res_did['t_statistic']:.2f}, p={res_did['p_value']:.4f})", color=TEXT, size="12pt")
        did_info.setText(
            f"ATT = {res_did['att']:.3f}  |  SE = {res_did['standard_error']:.3f}  |  "
            f"Parallel trends p = {pt_res['p_value']:.4f} ({'plausible' if pt_res['parallel_trends_plausible'] else 'violated'})"
        )
    except Exception as exc:
        did_plot.setTitle(f"DID Error: {exc}", color=DANGER, size="12pt")
        did_info.setText(str(exc))

    # ---- Panel 3: SIR Epidemic + Economic Impact ----
    sir_panel, sir_lay = frame("SIR Epidemic Model & GDP Impact", "Kermack-McKendrick SIR model with economic impact assessment across labour, consumption and supply-chain channels.")
    btn_row_sir = QHBoxLayout()
    btn_mild = QPushButton("Mild (R0=1.5)")
    btn_mild.setObjectName("secondaryButton")
    btn_moderate = QPushButton("Moderate (R0=2.5)")
    btn_moderate.setObjectName("secondaryButton")
    btn_severe = QPushButton("Severe (R0=4.0)")
    btn_severe.setObjectName("secondaryButton")
    btn_row_sir.addWidget(btn_mild)
    btn_row_sir.addWidget(btn_moderate)
    btn_row_sir.addWidget(btn_severe)
    sir_lay.addLayout(btn_row_sir)
    sir_plot = _styled_plot(300)
    sir_lay.addWidget(sir_plot, 1)
    sir_info = QLabel("")
    sir_info.setObjectName("panelSubtitle")
    sir_info.setWordWrap(True)
    sir_lay.addWidget(sir_info)
    sir_lay.addStretch()
    root.addWidget(sir_panel)

    def _run_sir(r0: float) -> None:
        try:
            sir = SIRModel(N=10_000_000, I0=100, R0=r0, gamma=1/14)
            res = sir.simulate(T=365, n_steps=500)
            sir_plot.clear()
            t = res["time"]
            sir_plot.plot(t, res["S"] / 1e7, pen=pg.mkPen(BLUE, width=2), name="S")
            sir_plot.plot(t, res["I"] / 1e7, pen=pg.mkPen(DANGER, width=2), name="I")
            sir_plot.plot(t, res["R"] / 1e7, pen=pg.mkPen(ACCENT, width=2), name="R")
            sir_plot.setLabel("left", "Population (millions)")
            sir_plot.setLabel("bottom", "Days")
            sir_plot.setTitle(f"SIR Model (R0={r0})", color=TEXT, size="12pt")
            # Economic impact
            econ = EconomicImpactSIR()
            impact = econ.assess(res, annual_gdp=1e12, baseline_growth=0.03)
            sir_info.setText(
                f"Peak infected: {res['peak_infected']/1e6:.1f}M (day {res['peak_day']})  |  "
                f"Attack rate: {res['attack_rate']:.1%}  |  "
                f"GDP loss: {impact['total_loss_pct_gdp']:.2%}  |  "
                f"Recovery: {impact['recovery_days']} days"
            )
        except Exception as exc:
            sir_plot.setTitle(f"SIR Error: {exc}", color=DANGER, size="12pt")

    btn_mild.clicked.connect(lambda: _run_sir(1.5))
    btn_moderate.clicked.connect(lambda: _run_sir(2.5))
    btn_severe.clicked.connect(lambda: _run_sir(4.0))
    _run_sir(2.5)

    # ---- Panel 4: Instrumental Variables (2SLS) ----
    iv_panel, iv_lay = frame("Instrumental Variables (2SLS)", "Two-Stage Least Squares with weak-instrument diagnostic. Z instruments correct for endogenous treatment X.")
    iv_info = QLabel("Computing…")
    iv_info.setObjectName("panelSubtitle")
    iv_info.setWordWrap(True)
    iv_lay.addWidget(iv_info)
    iv_lay.addStretch()
    root.addWidget(iv_panel)

    try:
        np.random.seed(99)
        n_iv = 200
        Z_instr = np.random.normal(0, 1, (n_iv, 2))
        U_conf = np.random.normal(0, 0.5, n_iv)
        X_endo = 0.6 * Z_instr[:, 0] + 0.4 * Z_instr[:, 1] + U_conf + np.random.normal(0, 0.3, n_iv)
        Y_out = 2.5 * X_endo + 0.8 * Z_instr[:, 0] + np.random.normal(0, 0.5, n_iv)
        iv_est = InstrumentalVariables()
        iv_res = iv_est.estimate(Y_out, X_endo, Z_instr)
        iv_info.setText(
            f"IV estimate (beta): {iv_res['iv_estimate']:.4f}  |  SE: {iv_res['standard_error']:.4f}  |  t: {iv_res['t_statistic']:.2f}  |  "
            f"First-stage F: {iv_res['first_stage_f_stat']:.1f}  |  R2: {iv_res['first_stage_r2']:.3f}  |  "
            f"Weak instrument: {'YES' if iv_res['weak_instrument_warning'] else 'No'}"
        )
        iv_info.setStyleSheet(f"color: {ACCENT if not iv_res['weak_instrument_warning'] else DANGER};")
    except Exception as exc:
        iv_info.setText(f"IV Error: {exc}")

    # ---- Panel 5: Double ML ----
    dml_panel, dml_lay = frame("Double/Debiased ML", "Cross-fitted orthogonal moment estimation of Average Treatment Effect using ridge regression as base learner.")
    dml_info = QLabel("Computing…")
    dml_info.setObjectName("panelSubtitle")
    dml_info.setWordWrap(True)
    dml_lay.addWidget(dml_info)
    dml_plot = _styled_plot(220)
    dml_lay.addWidget(dml_plot, 1)
    dml_lay.addStretch()
    root.addWidget(dml_panel)

    try:
        np.random.seed(77)
        n_dml = 300
        X_conf = np.random.normal(0, 1, (n_dml, 3))
        T_treat = 0.5 * X_conf[:, 0] + 0.3 * X_conf[:, 1] + np.random.normal(0, 0.4, n_dml)
        true_ate = 1.5
        Y_dml = true_ate * T_treat + 0.8 * X_conf[:, 0] - 0.5 * X_conf[:, 2] + np.random.normal(0, 0.5, n_dml)
        dml = DoubleML(n_folds=5, ridge_alpha=1.0)
        dml_res = dml.estimate(Y_dml, T_treat, X_conf)
        dml_plot.clear()
        dml_plot.plot(dml_res["y_residuals"], dml_res["t_residuals"], pen=None,
                      symbol='o', symbolBrush=pg.mkBrush(ACCENT), symbolSize=3, name="Residuals")
        dml_plot.addLine(pos=0, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        slope_line_x = np.linspace(dml_res["t_residuals"].min(), dml_res["t_residuals"].max(), 50)
        slope_line_y = dml_res["ate"] * slope_line_x
        dml_plot.plot(slope_line_x, slope_line_y, pen=pg.mkPen(AMBER, width=2), name=f"ATE={dml_res['ate']:.3f}")
        dml_plot.setLabel("left", "Y residual")
        dml_plot.setLabel("bottom", "T residual")
        dml_plot.setTitle(f"Double ML — ATE = {dml_res['ate']:.4f} (true = {true_ate:.1f})", color=TEXT, size="12pt")
        dml_info.setText(
            f"ATE = {dml_res['ate']:.4f}  |  SE = {dml_res['standard_error']:.4f}  |  t = {dml_res['t_statistic']:.2f}")
    except Exception as exc:
        dml_plot.setTitle(f"Double ML Error: {exc}", color=DANGER, size="12pt")
        dml_info.setText(str(exc))

    # ---- Panel 6: Propensity Score Matching ----
    psm_panel, psm_lay = frame("Propensity Score Matching", "Estimate ATT by matching treated and control units on estimated propensity scores with caliper constraint.")
    psm_info = QLabel("Computing…")
    psm_info.setObjectName("panelSubtitle")
    psm_info.setWordWrap(True)
    psm_lay.addWidget(psm_info)
    psm_plot = _styled_plot(220)
    psm_lay.addWidget(psm_plot, 1)
    psm_lay.addStretch()
    root.addWidget(psm_panel)

    try:
        np.random.seed(33)
        n_psm = 200
        X_cov = np.random.normal(0, 1, (n_psm, 2))
        T_psm = (0.4 * X_cov[:, 0] + 0.3 * X_cov[:, 1] + np.random.normal(0, 0.5, n_psm)) > 0.3
        T_psm = T_psm.astype(float)
        true_att = 2.0
        Y_psm = true_att * T_psm + 1.0 * X_cov[:, 0] - 0.5 * X_cov[:, 1] + np.random.normal(0, 0.8, n_psm)
        psm = PropensityScoreMatching(ridge_alpha=1.0, caliper=0.2)
        psm_res = psm.match_and_estimate(Y_psm, T_psm, X_cov)
        psm_plot.clear()
        scores = psm_res["propensity_scores"]
        treated_mask = T_psm == 1
        psm_plot.hist(scores[treated_mask], bins=20, fill=True, brush=pg.mkBrush(ACCENT, 80), pen=pg.mkPen(ACCENT), name="Treated")
        psm_plot.hist(scores[~treated_mask], bins=20, fill=True, brush=pg.mkBrush(BLUE, 80), pen=pg.mkPen(BLUE), name="Control")
        psm_plot.setLabel("left", "Count")
        psm_plot.setLabel("bottom", "Propensity score")
        psm_plot.setTitle(f"PSM — ATT = {psm_res['att']:.4f} (true = {true_att:.1f})", color=TEXT, size="12pt")
        psm_info.setText(
            f"ATT = {psm_res['att']:.4f}  |  SE = {psm_res['standard_error']:.4f}  |  Matched: {psm_res['n_matched']}/{psm_res['n_treated']}  |  "
            f"Mean propensity: treated={psm_res['mean_propensity_treated']:.3f}, control={psm_res['mean_propensity_control']:.3f}"
        )
    except Exception as exc:
        psm_plot.setTitle(f"PSM Error: {exc}", color=DANGER, size="12pt")
        psm_info.setText(str(exc))

    root.addStretch()
    return scroll


# ======================================================================
# Page 10: Fuzzy Decision Lab
# ======================================================================


def build_fuzzy_decision_page(parent: QWidget) -> QWidget:
    """Fuzzy multi-criteria decision making: AHP, TOPSIS, portfolio
    optimisation, ANFIS and fuzzy Black-Scholes."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Fuzzy decision systems",
        "Fuzzy Decision Lab",
        "Fuzzy AHP weighting, Fuzzy TOPSIS ranking, fuzzy portfolio optimisation, ANFIS neuro-fuzzy training and fuzzy volatility option pricing.",
    ))

    # ---- Panel 1: Fuzzy AHP ----
    ahp_panel, ahp_lay = frame("Fuzzy AHP — Multi-Criteria Weighting", "Fuzzy Analytic Hierarchy Process with triangular fuzzy pairwise comparisons. Consistency ratio validates judgment quality.")
    ahp_info = QLabel("Computing…")
    ahp_info.setObjectName("panelSubtitle")
    ahp_info.setWordWrap(True)
    ahp_lay.addWidget(ahp_info)
    ahp_table = make_table(["Criterion", "Weight"], [["…", "…"]])
    ahp_lay.addWidget(ahp_table)
    ahp_lay.addStretch()
    root.addWidget(ahp_panel)

    try:
        criteria = ["Growth", "Risk", "Liquidity", "ESG"]
        fahp = FuzzyAHP(criteria)
        # Set pairwise comparisons (crisp with auto-fuzziness)
        fahp.set_comparison_crisp("Growth", "Risk", 3)   # Growth moderately preferred
        fahp.set_comparison_crisp("Growth", "Liquidity", 5)
        fahp.set_comparison_crisp("Growth", "ESG", 2)
        fahp.set_comparison_crisp("Risk", "Liquidity", 1)
        fahp.set_comparison_crisp("Risk", "ESG", 4)
        fahp.set_comparison_crisp("Liquidity", "ESG", 3)
        res_ahp = fahp.compute_weights()
        rows_ahp = [[c, f"{w:.4f}"] for c, w in zip(criteria, res_ahp["weights"])]
        new_ahp_t = make_table(["Criterion", "Weight"], rows_ahp)
        for i in range(ahp_lay.count()):
            w = ahp_lay.itemAt(i).widget()
            if isinstance(w, QTableWidget):
                old_at = w
                break
        else:
            return scroll
        ahp_lay.replaceWidget(old_at, new_ahp_t)
        old_at.hide()
        old_at.setParent(None)
        old_at.deleteLater()
        ahp_info.setText(
            f"Consistency Ratio: {res_ahp['consistency_ratio']:.4f}  |  "
            f"{'Consistent' if res_ahp['consistent'] else 'Inconsistent — review judgments'}"
        )
    except Exception as exc:
        ahp_info.setText(f"AHP Error: {exc}")

    # ---- Panel 2: Fuzzy TOPSIS ----
    topsis_panel, topsis_lay = frame("Fuzzy TOPSIS — Alternative Ranking", "Fuzzy Technique for Order Preference by Similarity to Ideal Solution. Ranks investment alternatives under uncertainty.")
    topsis_info = QLabel("Computing…")
    topsis_info.setObjectName("panelSubtitle")
    topsis_info.setWordWrap(True)
    topsis_lay.addWidget(topsis_info)
    topsis_lay.addStretch()
    root.addWidget(topsis_panel)

    try:
        alts = ["Asset A", "Asset B", "Asset C", "Asset D"]
        crits = ["Return", "Risk", "Liquidity", "ESG Score"]
        ft = FuzzyTOPSIS(alts, crits, benefit_criteria=["Return", "Liquidity", "ESG Score"])
        # Set ratings (crisp with fuzziness)
        rating_data = {
            ("Asset A", "Return"): 12, ("Asset A", "Risk"): 8, ("Asset A", "Liquidity"): 9, ("Asset A", "ESG Score"): 7,
            ("Asset B", "Return"): 10, ("Asset B", "Risk"): 6, ("Asset B", "Liquidity"): 8, ("Asset B", "ESG Score"): 9,
            ("Asset C", "Return"): 14, ("Asset C", "Risk"): 10, ("Asset C", "Liquidity"): 5, ("Asset C", "ESG Score"): 6,
            ("Asset D", "Return"): 8, ("Asset D", "Risk"): 4, ("Asset D", "Liquidity"): 10, ("Asset D", "ESG Score"): 8,
        }
        for (a, c), v in rating_data.items():
            ft.set_rating_crisp(a, c, v, fuzziness=0.15)
        ft.set_weights({"Return": 0.35, "Risk": 0.25, "Liquidity": 0.20, "ESG Score": 0.20})
        res_ft = ft.rank()
        ranking_text = "  |  ".join([f"#{r[0]+1}: {r[1]} ({r[2]:.3f})" for r in zip(
            range(len(alts)), res_ft["rankings"], res_ft["closeness_scores"])])
        topsis_info.setText(f"Ranking: {ranking_text}")
    except Exception as exc:
        topsis_info.setText(f"TOPSIS Error: {exc}")

    # ---- Panel 3: Fuzzy Portfolio ----
    fp_panel, fp_lay = frame("Fuzzy Portfolio Optimisation", "Mean-variance optimisation with triangular fuzzy number expected returns. Sweep alpha-cuts to find weight ranges.")
    fp_plot = _styled_plot(260)
    fp_lay.addWidget(fp_plot, 1)
    fp_info = QLabel("")
    fp_info.setObjectName("panelSubtitle")
    fp_info.setWordWrap(True)
    fp_lay.addWidget(fp_info)
    fp_lay.addStretch()
    root.addWidget(fp_panel)

    try:
        fuzzy_rets = {
            "Equity": TFN(0.06, 0.10, 0.14),
            "Bonds": TFN(0.02, 0.04, 0.06),
            "Real Estate": TFN(0.04, 0.08, 0.12),
        }
        cov = np.array([[0.04, 0.002, 0.008],
                         [0.002, 0.01, 0.003],
                         [0.008, 0.003, 0.025]])
        fpo = FuzzyPortfolioOptimizer(fuzzy_rets, cov, risk_free=0.02)
        sweep = fpo.alpha_cut_sweep(n_cuts=6)
        fp_plot.clear()
        assets = list(fuzzy_rets.keys())
        colors_fp = [ACCENT, AMBER, BLUE]
        for ai, asset in enumerate(assets):
            ranges = sweep["weight_ranges"][asset]
            alphas = [p["alpha"] for p in sweep["alpha_portfolios"]]
            w_means = [p["weights"][ai] for p in sweep["alpha_portfolios"]]
            fp_plot.plot(alphas, w_means, pen=pg.mkPen(colors_fp[ai], width=2), name=asset)
        fp_plot.setLabel("left", "Weight")
        fp_plot.setLabel("bottom", "Alpha-cut")
        fp_plot.setTitle("Portfolio Weights vs Alpha-Cut", color=TEXT, size="12pt")
        mid = sweep["alpha_portfolios"][len(sweep["alpha_portfolios"])//2]
        fp_info.setText(
            f"At alpha=0.5: E[R]={mid['expected_return']:.4f}  |  "
            f"Vol={mid['volatility']:.4f}  |  Sharpe={mid['sharpe_ratio']:.3f}"
        )
    except Exception as exc:
        fp_plot.setTitle(f"Fuzzy Portfolio Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 4: ANFIS ----
    anfis_panel, anfis_lay = frame("Simplified ANFIS", "Adaptive Neuro-Fuzzy Inference System: trains fuzzy rules from data via least-squares consequent optimisation.")
    anfis_plot = _styled_plot(250)
    anfis_lay.addWidget(anfis_plot, 1)
    anfis_info = QLabel("")
    anfis_info.setObjectName("panelSubtitle")
    anfis_info.setWordWrap(True)
    anfis_lay.addWidget(anfis_info)
    anfis_lay.addStretch()
    root.addWidget(anfis_panel)

    try:
        np.random.seed(7)
        n_samples = 80
        X_anfis = np.random.uniform(-3, 3, (n_samples, 1))
        Y_anfis = np.sin(X_anfis.flatten()) + np.random.normal(0, 0.15, n_samples)
        anfis = SimplifiedANFIS(n_inputs=1, n_mf_per_input=3)
        train_res = anfis.fit(X_anfis, Y_anfis)
        X_pred = np.linspace(-3, 3, 200).reshape(-1, 1)
        Y_pred = anfis.predict(X_pred)
        anfis_plot.clear()
        anfis_plot.plot(X_anfis.flatten(), Y_anfis, pen=None, symbol='o', symbolBrush=pg.mkBrush(BLUE), symbolSize=4, name="Data")
        anfis_plot.plot(X_pred.flatten(), Y_pred, pen=pg.mkPen(ACCENT, width=2), name="ANFIS fit")
        anfis_plot.plot(X_pred.flatten(), np.sin(X_pred.flatten()), pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine), name="True sin(x)")
        anfis_plot.setLabel("left", "y")
        anfis_plot.setLabel("bottom", "x")
        anfis_plot.setTitle(f"ANFIS — {train_res['n_rules']} rules, R2={train_res['r_squared']:.4f}", color=TEXT, size="12pt")
        rules = anfis.get_rules()
        anfis_info.setText(f"MSE = {train_res['mse']:.6f}  |  Rules: {len(rules)}  |  Sample rule: {rules[0] if rules else 'N/A'}")
    except Exception as exc:
        anfis_plot.setTitle(f"ANFIS Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 5: Fuzzy Black-Scholes ----
    fbs_panel, fbs_lay = frame("Fuzzy Black-Scholes Option Pricing", "Option pricing with fuzzy volatility sigma = (sigma_l, sigma_m, sigma_u). Produces a triangular fuzzy number for the call price.")
    fbs_plot = _styled_plot(260)
    fbs_lay.addWidget(fbs_plot, 1)
    fbs_info = QLabel("")
    fbs_info.setObjectName("panelSubtitle")
    fbs_info.setWordWrap(True)
    fbs_lay.addWidget(fbs_info)
    fbs_lay.addStretch()
    root.addWidget(fbs_panel)

    try:
        fbs = FuzzyBlackScholes(S0=100, K=100, T=1.0, r=0.05, sigma_fuzzy=TFN(0.15, 0.20, 0.30))
        fuzzy_price = fbs.fuzzy_call_price()
        sens = fbs.sensitivity_to_volatility(n_points=50)
        fbs_plot.clear()
        fbs_plot.plot(sens["volatilities"], sens["call_prices"], pen=pg.mkPen(ACCENT, width=2), name="Call price")
        fbs_plot.addItem(pg.InfiniteLine(pos=fbs.sigma_fuzzy.l, angle=90, pen=pg.mkPen(BLUE, width=1, style=Qt.PenStyle.DotLine)))
        fbs_plot.addItem(pg.InfiniteLine(pos=fbs.sigma_fuzzy.u, angle=90, pen=pg.mkPen(DANGER, width=1, style=Qt.PenStyle.DotLine)))
        fbs_plot.setLabel("left", "Call price")
        fbs_plot.setLabel("bottom", "Volatility sigma")
        fbs_plot.setTitle(f"Fuzzy BS — Price TFN = ({fuzzy_price.l:.2f}, {fuzzy_price.m:.2f}, {fuzzy_price.u:.2f})", color=TEXT, size="12pt")
        fbs_info.setText(
            f"Crisp BS (sigma=20%): {fbs._bs_call(0.20):.2f}  |  Fuzzy range: [{fuzzy_price.l:.2f}, {fuzzy_price.u:.2f}]  |  "
            f"Price spread: {sens['price_range']:.2f}  |  Defuzzified (centroid): {fuzzy_price.defuzzify():.2f}"
        )
    except Exception as exc:
        fbs_plot.setTitle(f"Fuzzy BS Error: {exc}", color=DANGER, size="12pt")
        fbs_info.setText(str(exc))

    root.addStretch()
    return scroll


# ======================================================================
# Page 11: Advanced Markets
# ======================================================================


def build_advanced_markets_page(parent: QWidget) -> QWidget:
    """Advanced market models: Spence signalling, Rothschild-Stiglitz
    screening, auction mechanisms, Hull-White calibration, trade-off
    theory and pecking order."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Advanced market models",
        "Advanced Markets",
        "Information asymmetry models (Spence signalling, Rothschild-Stiglitz screening), auction mechanisms, Hull-White yield curve calibration and capital structure dynamics.",
    ))

    # ---- Panel 1: Spence Signalling ----
    spence_panel, spence_lay = frame("Spence Job-Market Signalling", "High-type workers signal ability through costly education. Separating vs pooling equilibrium analysis.")
    spence_plot = _styled_plot(260)
    spence_lay.addWidget(spence_plot, 1)
    spence_info = QLabel("")
    spence_info.setObjectName("panelSubtitle")
    spence_info.setWordWrap(True)
    spence_lay.addWidget(spence_info)
    spence_lay.addStretch()
    root.addWidget(spence_panel)

    try:
        sm = SpenceSignallingModel(theta_high=2.0, theta_low=1.0, c_high=0.5, c_low=1.5, frac_high=0.5)
        sep = sm.separating_equilibrium()
        sc = sm.signalling_cost_curve(max_e=10, n_points=100)
        spence_plot.clear()
        spence_plot.plot(sc["education"], sc["net_benefit_high"], pen=pg.mkPen(ACCENT, width=2), name="High-type net benefit")
        spence_plot.plot(sc["education"], sc["net_benefit_low"], pen=pg.mkPen(DANGER, width=2), name="Low-type net benefit")
        pw = sm.pooling_wage()
        spence_plot.addLine(y=pw, pen=pg.mkPen(AMBER, width=1, style=Qt.PenStyle.DashLine), label=f"Pooling wage={pw:.2f}")
        spence_plot.setLabel("left", "Net benefit")
        spence_plot.setLabel("bottom", "Education e")
        exists = "exists" if sep["separating_exists"] else "does NOT exist"
        spence_plot.setTitle(f"Spence Signalling — Separating eq. {exists}", color=TEXT, size="12pt")
        spence_info.setText(f"e* range: [{sep['e_min']:.2f}, {sep['e_max']:.2f}]  |  w_H={sep['wage_high']:.2f}  w_L={sep['wage_low']:.2f}")
    except Exception as exc:
        spence_plot.setTitle(f"Spence error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 2: Rothschild-Stiglitz Screening ----
    rs_panel, rs_lay = frame("Rothschild-Stiglitz Insurance Screening", "Adverse selection in insurance markets. Separating equilibrium with high-risk and low-risk types.")
    rs_info = QLabel("Computing…")
    rs_info.setObjectName("metricValue")
    rs_info.setWordWrap(True)
    rs_lay.addWidget(rs_info)
    rs_lay.addStretch()
    root.addWidget(rs_panel)

    try:
        rs = RothschildStiglitzScreening(
            loss_amount=100, p_low=0.1, p_high=0.3,
            frac_low=0.6, risk_aversion=1.0,
        )
        sep_rs = rs.separating_equilibrium()
        pol_rs = rs.pooling_contract()
        rs_info.setText(
            f"Separating: pi_H={sep_rs['pi_H']:.2f}, q_H={sep_rs['q_H']:.2f} | pi_L={sep_rs['pi_L']:.2f}, q_L={sep_rs['q_L']:.2f}  |  "
            f"Exists: {sep_rs['separating_exists']}  |  Pooling: premium={pol_rs['premium']:.2f}, coverage={pol_rs['coverage']:.2f}"
        )
        rs_info.setStyleSheet(f"color: {ACCENT if sep_rs['separating_exists'] else DANGER};")
    except Exception as exc:
        rs_info.setText(f"RS Error: {exc}")

    # ---- Panel 3: Auction Mechanisms ----
    auc_panel, auc_lay = frame("Auction Mechanism Comparison", "Compare Vickrey (second-price), first-price and uniform-price auction mechanisms.")
    auc_info = QLabel("")
    auc_info.setObjectName("panelSubtitle")
    auc_info.setWordWrap(True)
    auc_lay.addWidget(auc_info)
    auc_lay.addStretch()
    root.addWidget(auc_panel)

    try:
        bids = {"Alice": 95, "Bob": 82, "Carol": 78, "Dave": 71, "Eve": 65}
        results_auc = {}
        for mech in ["vickrey", "first_price", "uniform_price"]:
            a = AuctionMechanism(mechanism=mech)
            r = a.run(bids, reserve_price=60)
            results_auc[mech] = r
        rows_auc = [
            ["Vickrey", results_auc["vickrey"].winner, f"{results_auc['vickrey'].winning_bid:.0f}",
             f"{results_auc['vickrey'].revenue:.0f}", f"{results_auc['vickrey'].allocative_efficiency:.1%}"],
            ["First-price", results_auc["first_price"].winner, f"{results_auc['first_price'].winning_bid:.0f}",
             f"{results_auc['first_price'].revenue:.0f}", f"{results_auc['first_price'].allocative_efficiency:.1%}"],
            ["Uniform-price", results_auc["uniform_price"].winner, f"{results_auc['uniform_price'].winning_bid:.0f}",
             f"{results_auc['uniform_price'].revenue:.0f}", f"{results_auc['uniform_price'].allocative_efficiency:.1%}"],
        ]
        auc_lay.addWidget(make_table(["Mechanism", "Winner", "Winning Bid", "Revenue", "Efficiency"], rows_auc))
        auc_info.setText(f"5 bidders, reserve=60. Vickrey revenue = second-highest bid.")
    except Exception as exc:
        auc_info.setText(f"Auction error: {exc}")

    # ---- Panel 4: Hull-White Calibration ----
    hw_panel, hw_lay = frame("Hull-White Yield Curve Calibration", "Extended Vasicek model calibrated to market yield curve. Compare model-implied vs market yields.")
    hw_plot = _styled_plot(260)
    hw_lay.addWidget(hw_plot, 1)
    hw_lay.addStretch()
    root.addWidget(hw_panel)

    try:
        maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])
        market_rates = np.array([4.5, 4.4, 4.3, 4.1, 4.0, 3.9, 3.95, 4.0, 4.1, 4.0]) / 100
        hw = HullWhiteModel(kappa=0.1, sigma=0.01, r0=0.04)
        hw.calibrate_to_yield_curve(maturities, market_rates)
        comp = hw.model_vs_market_curves(maturities)
        hw_plot.clear()
        hw_plot.plot(comp["maturities"], np.array(comp["market_yields"]) * 100, pen=pg.mkPen(BLUE, width=2), name="Market")
        hw_plot.plot(comp["maturities"], np.array(comp["model_yields"]) * 100, pen=pg.mkPen(ACCENT, width=2), name="Hull-White")
        hw_plot.setLabel("left", "Yield (%)")
        hw_plot.setLabel("bottom", "Maturity (yrs)")
        hw_plot.setTitle("Hull-White vs Market Yield Curve", color=TEXT, size="12pt")
    except Exception as exc:
        hw_plot.setTitle(f"HW Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 5: Trade-Off Theory ----
    to_panel, to_lay = frame("Trade-Off Theory of Capital Structure", "Optimal debt level balances tax shield benefit against bankruptcy cost.")
    to_plot = _styled_plot(260)
    to_lay.addWidget(to_plot, 1)
    to_info = QLabel("")
    to_info.setObjectName("panelSubtitle")
    to_info.setWordWrap(True)
    to_lay.addWidget(to_info)
    to_lay.addStretch()
    root.addWidget(to_panel)

    try:
        to = TradeOffTheory(V_unlevered=1000, T_c=0.25, bankruptcy_alpha=50, bankruptcy_beta=3.0)
        opt = to.optimal_debt()
        frontier = to.frontier_curve(n_points=150)
        to_plot.clear()
        to_plot.plot(frontier["debt"], frontier["firm_value"], pen=pg.mkPen(ACCENT, width=2), name="V(D)")
        to_plot.plot(frontier["debt"], frontier["tax_benefit"], pen=pg.mkPen(BLUE, width=1.5), name="Tax benefit")
        to_plot.plot(frontier["debt"], frontier["bankruptcy_cost"], pen=pg.mkPen(DANGER, width=1.5), name="Bankruptcy cost")
        to_plot.addItem(pg.InfiniteLine(pos=opt["optimal_debt_numerical"], angle=90,
                                         pen=pg.mkPen(AMBER, width=1.5, style=Qt.PenStyle.DashLine)))
        to_plot.setLabel("left", "Value")
        to_plot.setLabel("bottom", "Debt D")
        to_plot.setTitle(f"Trade-Off — Optimal D* = {opt['optimal_debt_numerical']:.0f}", color=TEXT, size="12pt")
        to_info.setText(f"Max firm value: {opt['firm_value_optimal']:.1f}  |  Leverage: {opt['leverage_ratio']:.1%}")
    except Exception as exc:
        to_plot.setTitle(f"Trade-off Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 6: Pecking Order ----
    po_panel, po_lay = frame("Pecking Order Theory Simulation", "Firms prefer internal financing, then debt, then equity. Simulates 20-year capital structure evolution.")
    po_plot = _styled_plot(260)
    po_lay.addWidget(po_plot, 1)
    po_lay.addStretch()
    root.addWidget(po_panel)

    try:
        po = PeckingOrderModel(initial_equity=1000, initial_debt=300, retained_earnings_rate=0.05,
                                investment_needs=200, debt_capacity_ratio=0.6, cost_of_debt=0.06)
        po_res = po.simulate(n_years=20, growth_rate=0.03)
        x_po = po_res["years"]
        po_plot.clear()
        po_plot.plot(x_po, po_res["equity"], pen=pg.mkPen(ACCENT, width=2), name="Equity")
        po_plot.plot(x_po, po_res["debt"], pen=pg.mkPen(AMBER, width=2), name="Debt")
        po_plot.plot(x_po, np.array(po_res["debt_to_value"]) * 100, pen=pg.mkPen(DANGER, width=1.5), name="D/V (%)")
        po_plot.setLabel("left", "Value")
        po_plot.setLabel("bottom", "Year")
        po_plot.setTitle("Pecking Order — Capital Structure Evolution", color=TEXT, size="12pt")
    except Exception as exc:
        po_plot.setTitle(f"Pecking Order Error: {exc}", color=DANGER, size="12pt")

    # ---- Panel 7: Mechanism Design Analyzer ----
    md_panel, md_lay = frame("Mechanism Design — Winner's Curse & Revenue Equivalence", "Analyse auction mechanism properties: allocative efficiency, revenue equivalence and winner's curse bid shading.")
    md_info = QLabel("Computing…")
    md_info.setObjectName("panelSubtitle")
    md_info.setWordWrap(True)
    md_lay.addWidget(md_info)
    md_lay.addStretch()
    root.addWidget(md_panel)

    try:
        # Revenue equivalence check using same bids from auction panel
        bids_md = {"Alice": 95, "Bob": 82, "Carol": 78, "Dave": 71, "Eve": 65}
        a_vick = AuctionMechanism(mechanism="vickrey").run(bids_md, reserve_price=60)
        a_fp = AuctionMechanism(mechanism="first_price").run(bids_md, reserve_price=60)
        re_check = MechanismDesignAnalyzer.revenue_equivalence_check(a_vick, a_fp)
        wc = MechanismDesignAnalyzer.winner_curse_bid_adjustment(n_bidders=5, value_std=15, seed=42)
        md_info.setText(
            f"Revenue Equivalence: Vickrey={a_vick.revenue:.0f} vs First-Price={a_fp.revenue:.0f} (diff {re_check['pct_difference']:.1f}%)  |  "
            f"Winner's Curse (5 bidders, sigma=15): avg overpayment={wc['average_overpayment']:.2f}, "
            f"severity={wc['winner_curse_severity']:.3f}, shade factor={wc['optimal_bid_shading_fraction']:.4f}"
        )
    except Exception as exc:
        md_info.setText(f"Mechanism Design Error: {exc}")

    root.addStretch()
    return scroll


# ======================================================================
# Page 12: Compliance Suite
# ======================================================================


def build_compliance_suite_page(parent: QWidget) -> QWidget:
    """MiFID II best execution, Dodd-Frank compliance and event study
    for semi-strong EMH testing."""
    scroll, inner, root = _scroll_wrapper()
    root.addWidget(SectionTitle(
        "Compliance & event analysis",
        "Compliance Suite",
        "MiFID II best execution analysis, Dodd-Frank Volcker rule and stress testing, and Event Study for semi-strong form EMH.",
    ))

    # ---- Panel 1: MiFID II ----
    mifid_panel, mifid_lay = frame("MiFID II Best Execution Analysis", "Compare execution quality across trading venues. Total cost of ownership analysis.")
    mifid_info = QLabel("Computing…")
    mifid_info.setObjectName("panelSubtitle")
    mifid_info.setWordWrap(True)
    mifid_lay.addWidget(mifid_info)
    mifid_lay.addStretch()
    root.addWidget(mifid_panel)

    try:
        mifid = MiFIDIIAnalyzer(venue_list=["Venue A", "Venue B", "Venue C"])
        venue_execs = {
            "Venue A": {"trades": 500, "avg_spread_bps": 3.2, "fill_rate": 0.95, "avg_slippage_bps": 1.1, "fees_bps": 0.5},
            "Venue B": {"trades": 300, "avg_spread_bps": 2.8, "fill_rate": 0.88, "avg_slippage_bps": 0.9, "fees_bps": 0.8},
            "Venue C": {"trades": 200, "avg_spread_bps": 3.5, "fill_rate": 0.92, "avg_slippage_bps": 1.5, "fees_bps": 0.3},
        }
        be_res = mifid.best_execution_analysis(venue_execs)
        rankings = be_res["venue_rankings"]
        mifid_lay.addWidget(QLabel(f"Best venue: {be_res['best_venue']}  |  Rankings: {rankings}"))
        trades_list = [
            {"venue": "Venue A", "price": 100.50, "quantity": 1000, "fees": 5.0, "commission": 2.0},
            {"venue": "Venue B", "price": 100.48, "quantity": 500, "fees": 4.0, "commission": 1.5},
            {"venue": "Venue C", "price": 100.52, "quantity": 2000, "fees": 3.0, "commission": 2.5},
        ]
        tc_res = mifid.total_cost_analysis(trades_list)
        mifid_info.setText(
            f"Total cost: {tc_res['total_cost_bps']:.2f} bps  |  "
            f"Breakdown: spread={tc_res['cost_breakdown_bps'].get('spread', 'N/A')} bps, "
            f"fees={tc_res['cost_breakdown_bps'].get('fees', 'N/A')} bps  |  {tc_res['n_trades']} trades"
        )
    except Exception as exc:
        mifid_info.setText(f"MiFID II Error: {exc}")

    # ---- Panel 2: Dodd-Frank ----
    df_panel, df_lay = frame("Dodd-Frank Compliance", "Volcker rule check, derivative clearing requirements and stress scenario analysis.")
    df_info = QLabel("Computing…")
    df_info.setObjectName("metricValue")
    df_info.setWordWrap(True)
    df_lay.addWidget(df_info)
    df_lay.addStretch()
    root.addWidget(df_panel)

    try:
        dfa = DoddFrankAnalyzer()
        volcker = dfa.volcker_rule_check(trading_revenue=45, total_revenue=200,
                                          proprietary_positions=500, allowed_activities_revenue=10)
        deriv = dfa.derivative_clearing_check(otc_notional=12e9, cleared_notional=5e9)
        stress = dfa.stress_scenario(
            portfolio_value=1000,
            shocks={"equity": -0.20, "credit": -0.10, "rates": +0.15},
            correlations={"equity_credit": 0.6},
        )
        df_info.setText(
            f"Volcker Rule: Trading revenue = {volcker['trading_revenue_pct']:.1%} of total | Review needed: {volcker['needs_review']}  |  "
            f"Derivative Clearing: {deriv['clearing_percentage']:.1%} cleared | Above threshold: {deriv['above_threshold']} | Mandatory: {deriv['needs_mandatory_clearing']}  |  "
            f"Stress Test: Loss = {stress['loss_pct']:.1%} | Capital adequate: {stress['capital_adequate']}"
        )
        df_info.setStyleSheet(f"color: {ACCENT if stress['capital_adequate'] and not volcker['needs_review'] else DANGER};")
    except Exception as exc:
        df_info.setText(f"Dodd-Frank Error: {exc}")

    # ---- Panel 3: Event Study ----
    es_panel, es_lay = frame("Event Study — Semi-Strong EMH", "Measure abnormal returns around a corporate event using single-index market model.")
    es_plot = _styled_plot(280)
    es_lay.addWidget(es_plot, 1)
    es_info = QLabel("")
    es_info.setObjectName("panelSubtitle")
    es_info.setWordWrap(True)
    es_lay.addWidget(es_info)
    es_lay.addStretch()
    root.addWidget(es_panel)

    try:
        np.random.seed(55)
        n_days = 300
        market_rets = np.random.normal(0.0005, 0.01, n_days)
        beta_true = 1.2
        asset_rets = 0.0003 + beta_true * market_rets + np.random.normal(0, 0.008, n_days)
        # Inject event effect at day 250
        event_day = 250
        asset_rets[event_day] += 0.04  # +4% abnormal return
        es = EventStudy(asset_rets, market_rets, event_date=event_day,
                        estimation_window=(-240, -11), event_window=(-5, 5))
        mm = es.estimate_market_model()
        ar_res = es.compute_abnormal_returns()
        es_plot.clear()
        days = ar_res["event_days"]
        es_plot.plot(days, ar_res["cumulative_abnormal_returns"], pen=pg.mkPen(ACCENT, width=2), name="CAR")
        es_plot.addLine(y=0, pen=pg.mkPen(MUTED, width=1, style=Qt.PenStyle.DashLine))
        es_plot.addItem(pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(AMBER, width=1.5, style=Qt.PenStyle.DotLine)))
        es_plot.setLabel("left", "CAR")
        es_plot.setLabel("bottom", "Event day")
        es_plot.setTitle(f"Event Study — CAR = {ar_res['total_CAR']:.4f} (beta={mm['beta']:.3f}, R2={mm['r_squared']:.3f})", color=TEXT, size="12pt")
        es_info.setText(
            f"Model: alpha={mm['alpha']:.6f}, beta={mm['beta']:.3f}, R2={mm['r_squared']:.3f}  |  "
            f"Total CAR: {ar_res['total_CAR']:.4f}  |  Event day: {event_day}"
        )
    except Exception as exc:
        es_plot.setTitle(f"Event Study Error: {exc}", color=DANGER, size="12pt")
        es_info.setText(str(exc))

    root.addStretch()
    return scroll
