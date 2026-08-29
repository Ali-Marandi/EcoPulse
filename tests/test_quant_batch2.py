"""
Test batch 2 — 11 quant_engine modules.
Minimal-arg smoke tests: import, call, assert types/keys/shapes.
numpy seed 42 everywhere. No GUI.
"""
import numpy as np
import pytest


# ====================================================================
# 1. interest_rate_models
# ====================================================================
class TestInterestRateModels:
    def test_vasicek_yield_curve(self):
        from quant_engine import VasicekModel
        result = VasicekModel().yield_curve()
        assert isinstance(result, dict)
        assert 'maturities' in result
        assert 'yields' in result
        assert isinstance(result['maturities'], np.ndarray)
        assert isinstance(result['yields'], np.ndarray)
        assert len(result['maturities']) == len(result['yields'])
        assert len(result['maturities']) > 0

    def test_cir_yield_curve(self):
        from quant_engine import CIRModel
        result = CIRModel().yield_curve()
        assert isinstance(result, dict)
        assert 'maturities' in result
        assert 'yields' in result
        assert isinstance(result['maturities'], np.ndarray)
        assert isinstance(result['yields'], np.ndarray)
        assert len(result['maturities']) > 0

    def test_cir_feller_condition(self):
        from quant_engine import CIRModel
        model = CIRModel(kappa=0.5, theta=0.05, sigma=0.1, r0=0.03)
        result = model.feller_condition
        assert isinstance(result, bool)

    def test_hull_white_calibrate_and_curves(self):
        from quant_engine import HullWhiteModel
        np.random.seed(42)
        mats = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
        rates = np.array([0.03, 0.032, 0.035, 0.038, 0.042, 0.045, 0.047, 0.048])
        hw = HullWhiteModel()
        hw.calibrate_to_yield_curve(mats, rates)
        result = hw.model_vs_market_curves()
        assert isinstance(result, dict)
        assert 'model_yields' in result
        assert 'market_yields' in result
        assert isinstance(result['model_yields'], np.ndarray)
        assert isinstance(result['market_yields'], np.ndarray)
        assert len(result['model_yields']) == len(result['market_yields'])

    def test_bs_call_price(self):
        from quant_engine import BlackScholesModel
        bs = BlackScholesModel()
        result = bs.call_price(100, 1.0)
        assert isinstance(result, (int, float, np.floating))

    def test_bs_put_price(self):
        from quant_engine import BlackScholesModel
        bs = BlackScholesModel()
        result = bs.put_price(100, 1.0)
        assert isinstance(result, (int, float, np.floating))

    def test_bs_greeks(self):
        from quant_engine import BlackScholesModel
        bs = BlackScholesModel()
        result = bs.greeks(100, 1.0)
        assert isinstance(result, dict)
        for key in ('delta', 'gamma', 'vega', 'theta', 'rho'):
            assert key in result, f"Missing greek key: {key}"
            assert isinstance(result[key], (int, float, np.floating))

    def test_bs_volatility_smile(self):
        from quant_engine import BlackScholesModel
        bs = BlackScholesModel()
        result = bs.volatility_smile(T=1.0)
        assert isinstance(result, dict)
        assert 'implied_vols' in result
        assert isinstance(result['implied_vols'], np.ndarray)
        assert len(result['implied_vols']) > 0

    def test_bs_put_call_parity_price(self):
        from quant_engine import BlackScholesModel
        bs = BlackScholesModel()
        result = bs.put_call_parity_price(100, 1.0)
        assert isinstance(result, dict)


# ====================================================================
# 2. pca_factors
# ====================================================================
class TestPCAFactors:
    def test_pca_factor_extractor(self):
        from quant_engine.pca_factors import PCAFactorExtractor
        np.random.seed(42)
        returns_matrix = np.random.randn(100, 3)
        result = PCAFactorExtractor(n_components=0.90).fit_transform(
            returns_matrix, ['A', 'B', 'C']
        )
        assert isinstance(result, dict)
        assert 'factors' in result
        assert 'explained_var_ratio' in result
        assert 'factor_names' in result
        assert isinstance(result['factors'], np.ndarray)
        assert isinstance(result['explained_var_ratio'], np.ndarray)
        assert isinstance(result['factor_names'], list)
        assert len(result['factor_names']) > 0

    def test_yield_curve_decomposition(self):
        from quant_engine.pca_factors import yield_curve_decomposition
        np.random.seed(42)
        yields = np.random.randn(100, 5) * 0.5 + 4.0
        result = yield_curve_decomposition(yields)
        assert isinstance(result, dict)
        assert 'level' in result
        assert 'slope' in result
        assert 'curvature' in result
        assert isinstance(result['level'], np.ndarray)
        assert isinstance(result['slope'], np.ndarray)
        assert isinstance(result['curvature'], np.ndarray)
        assert len(result['level']) == 100
        assert len(result['slope']) == 100
        assert len(result['curvature']) == 100


# ====================================================================
# 3. market_efficiency
# ====================================================================
class TestMarketEfficiency:
    def test_runs_test(self):
        from quant_engine import WeakFormEMHTests
        np.random.seed(42)
        returns = np.random.randn(300) * 0.02
        emh = WeakFormEMHTests(returns)
        result = emh.runs_test()
        assert isinstance(result, dict)
        assert 'p_value' in result

    def test_variance_ratio_test(self):
        from quant_engine import WeakFormEMHTests
        np.random.seed(42)
        returns = np.random.randn(300) * 0.02
        emh = WeakFormEMHTests(returns)
        result = emh.variance_ratio_test(q=2)
        assert isinstance(result, dict)
        assert 'p_value' in result

    def test_full_report(self):
        from quant_engine import WeakFormEMHTests
        np.random.seed(42)
        returns = np.random.randn(300) * 0.02
        emh = WeakFormEMHTests(returns)
        result = emh.full_report()
        assert isinstance(result, dict)
        assert 'summary' in result

    def test_event_study(self):
        from quant_engine import EventStudy
        np.random.seed(42)
        n = 500
        mkt_rets = np.random.randn(n) * 0.015
        asset_rets = 0.8 * mkt_rets + np.random.randn(n) * 0.02
        es = EventStudy(asset_rets, mkt_rets, event_date=150)

        model = es.estimate_market_model()
        assert isinstance(model, dict)
        assert 'beta' in model
        assert 'r_squared' in model

        ab = es.compute_abnormal_returns()
        assert isinstance(ab, dict)
        assert 'total_CAR' in ab


# ====================================================================
# 4. regulatory_framework
# ====================================================================
class TestRegulatoryFramework:
    def test_basel_capital_dataclass(self):
        from quant_engine import BaselIIICapital
        cap = BaselIIICapital(
            common_equity_tier1=120,
            additional_tier1=30,
            tier2=50,
            total_assets=5000,
            risk_weighted_assets=3000,
            total_exposure=4000,
            hqla=800,
            net_cash_outflows_30d=600,
            available_stable_funding=2000,
            required_stable_funding=1500,
        )
        assert cap.common_equity_tier1 == 120
        assert cap.tier1_capital == 150
        assert cap.total_capital == 200

    def test_basel_compliance_check(self):
        from quant_engine import BaselIIICapital, BaselIIICompliance
        cap = BaselIIICapital(
            common_equity_tier1=120,
            additional_tier1=30,
            tier2=50,
            total_assets=5000,
            risk_weighted_assets=3000,
            total_exposure=4000,
            hqla=800,
            net_cash_outflows_30d=600,
            available_stable_funding=2000,
            required_stable_funding=1500,
        )
        result = BaselIIICompliance().compliance_check(cap)
        assert isinstance(result, dict)
        assert 'compliant' in result
        assert 'ratios' in result

    def test_mifid_best_execution(self):
        from quant_engine import MiFIDIIAnalyzer
        venue_execs = {
            "XEON": {"avg_price_deviation": 0.02, "avg_fill_rate": 0.95,
                       "avg_speed_ms": 50, "n_trades": 1000, "total_volume": 50000},
            "XPAR": {"avg_price_deviation": 0.05, "avg_fill_rate": 0.88,
                       "avg_speed_ms": 120, "n_trades": 800, "total_volume": 40000},
        }
        result = MiFIDIIAnalyzer().best_execution_analysis(venue_execs)
        assert isinstance(result, dict)

    def test_dodd_frank_volcker(self):
        from quant_engine import DoddFrankAnalyzer
        result = DoddFrankAnalyzer().volcker_rule_check(
            45, 200, proprietary_positions={"equity": 500}
        )
        assert isinstance(result, dict)
        assert 'needs_review' in result


# ====================================================================
# 5. time_series_advanced
# ====================================================================
class TestTimeSeriesAdvanced:
    def test_fit_arima(self):
        from quant_engine import fit_arima
        np.random.seed(42)
        series = np.cumsum(np.random.randn(200) * 0.5) + 100
        result = fit_arima(series, order=(1, 1, 1), forecast_steps=5)
        assert isinstance(result, dict)
        assert 'aic' in result
        assert 'bic' in result
        assert 'forecast_mean' in result
        assert isinstance(result['forecast_mean'], np.ndarray)
        assert len(result['forecast_mean']) == 5

    def test_granger_causality_test(self):
        from quant_engine import granger_causality_test
        np.random.seed(42)
        n = 300
        y1 = np.zeros(n)
        y2 = np.zeros(n)
        for t in range(2, n):
            y1[t] = 0.5 * y1[t - 1] + 0.3 * y2[t - 1] + np.random.randn() * 0.3
            y2[t] = 0.2 * y1[t - 1] + 0.6 * y2[t - 1] + np.random.randn() * 0.3
        result = granger_causality_test(y1, y2)
        assert isinstance(result, dict)
        assert 'p_value' in result

    def test_cusum_change_detection(self):
        from quant_engine import cusum_change_detection
        np.random.seed(42)
        series = np.concatenate([
            np.random.normal(0, 1, 100),
            np.random.normal(3, 1, 100),
            np.random.normal(0, 1, 100),
        ])
        result = cusum_change_detection(series)
        assert isinstance(result, dict)
        assert 'change_points' in result

    def test_fit_var(self):
        from quant_engine import fit_var
        np.random.seed(42)
        n = 300
        data = np.column_stack([
            np.cumsum(np.random.randn(n) * 0.5),
            np.cumsum(np.random.randn(n) * 0.5),
        ])
        result = fit_var(data, maxlags=2, forecast_steps=5)
        assert isinstance(result, dict)
        assert 'selected_lag' in result
        assert 'forecast' in result


# ====================================================================
# 6. causal_inference
# ====================================================================
class TestCausalInference:
    def test_causal_dag(self):
        from quant_engine import CausalDAG
        dag = CausalDAG()
        dag.add_node('A')
        dag.add_edges([
            ('A', 'B'), ('B', 'C'), ('A', 'D'), ('D', 'E'),
            ('B', 'E'),
        ])
        result = dag.find_adjustment_set('A', 'E')
        assert isinstance(result, dict)
        assert 'adjustment_set' in result

    def test_instrumental_variables(self):
        from quant_engine import InstrumentalVariables
        np.random.seed(42)
        n = 200
        Z = np.random.randn(n)
        X = 0.8 * Z + np.random.randn(n) * 0.3
        Y = 1.5 * X + np.random.randn(n) * 0.5
        result = InstrumentalVariables().estimate(Y, X, Z)
        assert isinstance(result, dict)
        assert 'iv_estimate' in result
        assert 'first_stage_f_stat' in result

    def test_double_ml(self):
        from quant_engine import DoubleML
        np.random.seed(42)
        n = 200
        X = np.random.randn(n, 3)
        T = X[:, 0] * 0.5 + np.random.randn(n) * 0.3
        Y = 2.0 * T + X[:, 1] + np.random.randn(n) * 0.3
        result = DoubleML(n_folds=3).estimate(Y, T, X)
        assert isinstance(result, dict)
        assert 'ate' in result
        assert 'p_value' in result

    def test_difference_in_differences(self):
        from quant_engine import DifferenceInDifferences
        np.random.seed(42)
        ypt = np.random.randn(100) * 1.0 + 10
        ypostt = np.random.randn(100) * 1.0 + 14
        ypc = np.random.randn(100) * 1.0 + 10
        ypostc = np.random.randn(100) * 1.0 + 11
        result = DifferenceInDifferences().estimate(ypt, ypostt, ypc, ypostc)
        assert isinstance(result, dict)
        assert 'att' in result

    def test_psm(self):
        from quant_engine import PropensityScoreMatching
        np.random.seed(42)
        n = 200
        X = np.random.randn(n, 3)
        T = (X[:, 0] > 0).astype(float)
        Y = 2.0 * T + X[:, 1] + np.random.randn(n) * 0.3
        result = PropensityScoreMatching().match_and_estimate(Y, T, X)
        assert isinstance(result, dict)
        assert 'att' in result
        assert 'n_matched' in result


# ====================================================================
# 7. fuzzy_advanced
# ====================================================================
class TestFuzzyAdvanced:
    def test_tfn_membership(self):
        from quant_engine import TFN
        t = TFN(1, 2, 3)
        result = t.membership(2)
        assert isinstance(result, float)
        assert result == 1.0

    def test_tfn_defuzzify(self):
        from quant_engine import TFN
        t = TFN(1, 2, 3)
        result = t.defuzzify()
        assert isinstance(result, float)
        assert abs(result - 2.0) < 1e-6

    def test_tfn_alpha_cut(self):
        from quant_engine import TFN
        t = TFN(1, 2, 3)
        result = t.alpha_cut(0.5)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_fuzzy_ahp(self):
        from quant_engine import FuzzyAHP, TFN
        ahp = FuzzyAHP(criteria=['C1', 'C2', 'C3'])
        ahp.set_comparison_crisp('C1', 'C2', 3)
        ahp.set_comparison_crisp('C1', 'C3', 5)
        ahp.set_comparison_crisp('C2', 'C3', 2)
        result = ahp.compute_weights()
        assert isinstance(result, dict)
        assert 'weights' in result

    def test_fuzzy_topsis(self):
        from quant_engine import FuzzyTOPSIS, TFN
        topsis = FuzzyTOPSIS(
            alternatives=['Alt1', 'Alt2', 'Alt3'],
            criteria=['C1', 'C2', 'C3'],
        )
        for alt in ['Alt1', 'Alt2', 'Alt3']:
            for crit in ['C1', 'C2', 'C3']:
                topsis.set_rating_crisp(alt, crit, np.random.uniform(3, 9))
        result = topsis.rank()
        assert isinstance(result, dict)
        assert 'rankings' in result
        assert isinstance(result['rankings'], list)
        assert len(result['rankings']) == 3

    def test_fuzzy_black_scholes(self):
        from quant_engine import FuzzyBlackScholes, TFN
        fbs = FuzzyBlackScholes(S0=100, sigma_fuzzy=TFN(0.15, 0.20, 0.30))
        price = fbs.fuzzy_call_price()
        assert isinstance(price, TFN)
        sens = fbs.sensitivity_to_volatility()
        assert isinstance(sens, dict)


# ====================================================================
# 8. fuzzy_credit
# ====================================================================
class TestFuzzyCredit:
    def test_credit_scorer(self):
        from quant_engine import FuzzyCreditScorer
        scorer = FuzzyCreditScorer()
        result = scorer.evaluate(
            income=60, debt_ratio=30, payment_history=70, employment_years=10
        )
        assert isinstance(result, dict)
        assert 'credit_score' in result
        assert 0 <= result['credit_score'] <= 100


# ====================================================================
# 9. contagion_network
# ====================================================================
class TestContagionNetwork:
    def test_financial_network_contagion(self):
        from quant_engine import FinancialNetwork
        fn = FinancialNetwork(n_banks=5, seed=42)
        result = fn.simulate_contagion(initial_shock_bank=0)
        assert isinstance(result, dict)
        assert 'n_defaults' in result

    def test_financial_network_systemic_risk(self):
        from quant_engine import FinancialNetwork
        fn = FinancialNetwork(n_banks=5, seed=42)
        result = fn.systemic_risk_metrics()
        assert isinstance(result, dict)

    def test_debt_rank(self):
        from quant_engine import DebtRank
        np.random.seed(42)
        N = 5
        adj = np.random.rand(N, N) * 0.1
        np.fill_diagonal(adj, 0)
        cap = 0.1 + 0.2 * np.random.rand(N)
        result = DebtRank(adj, cap).compute()
        assert isinstance(result, np.ndarray)
        assert result.shape == (N,)

    def test_correlation_network(self):
        from quant_engine import CorrelationNetwork
        np.random.seed(42)
        returns = np.random.randn(100, 5) * 0.02
        cn = CorrelationNetwork(returns)
        result = cn.build_network()
        assert isinstance(result, np.ndarray)


# ====================================================================
# 10. climate_risk
# ====================================================================
class TestClimateRisk:
    def test_climate_var(self):
        from quant_engine import ClimateVaR
        np.random.seed(42)
        asset_vals = np.array([1e9, 5e8, 2e9, 8e8, 1.5e9])
        temp_array = np.linspace(1.5, 4.5, 50)
        result = ClimateVaR().physical_risk(asset_vals, temp_array)
        assert isinstance(result, dict)
        assert 'var_95' in result
        assert isinstance(result['var_95'], np.ndarray)

    def test_innovation_s_curve(self):
        from quant_engine import InnovationSCurve
        result = InnovationSCurve().adoption_curve()
        assert isinstance(result, dict)
        assert 'peak_period' in result


# ====================================================================
# 11. monte_carlo_risk
# ====================================================================
class TestMonteCarloRisk:
    def test_simulate(self):
        from quant_engine import MonteCarloRiskEngine
        np.random.seed(42)
        N = 3
        weights = np.array([0.4, 0.3, 0.3])
        mu = np.array([0.08, 0.03, 0.06])
        cov = np.array([
            [0.04, 0.005, 0.01],
            [0.005, 0.01, 0.002],
            [0.01, 0.002, 0.025],
        ])
        engine = MonteCarloRiskEngine(weights, mu, cov)
        result = engine.simulate(T=1, n_steps=10, n_paths=50, seed=42)
        assert isinstance(result, dict)
        assert 'portfolio_paths' in result
        assert result['portfolio_paths'].shape == (50, 11)

    def test_risk_report(self):
        from quant_engine import MonteCarloRiskEngine
        np.random.seed(42)
        N = 3
        weights = np.array([0.4, 0.3, 0.3])
        mu = np.array([0.08, 0.03, 0.06])
        cov = np.array([
            [0.04, 0.005, 0.01],
            [0.005, 0.01, 0.002],
            [0.01, 0.002, 0.025],
        ])
        engine = MonteCarloRiskEngine(weights, mu, cov)
        result = engine.risk_report(confidence=0.95, n_paths=500, seed=42)
        assert isinstance(result, dict)
        assert 'parametric' in result
        assert 'monte_carlo' in result

    def test_var_historical(self):
        from quant_engine.monte_carlo_risk import var_historical
        np.random.seed(42)
        returns = np.random.randn(500) * 0.02
        result = var_historical(returns, 0.95)
        assert isinstance(result, float)

    def test_cvar_historical(self):
        from quant_engine.monte_carlo_risk import cvar_historical
        np.random.seed(42)
        returns = np.random.randn(500) * 0.02
        result = cvar_historical(returns, 0.95)
        assert isinstance(result, float)

    def test_optimize_min_variance(self):
        from quant_engine.monte_carlo_risk import optimize_min_variance
        np.random.seed(42)
        cov = np.array([
            [0.04, 0.005, 0.01],
            [0.005, 0.01, 0.002],
            [0.01, 0.002, 0.025],
        ])
        result = optimize_min_variance(cov)
        assert isinstance(result, dict)
        assert 'weights' in result
        assert isinstance(result['weights'], np.ndarray)
