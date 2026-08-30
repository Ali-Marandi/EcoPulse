"""
Capital Structure Models
=========================
Implements the key theories of corporate capital structure:

1. **Modigliani-Miller** (1958, 1963) - irrelevance proposition, with and
   without taxes, with bankruptcy costs (trade-off theory).

2. **WACC** - Weighted Average Cost of Capital calculation.

3. **Trade-Off Theory** - optimal capital structure balances tax shield
   benefits against bankruptcy costs.

4. **Pecking Order Theory** (Myers & Majluf, 1984) - financing hierarchy:
   retained earnings > debt > equity.

Mathematical foundations
-----------------------
MM without taxes:  V_L = V_U
MM with taxes:    V_L = V_U + T_c * D
  (tax shield of debt)

MM with bankruptcy costs (trade-off):
  V_L = V_U + T_c * D - PV(expected bankruptcy costs)

WACC:  WACC = (E/V) * r_e + (D/V) * r_d * (1 - T_c)

Levered equity return (MM Prop II):
  r_e = r_a + (D/E) * (r_a - r_d)

Trade-off optimal D*:  maximise V_L = V_U + T_c*D - C(D)
  FOC:  T_c = C'(D*)
"""
from __future__ import annotations

import numpy as np
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# 1. Modigliani-Miller Framework
# ---------------------------------------------------------------------------

class ModiglianiMiller:
    """
    Modigliani-Miller capital structure theorems.
    
    Proposition I (no taxes):    V_L = V_U
    Proposition I (with taxes):  V_L = V_U + T_c * D
    Proposition II:              r_e = r_a + (D/E)(r_a - r_d)
    """

    def __init__(
        self,
        EBIT: float = 100,
        r_a: float = 0.10,  # unlevered cost of capital
        r_d: float = 0.06,  # cost of debt
        T_c: float = 0.25,  # corporate tax rate
        V_unlevered: Optional[float] = None,
    ):
        self.EBIT = EBIT
        self.r_a = r_a
        self.r_d = r_d
        self.T_c = T_c
        self.V_U = V_unlevered if V_unlevered is not None else EBIT / r_a

    def prop1_no_tax(self, D: float) -> Dict:
        """MM Proposition I without taxes: V_L = V_U regardless of D."""
        E = self.V_U - D
        r_e = self.r_a + (D / E) * (self.r_a - self.r_d) if E > 0 else float("inf")
        WACC = (E / self.V_U) * r_e + (D / self.V_U) * self.r_d if self.V_U > 0 else 0
        return {
            "V_levered": self.V_U,
            "V_unlevered": self.V_U,
            "equity_value": E,
            "debt_value": D,
            "cost_of_equity": r_e,
            "WACC": WACC,
            "tax_benefit": 0,
        }

    def prop1_with_tax(self, D: float) -> Dict:
        """MM Proposition I with corporate taxes: V_L = V_U + T_c * D."""
        tax_shield = self.T_c * D
        V_L = self.V_U + tax_shield
        E = V_L - D
        r_e = self.r_a + (D / E) * (self.r_a - self.r_d) * (1 - self.T_c) if E > 0 else float("inf")
        WACC = (E / V_L) * r_e + (D / V_L) * self.r_d * (1 - self.T_c) if V_L > 0 else 0
        return {
            "V_levered": V_L,
            "V_unlevered": self.V_U,
            "equity_value": E,
            "debt_value": D,
            "cost_of_equity": r_e,
            "WACC": WACC,
            "tax_shield_value": tax_shield,
        }

    def leverage_sweep(self, max_D: Optional[float] = None, n_points: int = 50) -> Dict:
        """
        Sweep debt levels and compute firm value under MM with taxes.
        
        Returns arrays for plotting.
        """
        if max_D is None:
            max_D = self.V_U * 0.9
        D_arr = np.linspace(0, max_D, n_points)
        V_L = np.array([self.prop1_with_tax(d)["V_levered"] for d in D_arr])
        r_e_arr = np.array([self.prop1_with_tax(d)["cost_of_equity"] for d in D_arr])
        wacc_arr = np.array([self.prop1_with_tax(d)["WACC"] for d in D_arr])
        tax_shield = self.T_c * D_arr
        
        return {
            "debt": D_arr,
            "V_levered": V_L,
            "cost_of_equity": r_e_arr,
            "WACC": wacc_arr,
            "tax_shield": tax_shield,
            "leverage_ratio": D_arr / V_L,
        }


# ---------------------------------------------------------------------------
# 2. WACC Calculator
# ---------------------------------------------------------------------------

class WACCCalculator:
    """
    Weighted Average Cost of Capital calculator with multiple debt tranches
    and cost of equity models (CAPM, growth model, or direct input).
    """

    def __init__(
        self,
        equity_value: float = 1000,
        debt_tranches: Optional[list] = None,
        cost_of_equity: float = 0.12,
        tax_rate: float = 0.25,
        risk_free: float = 0.04,
        market_return: float = 0.10,
        beta: float = 1.2,
    ):
        self.E = equity_value
        self.debt_tranches = debt_tranches or [{"value": 400, "cost": 0.06}]
        self.r_e = cost_of_equity
        self.T_c = tax_rate
        self.rf = risk_free
        self.rm = market_return
        self.beta = beta

    @property
    def total_debt(self) -> float:
        return sum(t["value"] for t in self.debt_tranches)

    @property
    def V(self) -> float:
        return self.E + self.total_debt

    def cost_of_equity_capm(self) -> float:
        """CAPM: r_e = r_f + beta * (r_m - r_f)."""
        return self.rf + self.beta * (self.rm - self.rf)

    def weighted_cost_of_debt(self) -> float:
        """Weighted average cost of debt across tranches."""
        D = self.total_debt
        if D == 0:
            return 0
        return sum(t["value"] * t["cost"] for t in self.debt_tranches) / D

    def compute_wacc(self, use_capm: bool = False) -> Dict:
        """
        Compute WACC.
        
        WACC = (E/V) * r_e + (D/V) * r_d * (1 - T_c)
        """
        r_e = self.cost_of_equity_capm() if use_capm else self.r_e
        r_d = self.weighted_cost_of_debt()
        D = self.total_debt
        V = self.V

        if V <= 0:
            return {"WACC": 0, "r_e": 0, "r_d": 0}

        wacc = (self.E / V) * r_e + (D / V) * r_d * (1 - self.T_c)

        return {
            "WACC": wacc,
            "cost_of_equity": r_e,
            "weighted_cost_of_debt": r_d,
            "after_tax_cost_of_debt": r_d * (1 - self.T_c),
            "equity_weight": self.E / V,
            "debt_weight": D / V,
            "total_firm_value": V,
        }


# ---------------------------------------------------------------------------
# 3. Trade-Off Theory
# ---------------------------------------------------------------------------

class TradeOffTheory:
    """
    Trade-off theory of capital structure.
    
    Optimal D* maximises:  V(D) = V_U + T_c * D - C(D)
    
    where C(D) = expected bankruptcy costs, modelled as:
    C(D) = alpha * exp(beta * D / V_U)
    
    FOC:  T_c = C'(D*)  =>  T_c = alpha * beta / V_U * exp(beta * D*/V_U)
    
    Solving:  D* = (V_U / beta) * ln(T_c * V_U / (alpha * beta))
    """

    def __init__(
        self,
        V_unlevered: float = 1000,
        T_c: float = 0.25,
        bankruptcy_alpha: float = 50,
        bankruptcy_beta: float = 3.0,
    ):
        self.V_U = V_unlevered
        self.T_c = T_c
        self.alpha = bankruptcy_alpha  # scale of bankruptcy costs
        self.beta = bankruptcy_beta    # sensitivity to leverage

    def bankruptcy_cost(self, D: float) -> float:
        """Expected bankruptcy cost as a function of debt."""
        return self.alpha * np.exp(self.beta * D / self.V_U)

    def firm_value(self, D: float) -> float:
        """V(D) = V_U + T_c * D - C(D)."""
        return self.V_U + self.T_c * D - self.bankruptcy_cost(D)

    def optimal_debt(self) -> Dict:
        """
        Find the optimal debt level that maximises firm value.
        
        Analytical solution: D* = (V_U/beta) * ln(T_c*V_U / (alpha*beta))
        """
        # Analytical
        arg = self.T_c * self.V_U / (self.alpha * self.beta)
        if arg <= 0:
            D_star = 0
        else:
            D_star = (self.V_U / self.beta) * np.log(arg)
        D_star = max(D_star, 0)

        V_opt = self.firm_value(D_star)
        tax_benefit = self.T_c * D_star
        bank_cost = self.bankruptcy_cost(D_star)

        # Also do numerical check
        D_range = np.linspace(0, self.V_U * 0.95, 500)
        V_range = np.array([self.firm_value(d) for d in D_range])
        D_numerical = D_range[np.argmax(V_range)]
        V_numerical = V_range.max()

        return {
            "optimal_debt_analytical": D_star,
            "optimal_debt_numerical": D_numerical,
            "firm_value_optimal": V_opt,
            "tax_benefit": tax_benefit,
            "bankruptcy_cost": bank_cost,
            "max_firm_value": V_numerical,
            "leverage_ratio": D_star / V_opt if V_opt > 0 else 0,
        }

    def frontier_curve(self, n_points: int = 200) -> Dict:
        """
        Generate the trade-off frontier for plotting.
        
        Returns debt levels, firm values, tax benefits, and bankruptcy costs.
        """
        D_arr = np.linspace(0, self.V_U * 0.95, n_points)
        V_arr = np.array([self.firm_value(d) for d in D_arr])
        tax_arr = self.T_c * D_arr
        bank_arr = np.array([self.bankruptcy_cost(d) for d in D_arr])

        return {
            "debt": D_arr,
            "firm_value": V_arr,
            "tax_benefit": tax_arr,
            "bankruptcy_cost": bank_arr,
            "net_benefit": V_arr - self.V_U,
        }


# ---------------------------------------------------------------------------
# 4. Pecking Order Theory
# ---------------------------------------------------------------------------

class PeckingOrderModel:
    """
    Pecking Order Theory (Myers & Majluf, 1984).
    
    Financing hierarchy due to asymmetric information:
    1. Internal financing (retained earnings)
    2. Debt issuance
    3. Equity issuance (last resort, signals overvaluation)
    
    The model simulates the cumulative financing deficit and the
    resulting capital structure evolution.
    """

    def __init__(
        self,
        initial_equity: float = 1000,
        initial_debt: float = 300,
        retained_earnings_rate: float = 0.05,  # % of equity retained
        investment_needs: float = 200,  # annual investment requirement
        debt_capacity_ratio: float = 0.6,  # max D/V ratio
        cost_of_debt: float = 0.06,
        equity_issuance_cost: float = 0.15,  # flotation + signalling cost
    ):
        self.E0 = initial_equity
        self.D0 = initial_debt
        self.re_rate = retained_earnings_rate
        self.inv_need = investment_needs
        self.debt_cap = debt_capacity_ratio
        self.r_d = cost_of_debt
        self.eq_cost = equity_issuance_cost

    def simulate(
        self, n_years: int = 20, growth_rate: float = 0.03
    ) -> Dict:
        """
        Simulate capital structure evolution under pecking order.
        
        Each year:
        1. Generate retained earnings
        2. Fund investment needs (internal -> debt -> equity)
        3. Track capital structure
        
        Returns time series of equity, debt, D/V ratio, and financing sources.
        """
        E = self.E0
        D = self.D0

        equity_history = [E]
        debt_history = [D]
        dv_history = [D / (E + D)]
        retained_history = [0]
        debt_issued_history = [0]
        equity_issued_history = [0]

        for year in range(n_years):
            retained = E * self.re_rate
            deficit = self.inv_need * (1 + growth_rate) ** year - retained

            new_debt = 0
            new_equity = 0

            if deficit > 0:
                # Step 1: use retained earnings (already subtracted)
                # Step 2: issue debt up to capacity
                V = E + D + retained
                max_D = self.debt_cap * V
                debt_room = max(max_D - D, 0)
                new_debt = min(deficit, debt_room)
                remaining = deficit - new_debt

                # Step 3: issue equity as last resort
                if remaining > 0:
                    new_equity = remaining / (1 - self.eq_cost)

            E = E + retained + new_equity
            D = D + new_debt

            equity_history.append(E)
            debt_history.append(D)
            dv_history.append(D / (E + D) if (E + D) > 0 else 0)
            retained_history.append(retained)
            debt_issued_history.append(new_debt)
            equity_issued_history.append(new_equity)

        years = np.arange(n_years + 1)
        return {
            "years": years,
            "equity": np.array(equity_history),
            "debt": np.array(debt_history),
            "debt_to_value": np.array(dv_history),
            "retained_earnings": np.array(retained_history),
            "new_debt_issued": np.array(debt_issued_history),
            "new_equity_issued": np.array(equity_issued_history),
        }
