r"""
Quant Engine Batch 1 Tests
===========================
Tests for 10 quant_engine modules. Each test is independent and fast (< 2s).
Uses numpy seed 42 where random data is needed. No GUI imports.

Modules tested:
1. macro_models
2. garch_model
3. black_litterman
4. transfer_entropy
5. behavioral_finance
6. political_risk (+ climate_risk for HotellingRule, InnovationSCurve)
7. anomaly_detection
8. market_microstructure
9. capital_structure
10. epidemiological_economics
"""

import numpy as np
import pytest


# ==================================================================
# 1. macro_models
# ==================================================================


class TestMacroModels:
    """Tests for TaylorRule, PhillipsCurve, DSGESimple, MinskyCycle, KondratievWave."""

    def test_taylor_rule_predict_rate(self):
        from quant_engine import TaylorRule
        tr = TaylorRule()
        result = tr.predict_rate(3.0, 1.0)
        assert isinstance(result, float)
        # With defaults: r* + pi* + 1.5*(3-2) + 0.5*1 = 2+2+1.5+0.5 = 6.0
        assert abs(result - 6.0) < 1e-10

    def test_phillips_curve_predict_inflation(self):
        from quant_engine import PhillipsCurve
        pc = PhillipsCurve()
        result = pc.predict_inflation(6.0)
        assert isinstance(result, float)
        # 2.0 - 0.5*(6-5) = 1.5
        assert abs(result - 1.5) < 1e-10

    def test_dsge_simulate_shocks(self):
        from quant_engine import DSGESimple
        dsge = DSGESimple()
        periods = 40
        result = dsge.simulate_shocks(
            np.zeros(periods), np.zeros(periods), np.zeros(periods), periods
        )
        assert isinstance(result, dict)
        for key in ("output_gap", "inflation", "interest_rate"):
            assert key in result
            assert isinstance(result[key], np.ndarray)
            assert len(result[key]) == periods

    def test_minsky_cycle_simulate(self):
        from quant_engine import MinskyCycle
        mc = MinskyCycle()
        result = mc.simulate(periods=30)
        assert isinstance(result, np.ndarray)
        assert result.shape == (30, 3)

    def test_kondratiev_wave_generate(self):
        from quant_engine import KondratievWave
        kw = KondratievWave()
        result = kw.generate_wave(1900, 2020)
        assert isinstance(result, dict)
        assert "years" in result
        assert "wave" in result
        assert "phase" in result
        assert isinstance(result["years"], np.ndarray)
        assert isinstance(result["wave"], np.ndarray)
        assert len(result["years"]) == 121  # 1900..2020 inclusive


# ==================================================================
# 2. garch_model
# ==================================================================


class TestGARCHModel:
    """Tests for GARCH11: fit, var, cvar, forecast, summary."""

    def test_garch_fit_and_attrs(self, sample_returns):
        from quant_engine import GARCH11
        model = GARCH11(sample_returns).fit()
        assert model.omega is not None
        assert model.alpha is not None
        assert model.beta is not None
        assert isinstance(model.omega, float)
        assert isinstance(model.alpha, float)
        assert isinstance(model.beta, float)
        assert model.omega >= 0
        assert 0 <= model.alpha < 1
        assert 0 <= model.beta < 1

    def test_garch_var(self, sample_returns):
        from quant_engine import GARCH11
        model = GARCH11(sample_returns).fit()
        result = model.var(0.95)
        assert isinstance(result, float)
        assert result >= 0

    def test_garch_cvar(self, sample_returns):
        from quant_engine import GARCH11
        model = GARCH11(sample_returns).fit()
        result = model.cvar(0.95)
        assert isinstance(result, (float, np.floating))

    def test_garch_forecast(self, sample_returns):
        from quant_engine import GARCH11
        model = GARCH11(sample_returns).fit()
        result = model.forecast(5)
        assert isinstance(result, np.ndarray)
        assert result.shape == (5,)
        assert np.all(result >= 0)

    def test_garch_summary(self, sample_returns):
        from quant_engine import GARCH11
        model = GARCH11(sample_returns).fit()
        result = model.summary()
        assert isinstance(result, dict)
        assert len(result) == 8
        expected_keys = {
            "omega", "alpha", "beta",
            "persistence (\u03b1+\u03b2)", "unconditional_variance",
            "log_likelihood", "aic", "bic",
        }
        assert set(result.keys()) == expected_keys


# ==================================================================
# 3. black_litterman
# ==================================================================


class TestBlackLitterman:
    """Tests for BlView and BlackLittermanModel."""

    def test_bl_view_creation(self):
        from quant_engine import BlView
        view = BlView(asset=0, view_return=0.06, confidence=0.5)
        assert view.asset == 0
        assert view.view_return == 0.06
        assert view.confidence == 0.5

    def test_bl_model_run(self):
        from quant_engine import BlView, BlackLittermanModel
        np.random.seed(42)
        tickers = ["A", "B", "C"]
        N = len(tickers)
        A = np.random.randn(N, N) * 0.01
        cov = A.T @ A + np.eye(N) * 0.001
        w_mkt = np.array([0.5, 0.3, 0.2])

        views = [BlView(asset="A", view_return=0.06, confidence=0.5)]
        model = BlackLittermanModel(w_mkt, cov)
        result = model.run(views, tickers)

        assert isinstance(result, dict)
        assert "implied_returns" in result
        assert "posterior_returns" in result
        assert isinstance(result["implied_returns"], np.ndarray)
        assert isinstance(result["posterior_returns"], np.ndarray)
        assert len(result["implied_returns"]) == N
        assert len(result["posterior_returns"]) == N


# ==================================================================
# 4. transfer_entropy
# ==================================================================


class TestTransferEntropy:
    """Tests for shannon_entropy, transfer_entropy, network_analysis."""

    def test_shannon_entropy(self):
        from quant_engine import shannon_entropy
        np.random.seed(42)
        arr = np.random.randn(500)
        result = shannon_entropy(arr)
        assert isinstance(result, float)
        assert result >= 0

    def test_transfer_entropy_dict(self):
        from quant_engine import transfer_entropy
        np.random.seed(42)
        src = np.random.randn(500)
        tgt = np.random.randn(500)
        result = transfer_entropy(src, tgt, lag=1, bins=8)
        assert isinstance(result, dict)
        assert "te" in result
        assert "te_normalized" in result
        assert isinstance(result["te"], float)
        assert isinstance(result["te_normalized"], float)
        assert result["te"] >= 0

    def test_network_analysis(self):
        from quant_engine import network_analysis
        np.random.seed(42)
        T = 300
        matrix = np.column_stack([
            np.random.randn(T),
            np.random.randn(T),
            np.random.randn(T),
        ])
        names = ["X", "Y", "Z"]
        result = network_analysis(matrix, names)
        assert isinstance(result, dict)
        assert "te_matrix" in result
        assert isinstance(result["te_matrix"], np.ndarray)
        assert result["te_matrix"].shape == (3, 3)


# ==================================================================
# 5. behavioral_finance
# ==================================================================


class TestBehavioralFinance:
    """Tests for ProspectTheory, DispositionEffect, HerdingModel."""

    def test_prospect_theory_value_function(self):
        from quant_engine import ProspectTheory
        pt = ProspectTheory()
        result = pt.value_function(np.array([-1.0, 0.0, 1.0]))
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        # Losses hurt more than equivalent gains
        assert result[0] < 0  # loss is negative
        assert result[1] == 0.0  # zero
        assert result[2] > 0  # gain is positive
        assert abs(result[0]) > abs(result[2])  # loss aversion

    def test_prospect_theory_probability_weight(self):
        from quant_engine import ProspectTheory
        pt = ProspectTheory()
        result = pt.probability_weight(0.5)
        assert isinstance(result, float)
        assert 0 < result < 1

    def test_disposition_effect_simulate(self):
        from quant_engine import DispositionEffect
        de = DispositionEffect()
        np.random.seed(42)
        winners = np.abs(np.random.normal(50, 20, 20))
        losers = -np.abs(np.random.normal(30, 15, 20))
        result = de.simulate_trading(winners, losers, holding_period_win=5, holding_period_loss=5)
        assert isinstance(result, dict)
        assert "realized_pnl" in result
        assert "optimal_pnl" in result
        assert "disposition_cost" in result
        assert isinstance(result["realized_pnl"], float)

    def test_herding_model_simulate(self):
        from quant_engine import HerdingModel
        hm = HerdingModel()
        result = hm.simulate_decisions(n_agents=20)
        assert isinstance(result, dict)
        assert "decisions" in result
        assert isinstance(result["decisions"], np.ndarray)
        assert len(result["decisions"]) == 20
        assert "cascade_start" in result
        assert "true_quality" in result


# ==================================================================
# 6. political_risk  (includes HotellingRule, InnovationSCurve from climate_risk)
# ==================================================================


class TestPoliticalRisk:
    """Tests for PoliticalRiskScore, SanctionImpactModel, HotellingRule, InnovationSCurve."""

    def test_political_risk_score(self):
        from quant_engine import PoliticalRiskScore
        prs = PoliticalRiskScore()
        econ = {"gdp_growth": 60, "inflation": 50}
        pol = {"stability": 70, "corruption": 65}
        fin = {"current_account": 55, "fx_reserves": 60}
        result = prs.compute(econ, pol, fin)
        assert isinstance(result, dict)
        assert "composite_score" in result
        assert "risk_rating" in result
        assert isinstance(result["composite_score"], float)
        assert isinstance(result["risk_rating"], str)

    def test_sanction_impact_model(self):
        from quant_engine import SanctionImpactModel
        sim = SanctionImpactModel()
        result = sim.estimate_gdp_impact(0.25, 0.7, 10)
        assert isinstance(result, dict)
        assert "total_loss" in result
        assert isinstance(result["total_loss"], float)
        assert result["total_loss"] > 0

    def test_hotelling_rule_price_path(self):
        from quant_engine import HotellingRule
        hr = HotellingRule()
        result = hr.optimal_price_path()
        assert isinstance(result, dict)
        assert "prices" in result
        assert isinstance(result["prices"], np.ndarray)
        assert len(result["prices"]) == 50

    def test_innovation_s_curve(self):
        from quant_engine import InnovationSCurve
        isc = InnovationSCurve()
        result = isc.adoption_curve()
        assert isinstance(result, dict)
        assert "peak_period" in result
        assert isinstance(result["peak_period"], (int, np.integer))
        assert "cumulative_adopters" in result


# ==================================================================
# 7. anomaly_detection
# ==================================================================


class TestAnomalyDetection:
    """Tests for PriceManipulationDetector, AccountingFraudDetector."""

    def test_price_manipulation_detect_all(self):
        from quant_engine import PriceManipulationDetector
        np.random.seed(42)
        T = 200
        prices = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, T)))
        volumes = 1e6 + np.random.normal(0, 2e5, T)
        pmd = PriceManipulationDetector()
        result = pmd.detect_all(prices, volumes)
        assert isinstance(result, dict)
        assert "anomaly_count" in result
        assert isinstance(result["anomaly_count"], np.ndarray)
        assert len(result["anomaly_count"]) == T

    def test_accounting_fraud_m_score(self):
        from quant_engine import AccountingFraudDetector
        afd = AccountingFraudDetector()
        ratios = {
            "DSRI": 1.15,
            "GMI": 1.10,
            "AQI": 1.15,
            "SGI": 1.30,
            "DEPI": 0.85,
            "SGAI": 1.05,
            "TATA": 0.08,
            "LVGI": 1.20,
        }
        result = afd.compute_m_score(ratios)
        assert isinstance(result, dict)
        assert "m_score" in result
        assert isinstance(result["m_score"], float)
        assert "probability" in result
        assert "interpretation" in result

    def test_accounting_fraud_altman_z(self):
        from quant_engine import AccountingFraudDetector
        afd = AccountingFraudDetector()
        result = afd.altman_z_score(
            working_capital=50e6,
            total_assets=200e6,
            retained_earnings=40e6,
            ebit=15e6,
            market_cap=120e6,
            total_liabilities=80e6,
            sales=250e6,
        )
        assert isinstance(result, dict)
        assert "z_score" in result
        assert isinstance(result["z_score"], float)
        assert "zone" in result


# ==================================================================
# 8. market_microstructure
# ==================================================================


class TestMarketMicrostructure:
    """Tests for AuctionMechanism, AkerlofLemonsModel, SpenceSignallingModel, MechanismDesignAnalyzer."""

    def test_auction_vickrey(self):
        from quant_engine import AuctionMechanism
        auction = AuctionMechanism("vickrey")
        result = auction.run({"A": 95, "B": 82}, reserve_price=60)
        assert hasattr(result, "winner")
        assert result.winner == "A"
        assert result.winning_bid == 95
        # Second-price: pays 82
        assert result.second_price == 82

    def test_akerlof_lemons(self):
        from quant_engine import AkerlofLemonsModel
        model = AkerlofLemonsModel()
        result = model.find_equilibrium()
        assert isinstance(result, dict)
        assert "market_collapsed" in result
        assert isinstance(result["market_collapsed"], (bool, np.bool_))
        assert "equilibrium_price" in result

    def test_spence_signalling(self):
        from quant_engine import SpenceSignallingModel
        model = SpenceSignallingModel()
        result = model.separating_equilibrium()
        assert isinstance(result, dict)
        assert "separating_exists" in result
        assert isinstance(result["separating_exists"], bool)
        assert "e_min" in result
        assert "e_max" in result

    def test_mechanism_design_winner_curse(self):
        from quant_engine import MechanismDesignAnalyzer
        result = MechanismDesignAnalyzer.winner_curse_bid_adjustment(5, 15, seed=42)
        assert isinstance(result, dict)
        assert "average_overpayment" in result
        assert isinstance(result["average_overpayment"], float)


# ==================================================================
# 9. capital_structure
# ==================================================================


class TestCapitalStructure:
    """Tests for ModiglianiMiller, TradeOffTheory, PeckingOrderModel."""

    def test_mm_prop1_no_tax(self):
        from quant_engine import ModiglianiMiller
        mm = ModiglianiMiller()
        result = mm.prop1_no_tax(200)
        assert isinstance(result, dict)
        assert "V_levered" in result
        assert "equity_value" in result
        assert "debt_value" in result
        # MM without tax: V_L = V_U regardless of D
        assert result["V_levered"] == result["V_unlevered"]

    def test_mm_leverage_sweep(self):
        from quant_engine import ModiglianiMiller
        mm = ModiglianiMiller()
        result = mm.leverage_sweep()
        assert isinstance(result, dict)
        assert "debt" in result
        assert "V_levered" in result
        assert isinstance(result["debt"], np.ndarray)
        assert isinstance(result["V_levered"], np.ndarray)

    def test_trade_off_optimal_debt(self):
        from quant_engine import TradeOffTheory
        tot = TradeOffTheory()
        result = tot.optimal_debt()
        assert isinstance(result, dict)
        assert "optimal_debt_analytical" in result
        assert "firm_value_optimal" in result
        assert isinstance(result["optimal_debt_analytical"], float)
        assert isinstance(result["firm_value_optimal"], float)

    def test_pecking_order_simulate(self):
        from quant_engine import PeckingOrderModel
        pom = PeckingOrderModel()
        result = pom.simulate(10)
        assert isinstance(result, dict)
        assert "equity" in result
        assert "debt" in result
        assert "debt_to_value" in result
        assert isinstance(result["equity"], np.ndarray)
        assert isinstance(result["debt"], np.ndarray)
        # 10 years + initial = 11 entries
        assert len(result["equity"]) == 11


# ==================================================================
# 10. epidemiological_economics
# ==================================================================


class TestEpidemiologicalEconomics:
    """Tests for SIRModel and EconomicImpactSIR."""

    def test_sir_model_simulate(self):
        from quant_engine import SIRModel
        sir = SIRModel(R0=2.5)
        result = sir.simulate(T=365)
        assert isinstance(result, dict)
        assert "peak_day" in result
        assert "attack_rate" in result
        assert isinstance(result["peak_day"], (int, float, np.floating, np.integer))
        assert isinstance(result["attack_rate"], (float, np.floating))
        assert 0 < result["attack_rate"] <= 1
        assert result["peak_day"] > 0
        # Also check standard keys
        for key in ("S", "I", "R", "time"):
            assert key in result

    def test_economic_impact_sir(self):
        from quant_engine import SIRModel, EconomicImpactSIR
        sir = SIRModel(R0=2.5)
        sir_result = sir.simulate(T=365)
        eis = EconomicImpactSIR()
        result = eis.assess(sir_result)
        assert isinstance(result, dict)
        assert "total_loss_pct_gdp" in result
        assert isinstance(result["total_loss_pct_gdp"], (float, np.floating))
        # Pandemic should cause negative GDP impact
        assert result["total_loss_pct_gdp"] < 0
        assert "daily_gdp_impact_pct" in result
        assert "recovery_day" in result
