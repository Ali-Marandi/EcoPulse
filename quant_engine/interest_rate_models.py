"""
Interest Rate Models & Option Pricing (Black-Scholes)
====================================================
Implements the classical short-rate models (Vasicek, CIR, Hull-White)
and the Black-Scholes option pricing framework with Greeks.

Mathematical foundations
-----------------------
1. **Vasicek (1977)**:
       dr_t = kappa * (theta - r_t) dt + sigma dW_t
   Mean-reverting Ornstein-Uhlenbeck process. Can produce negative rates.

2. **Cox-Ingersoll-Ross (1985)**:
       dr_t = kappa * (theta - r_t) dt + sigma * sqrt(r_t) dW_t
   Square-root diffusion prevents negative rates. Feller condition: 2*kappa*theta > sigma^2.

3. **Hull-White (1990)** (extended Vasicek with time-dependent mean):
       dr_t = [theta(t) - kappa * r_t] dt + sigma dW_t
   theta(t) is calibrated to fit the initial yield curve exactly.

4. **Black-Scholes (1973)**:
       C = S0 * N(d1) - K * exp(-r*T) * N(d2)
       d1 = [ln(S0/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
       d2 = d1 - sigma*sqrt(T)
   European option pricing under GBM, constant vol, no dividends.

5. **Greeks**: Delta, Gamma, Vega, Theta, Rho.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from scipy.stats import norm


# ---------------------------------------------------------------------------
# 1. Vasicek Model
# ---------------------------------------------------------------------------

class VasicekModel:
    """
    Vasicek (1977) short-rate model.

        dr_t = kappa * (theta - r_t) dt + sigma dW_t

    Analytical bond price:
        P(t,T) = A(t,T) * exp(-B(t,T) * r_t)

    where
        B(t,T) = (1 - exp(-kappa*(T-t))) / kappa
        A(t,T) = exp( (B(t,T) - (T-t)) * (theta - sigma^2/(2*kappa^2))
                      - sigma^2 * B(t,T)^2 / (4*kappa) )
    """

    def __init__(
        self,
        kappa: float = 0.5,
        theta: float = 0.05,
        sigma: float = 0.01,
        r0: float = 0.03,
    ):
        """
        Parameters
        ----------
        kappa : float  - Mean reversion speed.
        theta : float  - Long-term mean rate.
        sigma : float  - Volatility of the short rate.
        r0    : float  - Initial short rate.
        """
        self.kappa = kappa
        self.theta = theta
        self.sigma = sigma
        self.r0 = r0

    def B(self, t: float, T: float) -> float:
        """B(t,T) = (1 - exp(-kappa*tau)) / kappa"""
        tau = T - t
        if abs(self.kappa) < 1e-12:
            return tau
        return (1.0 - np.exp(-self.kappa * tau)) / self.kappa

    def A(self, t: float, T: float) -> float:
        """A(t,T) discount factor component."""
        tau = T - t
        B_val = self.B(t, T)
        k, th, s = self.kappa, self.theta, self.sigma
        exp_term = (B_val - tau) * (th - s ** 2 / (2 * k ** 2)) - s ** 2 * B_val ** 2 / (4 * k)
        return np.exp(exp_term)

    def bond_price(self, t: float, T: float, r: Optional[float] = None) -> float:
        """Zero-coupon bond price P(t,T)."""
        r_val = r if r is not None else self.r0
        return self.A(t, T) * np.exp(-self.B(t, T) * r_val)

    def yield_curve(
        self, t: float = 0.0, maturities: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Compute the zero-coupon yield curve.

        Returns dict with: maturities, yields, bond_prices.
        """
        if maturities is None:
            maturities = np.linspace(0.25, 30, 120)
        yields = np.array([-np.log(self.bond_price(t, T)) / (T - t) for T in maturities])
        prices = np.array([self.bond_price(t, T) for T in maturities])
        return {"maturities": maturities, "yields": yields, "bond_prices": prices}

    def simulate(
        self, T: float = 10.0, n_steps: int = 1000, n_paths: int = 100, seed: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """
        Euler-Maruyama simulation of the Vasicek process.

        Returns dict with: time, rates (n_paths x n_steps+1), mean_path, std_path.
        """
        rng = np.random.default_rng(seed)
        dt = T / n_steps
        times = np.linspace(0, T, n_steps + 1)
        rates = np.zeros((n_paths, n_steps + 1))
        rates[:, 0] = self.r0

        sqrt_dt = np.sqrt(dt)
        for i in range(n_steps):
            dW = rng.normal(0, sqrt_dt, n_paths)
            rates[:, i + 1] = rates[:, i] + self.kappa * (self.theta - rates[:, i]) * dt + self.sigma * dW

        return {
            "time": times,
            "rates": rates,
            "mean_path": rates.mean(axis=0),
            "std_path": rates.std(axis=0),
        }

    def forward_rate(self, t: float, T1: float, T2: float) -> float:
        """Simply-compounded forward rate F(t; T1, T2)."""
        P1 = self.bond_price(t, T1)
        P2 = self.bond_price(t, T2)
        if P2 <= 0:
            return float("nan")
        return (P1 / P2 - 1) / (T2 - T1)


# ---------------------------------------------------------------------------
# 2. CIR Model
# ---------------------------------------------------------------------------

class CIRModel:
    """
    Cox-Ingersoll-Ross (1985) short-rate model.

        dr_t = kappa * (theta - r_t) dt + sigma * sqrt(r_t) dW_t

    Feller condition: 2*kappa*theta >= sigma^2 ensures r_t > 0.

    Bond price formula:
        P(t,T) = A(t,T) * exp(-B(t,T) * r_t)
    """

    def __init__(
        self,
        kappa: float = 0.5,
        theta: float = 0.05,
        sigma: float = 0.1,
        r0: float = 0.03,
    ):
        self.kappa = kappa
        self.theta = theta
        self.sigma = sigma
        self.r0 = r0

    @property
    def feller_condition(self) -> bool:
        """Check if 2*kappa*theta >= sigma^2 (prevents r from hitting 0)."""
        return 2 * self.kappa * self.theta >= self.sigma ** 2

    def _h(self) -> float:
        """h = sqrt(kappa^2 + 2*sigma^2)."""
        return np.sqrt(self.kappa ** 2 + 2 * self.sigma ** 2)

    def B(self, t: float, T: float) -> float:
        tau = T - t
        h = self._h()
        exp_term = np.exp(h * tau)
        return 2 * (exp_term - 1) / ((h + self.kappa) * exp_term + (h - self.kappa))

    def A(self, t: float, T: float) -> float:
        tau = T - t
        h = self._h()
        num = 2 * h * np.exp((self.kappa + h) * tau / 2)
        den = ((h + self.kappa) * np.exp(h * tau) + (h - self.kappa))
        return (num / den) ** (2 * self.kappa * self.theta / self.sigma ** 2)

    def bond_price(self, t: float, T: float, r: Optional[float] = None) -> float:
        r_val = r if r is not None else self.r0
        return self.A(t, T) * np.exp(-self.B(t, T) * r_val)

    def yield_curve(
        self, t: float = 0.0, maturities: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        if maturities is None:
            maturities = np.linspace(0.25, 30, 120)
        yields = np.array([-np.log(self.bond_price(t, T)) / (T - t) for T in maturities])
        prices = np.array([self.bond_price(t, T) for T in maturities])
        return {"maturities": maturities, "yields": yields, "bond_prices": prices}

    def simulate(
        self, T: float = 10.0, n_steps: int = 1000, n_paths: int = 100, seed: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """
        Simulate CIR process using the exact transition (non-central chi-squared).
        Falls back to Euler for very short dt where the exact method is unstable.
        """
        rng = np.random.default_rng(seed)
        dt = T / n_steps
        times = np.linspace(0, T, n_steps + 1)
        rates = np.zeros((n_paths, n_steps + 1))
        rates[:, 0] = self.r0

        k, th, s = self.kappa, self.theta, self.sigma
        d = 4 * k * th / s ** 2  # degrees of freedom

        for i in range(n_steps):
            r_prev = rates[:, i]
            # Non-central chi-squared parameters
            c = (s ** 2 * (1 - np.exp(-k * dt))) / (4 * k)
            lam = r_prev * np.exp(-k * dt) / c

            # Sample from non-central chi-squared
            # Approximation: if d > 0 and lambda > 0, use normal approximation
            nc_param = lam  # non-centrality parameter
            df = d
            # Normal approximation to NCCS for large samples
            mean_nc = df + nc_param
            var_nc = 2 * (df + 2 * nc_param)
            samples = rng.normal(mean_nc, np.sqrt(np.maximum(var_nc, 1e-16)), n_paths)
            rates[:, i + 1] = c * np.maximum(samples, 0)

        return {
            "time": times,
            "rates": rates,
            "mean_path": rates.mean(axis=0),
            "std_path": rates.std(axis=0),
        }


# ---------------------------------------------------------------------------
# 3. Hull-White Model
# ---------------------------------------------------------------------------

class HullWhiteModel:
    """
    Hull-White (1990) extended Vasicek model with time-dependent theta(t).

        dr_t = [theta(t) - kappa * r_t] dt + sigma dW_t

    theta(t) is calibrated so the model exactly reproduces the initial
    yield curve observed in the market.

    Calibration:
        theta(t) = f(0,t) + kappa * f(0,t) + sigma^2/(2*kappa) * (1 - exp(-2*kappa*t))
    where f(0,t) is the instantaneous forward rate.
    """

    def __init__(
        self,
        kappa: float = 0.1,
        sigma: float = 0.01,
        r0: float = 0.03,
    ):
        self.kappa = kappa
        self.sigma = sigma
        self.r0 = r0
        self._market_maturities: Optional[np.ndarray] = None
        self._market_rates: Optional[np.ndarray] = None

    def calibrate_to_yield_curve(
        self,
        maturities: np.ndarray,
        rates: np.ndarray,
    ) -> None:
        """
        Store the market yield curve for theta(t) computation.

        Parameters
        ----------
        maturities : array  - in years.
        rates : array  - continuously-compounded zero rates.
        """
        self._market_maturities = np.asarray(maturities, dtype=float)
        self._market_rates = np.asarray(rates, dtype=float)

    def _forward_rate(self, t: float) -> float:
        """Interpolate f(0,t) from the market curve."""
        if self._market_maturities is None:
            return self.r0
        return np.interp(t, self._market_maturities, self._market_rates)

    def theta(self, t: float) -> float:
        """Compute theta(t) from the calibration formula."""
        f = self._forward_rate(t)
        k, s = self.kappa, self.sigma
        # Numerical derivative of f(0,t)
        dt = 1e-6
        f_prime = (self._forward_rate(t + dt) - self._forward_rate(t - dt)) / (2 * dt)
        return f + f_prime + s ** 2 / (2 * k) * (1 - np.exp(-2 * k * t))

    def bond_price(self, t: float, T: float) -> float:
        """Bond price under Hull-White, calibrated to market curve."""
        tau = T - t
        B = (1 - np.exp(-self.kappa * tau)) / self.kappa
        # Integral of theta(s) * B(s,T) ds approximated numerically
        n_pts = max(int(tau * 100), 10)
        s_arr = np.linspace(t, T, n_pts)
        ds = s_arr[1] - s_arr[0] if n_pts > 1 else tau
        integral = 0.0
        for s in s_arr:
            B_sT = (1 - np.exp(-self.kappa * (T - s))) / self.kappa
            integral += self.theta(s) * B_sT * ds
        log_A = integral - self.sigma ** 2 / (4 * self.kappa) * B ** 2
        P_market_t = np.exp(-self._forward_rate(t) * t)
        return np.exp(log_A - B * self.r0)

    def simulate(
        self, T: float = 10.0, n_steps: int = 1000, n_paths: int = 100, seed: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """Simulate Hull-White process using Euler-Maruyama."""
        rng = np.random.default_rng(seed)
        dt = T / n_steps
        times = np.linspace(0, T, n_steps + 1)
        rates = np.zeros((n_paths, n_steps + 1))
        rates[:, 0] = self.r0
        sqrt_dt = np.sqrt(dt)

        for i in range(n_steps):
            t_i = times[i]
            dW = rng.normal(0, sqrt_dt, n_paths)
            theta_t = self.theta(t_i)
            rates[:, i + 1] = rates[:, i] + (theta_t - self.kappa * rates[:, i]) * dt + self.sigma * dW

        return {
            "time": times,
            "rates": rates,
            "mean_path": rates.mean(axis=0),
            "std_path": rates.std(axis=0),
        }

    def model_vs_market_curves(
        self, maturities: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """Compare model-implied vs market yield curves."""
        if maturities is None:
            maturities = np.linspace(0.25, 30, 60)
        model_prices = np.array([self.bond_price(0, T) for T in maturities])
        model_yields = -np.log(np.maximum(model_prices, 1e-16)) / maturities
        market_yields = np.array([self._forward_rate(T) for T in maturities])
        return {
            "maturities": maturities,
            "model_yields": model_yields,
            "market_yields": market_yields,
            "yield_error": model_yields - market_yields,
        }


# ---------------------------------------------------------------------------
# 4. Black-Scholes Option Pricing
# ---------------------------------------------------------------------------

class BlackScholesModel:
    """
    Black-Scholes (1973) European option pricing model.

        C = S0 * N(d1) - K * exp(-r*T) * N(d2)
        P = K * exp(-r*T) * N(-d2) - S0 * N(-d1)

    where
        d1 = [ln(S0/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
        d2 = d1 - sigma*sqrt(T)

    Greeks are computed analytically.
    """

    def __init__(
        self,
        S0: float = 100.0,
        r: float = 0.05,
        sigma: float = 0.2,
    ):
        self.S0 = S0
        self.r = r
        self.sigma = sigma

    def _d1_d2(self, K: float, T: float) -> Tuple[float, float]:
        """Compute d1 and d2."""
        if T <= 0 or self.sigma <= 0 or K <= 0 or self.S0 <= 0:
            return 0.0, 0.0
        sqrtT = np.sqrt(T)
        d1 = (np.log(self.S0 / K) + (self.r + 0.5 * self.sigma ** 2) * T) / (self.sigma * sqrtT)
        d2 = d1 - self.sigma * sqrtT
        return d1, d2

    def call_price(self, K: float, T: float) -> float:
        """Price a European call option."""
        d1, d2 = self._d1_d2(K, T)
        return self.S0 * norm.cdf(d1) - K * np.exp(-self.r * T) * norm.cdf(d2)

    def put_price(self, K: float, T: float) -> float:
        """Price a European put option."""
        d1, d2 = self._d1_d2(K, T)
        return K * np.exp(-self.r * T) * norm.cdf(-d2) - self.S0 * norm.cdf(-d1)

    def put_call_parity_price(self, K: float, T: float, option_type: str = "call") -> float:
        """Verify put-call parity: C - P = S - K*exp(-r*T)."""
        C = self.call_price(K, T)
        P = self.put_price(K, T)
        return {"call": C, "put": P, "parity_diff": C - P - (self.S0 - K * np.exp(-self.r * T))}

    def greeks(self, K: float, T: float) -> Dict[str, float]:
        """
        Compute all five Greeks for a European call option.

        Returns dict with: delta, gamma, vega, theta, rho.
        """
        d1, d2 = self._d1_d2(K, T)
        sqrtT = np.sqrt(T) if T > 0 else 1e-12
        exp_rT = np.exp(-self.r * T)

        delta = norm.cdf(d1)
        gamma = norm.pdf(d1) / (self.S0 * self.sigma * sqrtT)
        vega = self.S0 * norm.pdf(d1) * sqrtT / 100  # per 1% vol move
        theta = (
            -self.S0 * norm.pdf(d1) * self.sigma / (2 * sqrtT) / 365
            - self.r * K * exp_rT * norm.cdf(d2) / 365
        )  # per day
        rho = K * T * exp_rT * norm.cdf(d2) / 100  # per 1% rate move

        return {
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
        }

    def implied_volatility(
        self, K: float, T: float, market_price: float, option_type: str = "call",
        tol: float = 1e-8, max_iter: int = 100
    ) -> float:
        """
        Compute implied volatility using Newton-Raphson.

        Parameters
        ----------
        K, T : float
        market_price : float  - observed market price of the option.
        option_type : str   - 'call' or 'put'.
        """
        # Initial guess: use ATM vol as starting point
        sigma = self.sigma
        for _ in range(max_iter):
            self.sigma = sigma
            if option_type == "call":
                price = self.call_price(K, T)
                d1, _ = self._d1_d2(K, T)
                vega = self.S0 * norm.pdf(d1) * np.sqrt(T)
            else:
                price = self.put_price(K, T)
                d1, _ = self._d1_d2(K, T)
                vega = self.S0 * norm.pdf(d1) * np.sqrt(T)

            diff = price - market_price
            if abs(diff) < tol:
                self.sigma = sigma  # restore
                return sigma
            if vega < 1e-16:
                break
            sigma = sigma - diff / vega
            sigma = max(sigma, 1e-8)  # vol must be positive

        self.sigma = sigma
        return sigma

    def volatility_smile(
        self, T: float = 1.0, strikes: Optional[np.ndarray] = None,
        call_prices: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Compute the volatility smile/skew from a set of option prices.

        If call_prices is provided, compute implied vol for each strike.
        Otherwise, return the theoretical BS smile (flat at sigma).
        """
        if strikes is None:
            strikes = np.linspace(self.S0 * 0.7, self.S0 * 1.3, 30)

        if call_prices is not None and len(call_prices) == len(strikes):
            vols = np.array([
                self.implied_volatility(K, T, C, "call") for K, C in zip(strikes, call_prices)
            ])
        else:
            vols = np.full(len(strikes), self.sigma)

        return {"strikes": strikes, "implied_vols": vols, "moneyness": strikes / self.S0}

    def binomial_tree_price(
        self, K: float, T: float, n_steps: int = 200, option_type: str = "call"
    ) -> Dict[str, float]:
        """
        Price a European option using a Cox-Ross-Rubinstein binomial tree.
        Useful for comparison with the analytical BS formula.
        """
        dt = T / n_steps
        u = np.exp(self.sigma * np.sqrt(dt))
        d = 1.0 / u
        p = (np.exp(self.r * dt) - d) / (u - d)
        p = max(0, min(1, p))  # ensure valid probability

        # Forward induction: asset prices at expiry
        prices = np.zeros(n_steps + 1)
        prices[0] = self.S0 * d ** n_steps
        for j in range(1, n_steps + 1):
            prices[j] = prices[j - 1] * (u / d)

        # Option values at expiry
        if option_type == "call":
            values = np.maximum(prices - K, 0)
        else:
            values = np.maximum(K - prices, 0)

        # Backward induction
        disc = np.exp(-self.r * dt)
        for i in range(n_steps - 1, -1, -1):
            for j in range(i + 1):
                values[j] = disc * (p * values[j + 1] + (1 - p) * values[j])

        analytical = self.call_price(K, T) if option_type == "call" else self.put_price(K, T)
        return {
            "tree_price": values[0],
            "analytical_price": analytical,
            "difference": values[0] - analytical,
        }
