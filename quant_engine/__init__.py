"""
EcoPulse Quantitative Engine
==========================
A comprehensive suite of advanced quantitative finance modules for the
EcoPulse economic intelligence workstation.

Modules (21 total)
-------
Core Quantitative
- black_litterman       : Black-Litterman Bayesian portfolio allocation.
- garch_model           : GARCH(1,1) volatility with VaR / CVaR.
- pca_factors           : PCA factor extraction, yield-curve decomposition.
- monte_carlo_risk      : Monte Carlo simulation, VaR/CVaR, stress testing.
- time_series_advanced  : ARIMA/SARIMA, VAR, Granger, Johansen, CUSUM.

Macro & Political
- macro_models          : Taylor rule, Phillips curve, DSGE, Minsky, Kondratiev.
- political_risk        : ICRG scoring, sanctions, game theory, elections.
- epidemiological_economics : SIR model with economic transmission channels.

Risk & Anomaly
- contagion_network     : Financial contagion, DebtRank, community detection.
- anomaly_detection     : Price manipulation, Beneish M-Score, Altman Z-Score.
- climate_risk          : Climate VaR, Hotelling rule, innovation S-curves.

Behavioural & Fuzzy
- behavioral_finance    : Prospect theory, disposition, herding, overconfidence.
- fuzzy_credit          : Mamdani fuzzy inference for credit scoring.
- fuzzy_advanced        : ANFIS, Fuzzy AHP, Fuzzy TOPSIS, fuzzy portfolio, fuzzy BS.

Market Microstructure & Pricing
- market_microstructure : Market making, Glosten-Milgrom, auctions,
                          Akerlof lemons, Spence signalling, Stiglitz screening.
- interest_rate_models  : Vasicek, CIR, Hull-White, Black-Scholes with Greeks.
- capital_structure     : Modigliani-Miller, WACC, trade-off, pecking order.

Causal & Regulatory
- causal_inference      : DAGs, do-calculus, Double ML, IV/2SLS, DID, PSM.
- regulatory_framework  : Basel III ratios, MiFID II, Dodd-Frank compliance.
- market_efficiency     : EMH tests (Runs, Variance Ratio, Ljung-Box, Event Study).
"""

from __future__ import annotations

# --- Core Quantitative ---
from .black_litterman import BlackLittermanModel, BlView
from .garch_model import GARCH11
from .pca_factors import PCAFactorExtractor
from .fuzzy_credit import FuzzyCreditScorer
from .transfer_entropy import transfer_entropy, network_analysis, shannon_entropy
from .time_series_advanced import (
    fit_arima,
    fit_sarima,
    fit_var,
    granger_causality_test,
    johansen_cointegration_test,
    cusum_change_detection,
)
from .monte_carlo_risk import MonteCarloRiskEngine

# --- Macro & Political ---
from .macro_models import TaylorRule, PhillipsCurve, DSGESimple, MinskyCycle, KondratievWave
from .political_risk import PoliticalRiskScore, SanctionImpactModel, GeopoliticalGameModel, ElectionCycleModel
from .epidemiological_economics import SIRModel, EconomicImpactSIR

# --- Risk & Anomaly ---
from .contagion_network import FinancialNetwork, CorrelationNetwork, DebtRank
from .anomaly_detection import PriceManipulationDetector, AccountingFraudDetector
from .climate_risk import ClimateVaR, HotellingRule, InnovationSCurve

# --- Behavioural & Fuzzy ---
from .behavioral_finance import ProspectTheory, DispositionEffect, HerdingModel, OverconfidenceBias
from .fuzzy_advanced import (
    TFN,
    FuzzyAHP,
    FuzzyTOPSIS,
    FuzzyPortfolioOptimizer,
    FuzzyBlackScholes,
    SimplifiedANFIS,
)

# --- Market Microstructure & Pricing ---
from .market_microstructure import (
    MarketMakerModel,
    GlostenMilgromSpread,
    AuctionMechanism,
    AkerlofLemonsModel,
    SpenceSignallingModel,
    RothschildStiglitzScreening,
    MechanismDesignAnalyzer,
)
from .interest_rate_models import (
    VasicekModel,
    CIRModel,
    HullWhiteModel,
    BlackScholesModel,
)
from .capital_structure import (
    ModiglianiMiller,
    WACCCalculator,
    TradeOffTheory,
    PeckingOrderModel,
)

# --- Causal & Regulatory ---
from .causal_inference import (
    CausalDAG,
    DoubleML,
    InstrumentalVariables,
    DifferenceInDifferences,
    PropensityScoreMatching,
)
from .regulatory_framework import (
    BaselIIICapital,
    BaselIIICompliance,
    MiFIDIIAnalyzer,
    DoddFrankAnalyzer,
)
from .market_efficiency import (
    WeakFormEMHTests,
    EventStudy,
)

__all__ = [
    # Core Quantitative
    "BlackLittermanModel", "BlView",
    "GARCH11",
    "PCAFactorExtractor",
    "FuzzyCreditScorer",
    "transfer_entropy", "network_analysis", "shannon_entropy",
    "fit_arima", "fit_sarima", "fit_var",
    "granger_causality_test", "johansen_cointegration_test", "cusum_change_detection",
    "MonteCarloRiskEngine",
    # Macro & Political
    "TaylorRule", "PhillipsCurve", "DSGESimple", "MinskyCycle", "KondratievWave",
    "PoliticalRiskScore", "SanctionImpactModel", "GeopoliticalGameModel", "ElectionCycleModel",
    "SIRModel", "EconomicImpactSIR",
    # Risk & Anomaly
    "FinancialNetwork", "CorrelationNetwork", "DebtRank",
    "PriceManipulationDetector", "AccountingFraudDetector",
    "ClimateVaR", "HotellingRule", "InnovationSCurve",
    # Behavioural & Fuzzy
    "ProspectTheory", "DispositionEffect", "HerdingModel", "OverconfidenceBias",
    "TFN", "FuzzyAHP", "FuzzyTOPSIS", "FuzzyPortfolioOptimizer", "FuzzyBlackScholes", "SimplifiedANFIS",
    # Market Microstructure & Pricing
    "MarketMakerModel", "GlostenMilgromSpread", "AuctionMechanism",
    "AkerlofLemonsModel", "SpenceSignallingModel", "RothschildStiglitzScreening", "MechanismDesignAnalyzer",
    "VasicekModel", "CIRModel", "HullWhiteModel", "BlackScholesModel",
    "ModiglianiMiller", "WACCCalculator", "TradeOffTheory", "PeckingOrderModel",
    # Causal & Regulatory
    "CausalDAG", "DoubleML", "InstrumentalVariables", "DifferenceInDifferences", "PropensityScoreMatching",
    "BaselIIICapital", "BaselIIICompliance", "MiFIDIIAnalyzer", "DoddFrankAnalyzer",
    "WeakFormEMHTests", "EventStudy",
]
