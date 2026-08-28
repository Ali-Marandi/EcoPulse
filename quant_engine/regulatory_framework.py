"""
Regulatory Framework Models: Basel III, MiFID II, Dodd-Frank
===========================================================
Implements quantitative metrics and compliance checks for the three major
post-2008 financial regulatory frameworks.

1. **Basel III** capital adequacy, leverage ratio, liquidity coverage (LCR),
   net stable funding (NSFR), and capital buffers.

2. **MiFID II** best execution analysis, transaction cost measurement,
   and suitability scoring.

3. **Dodd-Frank** stress testing, Volcker Rule compliance,
   and derivatives clearing metrics.

Mathematical foundations
-----------------------
Basel III CET1 ratio = CET1 / RWA >= 4.5% (plus buffers >= 7.0% total)
Leverage ratio    = Tier 1 Capital / Total Exposure >= 3%
LCR              = HQLA / Net Cash Outflows >= 100%
NSFR             = ASF / RSF >= 100%
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. Basel III Capital Adequacy
# ---------------------------------------------------------------------------

@dataclass
class BaselIIICapital:
    """Represents a bank's capital structure for Basel III calculations."""
    common_equity_tier1: float = 0.0
    additional_tier1: float = 0.0
    tier2: float = 0.0
    total_assets: float = 0.0
    risk_weighted_assets: float = 0.0
    total_exposure: float = 0.0
    hqla: float = 0.0
    net_cash_outflows_30d: float = 0.0
    available_stable_funding: float = 0.0
    required_stable_funding: float = 0.0

    @property
    def tier1_capital(self) -> float:
        return self.common_equity_tier1 + self.additional_tier1

    @property
    def total_capital(self) -> float:
        return self.tier1_capital + self.tier2


class BaselIIICompliance:
    """
    Basel III regulatory compliance calculator.

    Computes all key ratios and checks against minimum requirements
    including capital conservation buffer (2.5%), countercyclical buffer
    (0-2.5%), and G-SIB surcharge (0-3.5%).
    """

    CET1_MIN = 0.045
    TIER1_MIN = 0.060
    TOTAL_MIN = 0.080
    LEVERAGE_MIN = 0.030
    LCR_MIN = 1.0
    NSFR_MIN = 1.0

    def __init__(
        self,
        capital_conservation_buffer: float = 0.025,
        countercyclical_buffer: float = 0.0,
        gsib_surcharge: float = 0.0,
        dsrb_surcharge: float = 0.0,
    ):
        self.ccb = capital_conservation_buffer
        self.ccyb = countercyclical_buffer
        self.gsib = gsib_surcharge
        self.dsrb = dsrb_surcharge

    @property
    def total_buffer_requirement(self) -> float:
        return self.ccb + self.ccyb + self.gsib + self.dsrb

    def compute_ratios(self, cap: BaselIIICapital) -> Dict[str, float]:
        rwa = cap.risk_weighted_assets
        total_exp = cap.total_exposure
        cet1_ratio = cap.common_equity_tier1 / rwa if rwa > 0 else 0
        tier1_ratio = cap.tier1_capital / rwa if rwa > 0 else 0
        total_ratio = cap.total_capital / rwa if rwa > 0 else 0
        leverage = cap.tier1_capital / total_exp if total_exp > 0 else 0
        lcr = cap.hqla / cap.net_cash_outflows_30d if cap.net_cash_outflows_30d > 0 else float("inf")
        nsfr = cap.available_stable_funding / cap.required_stable_funding if cap.required_stable_funding > 0 else float("inf")
        return {
            "cet1_ratio": cet1_ratio, "tier1_ratio": tier1_ratio,
            "total_ratio": total_ratio, "leverage_ratio": leverage,
            "lcr": lcr, "nsfr": nsfr,
        }

    def compliance_check(self, cap: BaselIIICapital) -> Dict:
        ratios = self.compute_ratios(cap)
        buf = self.total_buffer_requirement
        cet1_req = self.CET1_MIN + buf
        tier1_req = self.TIER1_MIN + buf
        total_req = self.TOTAL_MIN + buf

        deficits = {}
        compliant = True
        for name, ratio, req in [
            ("cet1", ratios["cet1_ratio"], cet1_req),
            ("tier1", ratios["tier1_ratio"], tier1_req),
            ("total", ratios["total_ratio"], total_req),
            ("leverage", ratios["leverage_ratio"], self.LEVERAGE_MIN),
            ("lcr", ratios["lcr"], self.LCR_MIN),
            ("nsfr", ratios["nsfr"], self.NSFR_MIN),
        ]:
            deficit = req - ratio
            deficits[f"{name}_deficit"] = max(deficit, 0)
            if deficit > 0:
                compliant = False

        cet1_ratio = ratios["cet1_ratio"]
        if cet1_ratio < self.CET1_MIN + self.ccb:
            max_payout = 0
        elif cet1_ratio < self.CET1_MIN + self.ccb + 0.00625:
            max_payout = 0.2
        elif cet1_ratio < self.CET1_MIN + self.ccb + 0.0125:
            max_payout = 0.4
        else:
            max_payout = 0.6

        return {
            "ratios": ratios,
            "requirements": {
                "cet1_min": cet1_req, "tier1_min": tier1_req,
                "total_min": total_req, "leverage_min": self.LEVERAGE_MIN,
                "lcr_min": self.LCR_MIN, "nsfr_min": self.NSFR_MIN,
            },
            "compliant": compliant, "deficits": deficits,
            "max_payout_ratio": max_payout,
            "buffer_breakdown": {
                "conservation_buffer": self.ccb,
                "countercyclical_buffer": self.ccyb,
                "gsib_surcharge": self.gsib,
                "dsrb_surcharge": self.dsrb,
                "total_buffer": buf,
            },
        }

    @staticmethod
    def stress_test(
        cap: BaselIIICapital,
        rwa_shock: float = 0.15,
        hqla_shock: float = 0.20,
        outflow_shock: float = 0.30,
    ) -> Dict:
        stressed = BaselIIICapital(
            common_equity_tier1=cap.common_equity_tier1 * (1 - rwa_shock * 0.3),
            additional_tier1=cap.additional_tier1, tier2=cap.tier2,
            total_assets=cap.total_assets,
            risk_weighted_assets=cap.risk_weighted_assets * (1 + rwa_shock),
            total_exposure=cap.total_exposure,
            hqla=cap.hqla * (1 - hqla_shock),
            net_cash_outflows_30d=cap.net_cash_outflows_30d * (1 + outflow_shock),
            available_stable_funding=cap.available_stable_funding * (1 - hqla_shock * 0.5),
            required_stable_funding=cap.required_stable_funding * (1 + rwa_shock * 0.3),
        )
        checker = BaselIIICompliance()
        baseline = checker.compute_ratios(cap)
        stressed_r = checker.compute_ratios(stressed)
        return {
            "baseline": baseline, "stressed": stressed_r,
            "cet1_impact": stressed_r["cet1_ratio"] - baseline["cet1_ratio"],
            "lcr_impact": stressed_r["lcr"] - baseline["lcr"],
            "nsfr_impact": stressed_r["nsfr"] - baseline["nsfr"],
        }


# ---------------------------------------------------------------------------
# 2. MiFID II Compliance
# ---------------------------------------------------------------------------

class MiFIDIIAnalyzer:
    """
    MiFID II compliance analysis for investment firms.

    Key requirements: Best Execution (Art.44), Transaction Reporting (Art.26),
    Product Governance (Art.16), Suitability (Art.25), Cost Disclosure.
    """

    def __init__(self, venue_list: Optional[List[str]] = None):
        self.venues = venue_list or ["XEON", "XPAR", "XLON", "XETR"]

    def best_execution_analysis(self, venue_executions: Dict[str, Dict[str, float]]) -> Dict:
        """
        Analyze execution quality across venues for best execution compliance.

        Parameters
        ----------
        venue_executions : dict
            {venue: {"avg_price_deviation", "avg_fill_rate", "avg_speed_ms", "n_trades", "total_volume"}}

        Returns dict with venue_rankings, best_venue, scores.
        """
        scores = {}
        for venue, stats in venue_executions.items():
            price_score = max(0, 1 - stats.get("avg_price_deviation", 0))
            fill_score = stats.get("avg_fill_rate", 0)
            speed = stats.get("avg_speed_ms", 100)
            speed_score = max(0, 1 - speed / 1000)
            composite = 0.4 * price_score + 0.3 * fill_score + 0.3 * speed_score
            scores[venue] = {
                "composite_score": composite, "price_score": price_score,
                "fill_score": fill_score, "speed_score": speed_score,
                "n_trades": stats.get("n_trades", 0),
                "total_volume": stats.get("total_volume", 0),
            }
        ranked = sorted(scores.items(), key=lambda x: x[1]["composite_score"], reverse=True)
        return {
            "venue_rankings": ranked,
            "best_venue": ranked[0][0] if ranked else None,
            "scores": scores,
        }

    def total_cost_analysis(self, trades: List[Dict[str, float]]) -> Dict:
        """
        Ex-post cost analysis per MiFID II cost disclosure.
        Each trade dict: {notional, commission, exchange_fees, clearing_fees, market_impact}.
        """
        total_cost = 0.0
        total_notional = 0.0
        breakdown = {"commission": 0, "fees": 0, "market_impact": 0, "other": 0}

        for t in trades:
            notional = t.get("notional", 0)
            total_notional += notional
            comm = t.get("commission", 0)
            fees = t.get("exchange_fees", 0) + t.get("clearing_fees", 0) + t.get("settlement_fees", 0)
            impact = t.get("market_impact", 0)
            other = t.get("other_costs", 0)
            trade_cost = comm + fees + impact + other
            total_cost += trade_cost
            breakdown["commission"] += comm
            breakdown["fees"] += fees
            breakdown["market_impact"] += impact
            breakdown["other"] += other

        total_bps = (total_cost / total_notional * 10000) if total_notional > 0 else 0
        pct = {k: v / total_cost * 100 if total_cost > 0 else 0 for k, v in breakdown.items()}

        return {
            "total_cost_bps": total_bps,
            "total_cost": total_cost,
            "total_notional": total_notional,
            "cost_breakdown_bps": {k: v / total_notional * 10000 if total_notional > 0 else 0 for k, v in breakdown.items()},
            "cost_percentage": pct,
            "n_trades": len(trades),
        }

    def suitability_score(
        self,
        client_risk_profile: float,
        product_risk_score: float,
        client_experience: int,
        product_complexity: int,
        knowledge_match: float = 0.5,
    ) -> Dict:
        """
        Compute suitability score for MiFID II Art. 25 compliance.

        Parameters
        ----------
        client_risk_profile : float  - 0 (conservative) to 1 (aggressive).
        product_risk_score : float  - 0 (safe) to 1 (risky).
        client_experience : int    - Years of investment experience.
        product_complexity : int  - 1 (simple) to 5 (very complex).
        knowledge_match : float  - 0 to 1, how well client knowledge matches product.

        Returns dict with: suitability_score (0-100), suitable (bool), reasons.
        """
        risk_alignment = 1 - abs(client_risk_profile - product_risk_score)
        experience_ok = min(client_experience / 5.0, 1.0)
        complexity_ok = 1 - (product_complexity - 1) / 4.0

        score = (
            0.35 * risk_alignment +
            0.25 * experience_ok +
            0.20 * complexity_ok +
            0.20 * knowledge_match
        ) * 100

        reasons = []
        if risk_alignment < 0.5:
            reasons.append("Risk mismatch between client profile and product")
        if experience_ok < 0.5:
            reasons.append("Insufficient experience for product complexity")
        if complexity_ok < 0.4:
            reasons.append("Product too complex for client")
        if knowledge_match < 0.3:
            reasons.append("Knowledge gap identified")

        return {
            "suitability_score": round(score, 2),
            "suitable": score >= 50,
            "risk_alignment": risk_alignment,
            "reasons": reasons,
        }


# ---------------------------------------------------------------------------
# 3. Dodd-Frank Compliance
# ---------------------------------------------------------------------------

class DoddFrankAnalyzer:
    """
    Dodd-Frank Act compliance analyzer.

    Covers: stress testing (CCAR/DFAST), Volcker Rule,
    derivatives clearing mandate, and swap dealer metrics.
    """

    def __init__(self):
        pass

    def volcker_rule_check(
        self,
        trading_revenue: float,
        total_revenue: float,
        proprietary_positions: Dict[str, float],
        allowed_activities_revenue: float = 0.0,
    ) -> Dict:
        """
        Check Volcker Rule compliance.

        The Volcker Rule generally prohibits proprietary trading by banks.
        Key metric: trading revenue as % of total revenue.

        Parameters
        ----------
        trading_revenue : float  - Revenue from trading activities.
        total_revenue : float  - Total firm revenue.
        proprietary_positions : dict  - {asset: notional_value} for prop positions.
        allowed_activities_revenue : float  - Revenue from permitted activities.
        """
        trading_pct = trading_revenue / total_revenue * 100 if total_revenue > 0 else 0
        total_prop_notional = sum(proprietary_positions.values())

        # Heuristic: if trading revenue > 10% of total, flag for review
        flag_threshold = 10.0
        needs_review = trading_pct > flag_threshold

        return {
            "trading_revenue_pct": trading_pct,
            "total_proprietary_notional": total_prop_notional,
            "flag_threshold_pct": flag_threshold,
            "needs_review": needs_review,
            "allowed_activities_revenue": allowed_activities_revenue,
            "prop_positions": proprietary_positions,
        }

    def stress_scenario(
        self,
        portfolio_value: float,
        shocks: Dict[str, float],
        correlations: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Apply stress scenario shocks to a portfolio.

        Parameters
        ----------
        portfolio_value : float
        shocks : dict  - {"equity": -0.20, "rates": +0.02, "credit_spread": +0.03}
        correlations : dict  - Pairwise correlations between risk factors.

        Returns dict with: stressed_value, loss, loss_pct, factor_impacts.
        """
        total_loss = 0
        factor_impacts = {}

        for factor, shock in shocks.items():
            # Assume equal allocation across factors for simplicity
            allocation = portfolio_value / len(shocks)
            impact = allocation * shock
            total_loss += impact
            factor_impacts[factor] = {
                "shock": shock,
                "allocated_value": allocation,
                "impact": impact,
            }

        stressed_value = portfolio_value + total_loss

        return {
            "original_value": portfolio_value,
            "stressed_value": stressed_value,
            "total_loss": total_loss,
            "loss_pct": total_loss / portfolio_value if portfolio_value > 0 else 0,
            "factor_impacts": factor_impacts,
            "capital_adequate": stressed_value > 0,
        }

    def derivative_clearing_check(
        self,
        otc_notional: float,
        cleared_notional: float,
        threshold_notional: float = 8e9,
    ) -> Dict:
        """
        Check compliance with the derivatives clearing mandate.

        Dodd-Frank requires certain standardized swaps to be cleared through
        a CCP. The threshold applies to the aggregate notional of swap positions.

        Parameters
        ----------
        otc_notional : float  - Total uncleared OTC derivative notional.
        cleared_notional : float  - Total cleared through CCP.
        threshold_notional : float  - Clearing mandate threshold.
        """
        total = otc_notional + cleared_notional
        clearing_pct = cleared_notional / total * 100 if total > 0 else 0
        above_threshold = total > threshold_notional
        needs_clearing = above_threshold and clearing_pct < 100

        return {
            "total_notional": total,
            "cleared_notional": cleared_notional,
            "otc_notional": otc_notional,
            "clearing_percentage": clearing_pct,
            "above_threshold": above_threshold,
            "needs_mandatory_clearing": needs_clearing,
            "threshold_notional": threshold_notional,
        }
