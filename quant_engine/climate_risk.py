r"""
climate_risk.py — Climate Financial Risk Models
===================================================
Provides models for assessing climate-related financial risks:

* **ClimateVaR**        — Physical + transition risk, combined VaR, TCFD reporting
* **HotellingRule**      — Optimal extraction pricing for depletable resources
* **InnovationSCurve**   — Bass diffusion S-curve & chasm analysis

Dependencies: numpy, scipy.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    from scipy import interpolate as sp_interp
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class ClimateVaR:
    """
    Models climate-related financial risk encompassing physical risk,
    transition risk, and combined assessment aligned with TCFD.
    """

    def physical_risk(
        self,
        asset_values: np.ndarray,
        temperature_scenarios: np.ndarray,
        damage_function: str = "nordhaus",
    ) -> Dict[str, np.ndarray]:
        """
        Estimate value-at-risk under climate physical risk.

        Physical risk arises from acute events (floods, storms) and
        chronic shifts (sea-level rise, heat stress).

        Parameters
        ----------
        asset_values : ndarray of shape (N,)
            Current market value of N assets.
        temperature_scenarios : ndarray of shape (S,)
            Temperature increase scenarios (in °C above pre-industrial).
        damage_function : str
            Damage function type: 'nordhaus' or 'howard'.

        Returns
        -------
        dict with keys:
            'losses'       : ndarray of shape (S, N), expected loss per scenario per asset
            'var_95'       : ndarray of shape (N,), 95th percentile VaR per asset
            'var_99'       : ndarray of shape (N,), 99th percentile VaR per asset
            'expected_loss': ndarray of shape (N,), mean loss across scenarios
        """
        asset_values = np.asarray(asset_values, dtype=float)
        temp = np.asarray(temperature_scenarios, dtype=float)
        N = len(asset_values)
        S = len(temp)

        losses = np.zeros((S, N))

        for s, T in enumerate(temp):
            # Damage fraction depends on temperature increase
            if damage_function == "nordhaus":
                # Nordhaus (2017): D(T) = a1*T + a2*T^2
                damage_frac = 0.00236 * T + 0.00027 * T ** 2
            elif damage_function == "howard":
                # Howard & Sterner (2017): more aggressive
                damage_frac = 0.012 * T + 0.003 * T ** 2
            else:
                damage_frac = 0.005 * T + 0.001 * T ** 2

            # Add asset-specific vulnerability (random for demonstration)
            # In practice, this would come from geospatial data
            rng = np.random.default_rng(seed=int(T * 100))
            vulnerability = 0.5 + rng.random(N)  # 0.5 to 1.5
            losses[s] = asset_values * damage_frac * vulnerability

        # Value-at-Risk at confidence levels
        var_95 = np.percentile(losses, 95, axis=0)
        var_99 = np.percentile(losses, 99, axis=0)
        expected_loss = np.mean(losses, axis=0)

        return {
            "losses": losses,
            "var_95": var_95,
            "var_99": var_99,
            "expected_loss": expected_loss,
        }

    def transition_risk(
        self,
        carbon_intensity: np.ndarray,
        carbon_price_path: np.ndarray,
        elasticity: float = -0.5,
    ) -> Dict[str, np.ndarray]:
        """
        Estimate asset devaluation under carbon pricing.

        Parameters
        ----------
        carbon_intensity : ndarray of shape (N,)
            Carbon intensity of each asset (tCO2e / $M revenue).
        carbon_price_path : ndarray of shape (T,)
            Projected carbon prices ($/tCO2e) over time.
        elasticity : float
            Price elasticity of value to carbon cost. Default -0.5.

        Returns
        -------
        dict with keys:
            'stranded_value' : ndarray of shape (T, N), value at risk per period
            'total_stranded' : ndarray of shape (N,), cumulative stranded value
            'transition_var95': float, 95th percentile of total stranded value
        """
        carbon_intensity = np.asarray(carbon_intensity, dtype=float)
        carbon_price_path = np.asarray(carbon_price_path, dtype=float)
        N = len(carbon_intensity)
        T = len(carbon_price_path)

        stranded = np.zeros((T, N))
        for t in range(T):
            # Carbon cost per unit
            carbon_cost = carbon_intensity * carbon_price_path[t]
            # Value impact (negative elasticity means higher carbon cost -> lower value)
            stranded[t] = np.abs(elasticity) * carbon_cost * 1e6  # scale

        total_stranded = np.sum(stranded, axis=0)
        transition_var95 = np.percentile(total_stranded, 95)

        return {
            "stranded_value": stranded,
            "total_stranded": total_stranded,
            "transition_var95": transition_var95,
        }

    def combined_climate_var(
        self,
        portfolio: Dict[str, float],
        temperature_path: np.ndarray,
        carbon_price_path: np.ndarray,
        time_horizon: int = 30,
    ) -> Dict[str, np.ndarray]:
        """
        Combined physical + transition risk for a portfolio.

        Parameters
        ----------
        portfolio : dict
            Mapping of asset_name -> value.
        temperature_path : ndarray of shape (T,)
            Temperature trajectory over time_horizon years.
        carbon_price_path : ndarray of shape (T,)
            Carbon price trajectory.
        time_horizon : int
            Investment horizon in years.

        Returns
        -------
        dict with keys:
            'total_climate_var95': float
            'physical_var95'     : float
            'transition_var95'   : float
            'by_asset'           : dict of per-asset risk decomposition
        """
        names = list(portfolio.keys())
        values = np.array([portfolio[n] for n in names], dtype=float)
        N = len(names)

        # Physical risk: use end-of-horizon temperature
        temp_end = temperature_path[-1] if len(temperature_path) > 0 else 2.0
        temp_scenarios = np.linspace(temp_end * 0.5, temp_end * 1.5, 100)
        phys = self.physical_risk(values, temp_scenarios)

        # Transition risk
        # Synthetic carbon intensity based on portfolio value
        rng = np.random.default_rng(42)
        carbon_int = 50 + rng.exponential(100, N)  # tCO2e / $M
        trans = self.transition_risk(carbon_int, carbon_price_path[:time_horizon])

        # Combine
        phys_per_asset = phys["expected_loss"]
        trans_per_asset = trans["total_stranded"]
        combined_per_asset = phys_per_asset + trans_per_asset

        return {
            "total_climate_var95": float(np.percentile(combined_per_asset, 95)),
            "physical_var95": float(np.percentile(phys_per_asset, 95)),
            "transition_var95": float(np.percentile(trans_per_asset, 95)),
            "by_asset": {name: float(combined_per_asset[i]) for i, name in enumerate(names)},
        }

    def tcfd_report(
        self,
        portfolio: Dict[str, float],
        scenarios: Dict[str, np.ndarray],
    ) -> Dict[str, object]:
        """
        Generate TCFD-aligned risk metrics.

        Parameters
        ----------
        portfolio : dict
            asset_name -> value.
        scenarios : dict
            scenario_name -> temperature_path (ndarray).

        Returns
        -------
        dict with TCFD-aligned metrics per scenario.
        """
        names = list(portfolio.keys())
        values = np.array([portfolio[n] for n in names], dtype=float)

        report: Dict[str, object] = {}
        for sc_name, temp_path in scenarios.items():
            temp_path = np.asarray(temp_path, dtype=float)
            # Physical risk at end of horizon
            temp_end = temp_path[-1] if len(temp_path) > 0 else 2.0
            temp_scenarios = np.linspace(temp_end * 0.5, temp_end * 1.5, 50)
            phys = self.physical_risk(values, temp_scenarios)

            # Carbon price (simple linear ramp)
            n_years = len(temp_path)
            carbon_price = np.linspace(50, 200, max(n_years, 2))

            rng = np.random.default_rng(42)
            carbon_int = 50 + rng.exponential(100, len(values))
            trans = self.transition_risk(carbon_int, carbon_price[:n_years])

            total_phys = float(phys["expected_loss"].sum())
            total_trans = float(trans["total_stranded"].sum())
            portfolio_value = float(values.sum())

            report[sc_name] = {
                "physical_risk_pct": total_phys / max(portfolio_value, 1e-10) * 100,
                "transition_risk_pct": total_trans / max(portfolio_value, 1e-10) * 100,
                "combined_risk_pct": (total_phys + total_trans) / max(portfolio_value, 1e-10) * 100,
                "physical_var95": float(phys["var_95"].sum()),
                "portfolio_exposure": portfolio_value,
            }

        return report


class HotellingRule:
    """
    Models optimal extraction pricing for depletable resources.

    The Hotelling rule states that the net price (price minus marginal
    extraction cost) of a non-renewable resource should grow at the
    rate of interest: d(P - C)/dt = r * (P - C).
    """

    def optimal_price_path(
        self,
        initial_price: float = 100.0,
        extraction_cost: float = 30.0,
        discount_rate: float = 0.05,
        reserves: float = 1000.0,
        periods: int = 50,
    ) -> Dict[str, np.ndarray]:
        """
        Compute the Hotelling optimal price path.

        Parameters
        ----------
        initial_price : float
            Current market price.
        extraction_cost : float
            Marginal extraction cost.
        discount_rate : float
            Social discount rate.
        reserves : float
            Total remaining reserves (arbitrary units).
        periods : int
            Number of periods.

        Returns
        -------
        dict with keys:
            'prices'     : ndarray of optimal prices per period
            'net_prices' : ndarray of net prices (price - cost)
            'extraction'  : ndarray of optimal extraction quantities
            'reserves_remaining': ndarray of reserves at each period
        """
        # Net price grows at the discount rate
        net_price_0 = initial_price - extraction_cost
        net_prices = net_price_0 * np.exp(discount_rate * np.arange(periods))
        prices = net_prices + extraction_cost

        # Optimal extraction: declining as price rises (demand curve)
        # Assume linear demand: Q = a - b*P, with a, b calibrated
        demand_intercept = reserves * 2  # enough to exhaust over periods
        demand_slope = demand_intercept / (prices.max() * 1.5)
        extraction = np.maximum(demand_intercept - demand_slope * prices, 0)

        # Reserves remaining
        reserves_remaining = np.zeros(periods)
        reserves_remaining[0] = reserves - extraction[0]
        for t in range(1, periods):
            reserves_remaining[t] = max(reserves_remaining[t - 1] - extraction[t], 0)

        return {
            "prices": prices,
            "net_prices": net_prices,
            "extraction": extraction,
            "reserves_remaining": reserves_remaining,
        }

    def optimal_extraction_rate(
        self,
        reserves: float = 1000.0,
        price_path: np.ndarray | None = None,
        demand_elasticity: float = -0.5,
        periods: int = 50,
    ) -> np.ndarray:
        """
        Compute optimal extraction schedule given demand elasticity.

        Parameters
        ----------
        reserves : float
            Total reserves.
        price_path : ndarray or None
            If provided, extraction is demand-determined.
        demand_elasticity : float
            Price elasticity of demand (negative).
        periods : int

        Returns
        -------
        ndarray of shape (periods,)
            Optimal extraction per period.
        """
        if price_path is None:
            # If no price path, assume smooth decline
            extraction = reserves / periods * np.linspace(1.5, 0.5, periods)
        else:
            price_path = np.asarray(price_path, dtype=float)
            # Higher prices -> lower extraction (demand curve)
            p_norm = price_path / max(price_path.max(), 1e-10)
            extraction = (1.0 - p_norm) ** np.abs(demand_elasticity)
            extraction = extraction / extraction.sum() * reserves

        return extraction


class InnovationSCurve:
    r"""
    Rogers S-curve adoption model (Bass diffusion model).

    The Bass model:
        dF/dt = (p + q*F) * (1 - F)

    where F is the cumulative adoption fraction, p is the innovation
    coefficient (external influence), q is the imitation coefficient
    (internal influence / word-of-mouth).
    """

    def adoption_curve(
        self,
        market_size: float = 1000.0,
        innovation_coefficient: float = 0.03,
        imitation_coefficient: float = 0.38,
        periods: int = 50,
    ) -> Dict[str, np.ndarray]:
        """
        Generate the Bass diffusion adoption curve.

        Parameters
        ----------
        market_size : float
            Total addressable market.
        innovation_coefficient : float
            p: coefficient of innovation (external influence).
        imitation_coefficient : float
            q: coefficient of imitation (internal influence).
        periods : int
            Number of time periods.

        Returns
        -------
        dict with keys:
            'cumulative_adopters' : ndarray, cumulative adopters per period
            'new_adopters'       : ndarray, new adopters per period
            'adoption_rate'      : ndarray, fraction of market adopted
            'peak_period'        : int, period of maximum new adoptions
            'peak_adopters'      : float, number of new adopters at peak
        """
        p = innovation_coefficient
        q = imitation_coefficient

        cumulative = np.zeros(periods)
        new_adopters = np.zeros(periods)
        cumulative[0] = market_size * p
        new_adopters[0] = cumulative[0]

        for t in range(1, periods):
            F_prev = cumulative[t - 1] / market_size
            # Bass formula: new adopters at t
            new = market_size * (p + q * F_prev) * (1.0 - F_prev)
            new_adopters[t] = max(new, 0)
            cumulative[t] = cumulative[t - 1] + new_adopters[t]

        adoption_rate = cumulative / market_size
        peak_period = int(np.argmax(new_adopters))
        peak_adopters = float(new_adopters[peak_period])

        return {
            "cumulative_adopters": cumulative,
            "new_adopters": new_adopters,
            "adoption_rate": adoption_rate,
            "peak_period": peak_period,
            "peak_adopters": peak_adopters,
        }

    def chasm_analysis(
        self,
        adopter_fractions: np.ndarray,
    ) -> Dict[str, object]:
        """
        Detect the "chasm" between early adopters and early majority
        (Moore's chasm in technology adoption).

        The chasm is identified as the period of slowest adoption growth
        between the early adopter and early majority phases.

        Parameters
        ----------
        adopter_fractions : ndarray of shape (T,)
            Cumulative adoption fraction at each period.

        Returns
        -------
        dict with keys:
            'chasm_detected'   : bool
            'chasm_period'     : int or None, period index of deepest chasm
            'chasm_width'      : int, number of periods in the chasm
            'growth_rate'      : ndarray, period-over-period growth rate
            'min_growth_rate'  : float, minimum growth rate (the chasm)
        """
        adopter_fractions = np.asarray(adopter_fractions, dtype=float)
        T = len(adopter_fractions)

        if T < 2:
            return {
                "chasm_detected": False,
                "chasm_period": None,
                "chasm_width": 0,
                "growth_rate": np.array([0.0]),
                "min_growth_rate": 0.0,
            }

        # Growth rate of adoption
        growth_rate = np.diff(adopter_fractions)
        growth_rate = np.concatenate([[0.0], growth_rate])

        # Chasm: look for the deepest trough in growth rate after initial ramp
        # in the early part of the adoption curve (before 50% adoption)
        early_phase = adopter_fractions < 0.50

        if not np.any(early_phase):
            return {
                "chasm_detected": False,
                "chasm_period": None,
                "chasm_width": 0,
                "growth_rate": growth_rate,
                "min_growth_rate": float(growth_rate.min()),
            }

        # Find the minimum growth rate in the early phase
        early_growth = growth_rate.copy()
        early_growth[~early_phase] = np.inf

        min_growth = float(early_growth.min())

        # Chasm is significant if there's a dip below median growth
        median_growth = float(np.median(growth_rate[early_phase]))

        if min_growth < median_growth * 0.5:
            chasm_detected = True
            chasm_period = int(np.argmin(early_growth))

            # Find width: contiguous period where growth < 0.7 * median
            threshold = median_growth * 0.7
            below = growth_rate < threshold
            # Find the cluster containing chasm_period
            chasm_width = 0
            for i in range(max(0, chasm_period - 20), min(T, chasm_period + 20)):
                if below[i]:
                    chasm_width += 1
        else:
            chasm_detected = False
            chasm_period = None
            chasm_width = 0

        return {
            "chasm_detected": chasm_detected,
            "chasm_period": chasm_period,
            "chasm_width": chasm_width,
            "growth_rate": growth_rate,
            "min_growth_rate": min_growth,
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("climate_risk.py — Demo")
    print("=" * 60)

    # --- ClimateVaR ---
    print("\n--- ClimateVaR ---")
    cv = ClimateVaR()

    assets = np.array([1e9, 5e8, 2e9, 8e8, 1.5e9])  # 5 assets
    temp_scenarios = np.linspace(1.5, 4.5, 50)

    phys = cv.physical_risk(assets, temp_scenarios, damage_function="nordhaus")
    print(f"  Physical risk (5 assets, 50 temp scenarios):")
    print(f"    Expected losses: {phys['expected_loss']}")
    print(f"    VaR 95%: {phys['var_95']}")
    print(f"    VaR 99%: {phys['var_99']}")

    carbon_int = np.array([120, 80, 200, 50, 150])
    carbon_prices = np.linspace(50, 300, 30)
    trans = cv.transition_risk(carbon_int, carbon_prices)
    print(f"  Transition risk:")
    print(f"    Total stranded value: {trans['total_stranded']}")
    print(f"    Transition VaR 95%: {trans['transition_var95']:.2f}")

    # TCFD Report
    portfolio = {"Oil Corp": 2e9, "Tech Green": 1.5e9, "Solar Co": 5e8, "Utility": 1e9}
    scenarios = {
        "1.5C": np.linspace(1.0, 1.5, 30),
        "2.5C": np.linspace(1.0, 2.5, 30),
        "4.0C": np.linspace(1.0, 4.0, 30),
    }
    report = cv.tcfd_report(portfolio, scenarios)
    for sc_name, metrics in report.items():
        print(f"  Scenario {sc_name}: combined risk = {metrics['combined_risk_pct']:.2f}%")

    # --- Hotelling Rule ---
    print("\n--- Hotelling Rule ---")
    hr = HotellingRule()
    hot = hr.optimal_price_path(initial_price=100, extraction_cost=30,
                                  discount_rate=0.05, reserves=1000, periods=50)
    print(f"  Price range: [{hot['prices'][0]:.2f}, {hot['prices'][-1]:.2f}]")
    print(f"  Net price growth rate: {(hot['net_prices'][-1]/hot['net_prices'][0] - 1)*100:.1f}%")
    print(f"  Reserves at end: {hot['reserves_remaining'][-1]:.1f}")

    # --- Innovation S-Curve ---
    print("\n--- Innovation S-Curve (Bass Diffusion) ---")
    isc = InnovationSCurve()
    bass = isc.adoption_curve(market_size=1000, innovation_coefficient=0.03,
                                imitation_coefficient=0.38, periods=50)
    print(f"  Peak adoption period: {bass['peak_period']}")
    print(f"  Peak new adopters: {bass['peak_adopters']:.1f}")
    print(f"  Final adoption: {bass['adoption_rate'][-1]:.1%}")

    chasm = isc.chasm_analysis(bass["adoption_rate"])
    print(f"  Chasm detected: {chasm['chasm_detected']}")
    if chasm['chasm_detected']:
        print(f"  Chasm period: {chasm['chasm_period']}, width: {chasm['chasm_width']}")

    print("\n[DONE]")
