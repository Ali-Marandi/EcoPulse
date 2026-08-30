"""
Epidemiological-Economic Models (SIR)
=========================================
Implements the SIR epidemiological model and its integration with
economic impact assessment.

Mathematical foundations
-----------------------
SIR Model (Kermack-McKendrick, 1927):
    dS/dt = -beta * S * I / N
    dI/dt = beta * S * I / N - gamma * I
    dR/dt = gamma * I

R0 = beta / gamma  (basic reproduction number)

Economic transmission channels:
1. Labour supply reduction:  delta_L = -theta_I * I/N * L
2. Consumption drop:  delta_C = -theta_C * I/N * C
3. Supply chain disruption:  delta_S = -theta_S * (I/N)^alpha
4. Fiscal stimulus offset:  delta_G = +G_stimulus(t)
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 1. SIR Model
# ---------------------------------------------------------------------------

class SIRModel:
    """
    Classical SIR epidemiological model with economic impact channels.
    
    Parameters
    ----------
    N : int        - Total population.
    I0 : int       - Initial infected.
    R0 : float     - Basic reproduction number (beta/gamma).
    gamma : float  - Recovery rate (1/days_infectious).
    """

    def __init__(
        self,
        N: int = 10_000_000,
        I0: int = 100,
        R0: float = 2.5,
        gamma: float = 1.0 / 14,  # 14-day infectious period
    ):
        self.N = N
        self.I0 = I0
        self.R0 = R0
        self.gamma = gamma
        self.beta = R0 * gamma

    def simulate(
        self,
        T: float = 365,
        n_steps: int = 1000,
        vaccination_rate: float = 0.0,
    ) -> Dict[str, np.ndarray]:
        """
        Simulate the SIR model using RK4 integration.
        
        Returns dict with: time, S, I, R, new_cases, R_effective.
        """
        dt = T / n_steps
        times = np.linspace(0, T, n_steps + 1)
        S = np.zeros(n_steps + 1)
        I = np.zeros(n_steps + 1)
        R = np.zeros(n_steps + 1)
        new_cases = np.zeros(n_steps + 1)
        R_eff = np.zeros(n_steps + 1)

        S[0] = self.N - self.I0
        I[0] = self.I0
        R[0] = 0

        N = self.N
        beta = self.beta
        gamma = self.gamma

        for i in range(n_steps):
            s, inf, r = S[i], I[i], R[i]
            vac = vaccination_rate * s * dt

            # RK4
            def deriv(s_, i_, r_):
                new_inf = beta * s_ * i_ / N
                rec = gamma * i_
                return -new_inf - vac, new_inf - rec, rec

            k1s, k1i, k1r = deriv(s, inf, r)
            k2s, k2i, k2r = deriv(s + 0.5*dt*k1s, inf + 0.5*dt*k1i, r + 0.5*dt*k1r)
            k3s, k3i, k3r = deriv(s + 0.5*dt*k2s, inf + 0.5*dt*k2i, r + 0.5*dt*k2r)
            k4s, k4i, k4r = deriv(s + dt*k3s, inf + dt*k3i, r + dt*k3r)

            S[i+1] = max(s + dt/6 * (k1s + 2*k2s + 2*k3s + k4s), 0)
            I[i+1] = max(inf + dt/6 * (k1i + 2*k2i + 2*k3i + k4i), 0)
            R[i+1] = r + dt/6 * (k1r + 2*k2r + 2*k3r + k4r)

            new_cases[i+1] = max(beta * S[i] * I[i] / N * dt, 0)
            R_eff[i] = beta * S[i] / (N * gamma)

        R_eff[-1] = beta * S[-1] / (N * gamma)

        return {
            "time": times,
            "S": S, "I": I, "R": R,
            "new_cases": new_cases,
            "R_effective": R_eff,
            "peak_infected": I.max(),
            "peak_day": times[np.argmax(I)],
            "total_ever_infected": R[-1] + I[-1],
            "attack_rate": (R[-1] + I[-1]) / N,
        }


# ---------------------------------------------------------------------------
# 2. Economic Impact Assessment
# ---------------------------------------------------------------------------

class EconomicImpactSIR:
    """
    Links SIR epidemiological dynamics to economic output.
    
    The key idea: the fraction of the population infected (I/N) and
    recovered (R/N) affect labour supply, consumption, and supply chains.
    """

    def __init__(
        self,
        labour_elasticity: float = 0.7,    # How much GDP drops per 1% workforce loss
        consumption_elasticity: float = 0.5,
        supply_chain_factor: float = 0.3,
        fiscal_stimulus: float = 0.0,       # As % of annual GDP
        stimulus_duration_days: int = 180,
    ):
        self.theta_L = labour_elasticity
        self.theta_C = consumption_elasticity
        self.theta_S = supply_chain_factor
        self.fiscal_stim = fiscal_stimulus
        self.stim_duration = stimulus_duration_days

    def assess(
        self,
        sir_result: Dict[str, np.ndarray],
        annual_gdp: float = 1e12,
        baseline_growth: float = 0.03,
    ) -> Dict:
        """
        Compute economic impact from SIR simulation results.
        
        Parameters
        ----------
        sir_result : dict from SIRModel.simulate()
        annual_gdp : float  - Annual GDP in currency units.
        baseline_growth : float  - Expected annual growth rate without pandemic.
        
        Returns dict with: daily_gdp_impact, cumulative_loss, recovery_timeline.
        """
        I = sir_result["I"]
        R = sir_result["R"]
        S = sir_result["S"]
        times = sir_result["time"]
        N = S[0] + I[0] + R[0]
        n = len(times)

        daily_gdp = annual_gdp / 365
        infection_rate = I / N
        recovered_rate = R / N

        # Labour supply channel
        labour_impact = -self.theta_L * infection_rate

        # Consumption channel
        consumption_impact = -self.theta_C * (infection_rate + 0.3 * recovered_rate)

        # Supply chain channel (nonlinear)
        supply_impact = -self.theta_S * infection_rate ** 0.8

        # Fiscal stimulus
        fiscal = np.zeros(n)
        stim_mask = times <= self.stim_duration
        fiscal[stim_mask] = self.fiscal_stim * baseline_growth

        # Total daily GDP impact (fraction of normal daily GDP)
        total_impact = labour_impact + consumption_impact + supply_impact + fiscal
        total_impact = np.clip(total_impact, -0.5, 0.1)  # Cap at -50%

        daily_gdp_actual = daily_gdp * (1 + total_impact)
        baseline_daily_gdp = daily_gdp * (1 + baseline_growth / 365)
        daily_loss = daily_gdp_actual - baseline_daily_gdp
        cumulative_loss = np.cumsum(daily_loss)

        # Recovery timeline: when daily GDP returns to 95% of baseline
        recovery_idx = np.where(daily_gdp_actual >= 0.95 * baseline_daily_gdp)[0]
        recovery_day = times[recovery_idx[0]] if len(recovery_idx) > 0 else float("inf")

        return {
            "daily_gdp_impact_pct": total_impact * 100,
            "daily_gdp_actual": daily_gdp_actual,
            "daily_loss": daily_loss,
            "cumulative_loss": cumulative_loss,
            "total_loss_pct_gdp": cumulative_loss[-1] / annual_gdp * 100,
            "peak_daily_loss_pct": abs(daily_loss.min()) / daily_gdp * 100,
            "recovery_day": recovery_day,
            "recovery_days": recovery_day if np.isfinite(recovery_day) else n,
            "labour_channel": labour_impact,
            "consumption_channel": consumption_impact,
            "supply_chain_channel": supply_impact,
            "fiscal_channel": fiscal,
        }

    def scenario_comparison(
        self,
        scenarios: Dict[str, Dict],
        annual_gdp: float = 1e12,
    ) -> Dict:
        """
        Compare multiple epidemic scenarios.
        
        Parameters
        ----------
        scenarios : dict  - {name: {"R0": float, "gamma": float, "I0": int}}
        
        Returns dict with: summary table of all scenarios.
        """
        results = {}
        for name, params in scenarios.items():
            sir = SIRModel(
                R0=params.get("R0", 2.5),
                gamma=params.get("gamma", 1/14),
                I0=params.get("I0", 100),
            )
            sim = sir.simulate()
            impact = self.assess(sim, annual_gdp)
            results[name] = {
                "peak_infected_pct": sim["peak_infected"] / sir.N * 100,
                "attack_rate_pct": sim["attack_rate"] * 100,
                "total_gdp_loss_pct": impact["total_loss_pct_gdp"],
                "recovery_days": impact["recovery_days"],
                "peak_daily_loss_pct": impact["peak_daily_loss_pct"],
            }
        return results
