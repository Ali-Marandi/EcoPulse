r"""
GARCH(1,1) Volatility Modelling
================================

Implements the GARCH(1,1) model for conditional heteroskedasticity:

    σ²_t = ω + α · ε²_{t-1} + β · σ²_{t-1}

Fitted via maximum likelihood estimation (Gaussian likelihood) using
:func:`scipy.optimize.minimize`.  The module also provides:

- n-step-ahead volatility forecasting
- Conditional volatility series
- Value-at-Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall)

References
----------
Bollerslev, T. (1986). Generalized Autoregressive Conditional
    Heteroskedasticity. Journal of Econometrics, 31(3), 307-327.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


# Parameter lower bounds for numerical stability
_BOUNDS = [(1e-8, None), (0.0, 1.0 - 1e-8), (0.0, 1.0 - 1e-8)]  # ω, α, β


def _garch_log_likelihood(
    params: np.ndarray, returns: np.ndarray
) -> float:
    """Negative Gaussian log-likelihood for GARCH(1,1)."""
    omega, alpha, beta = params
    T = len(returns)
    sigma2 = np.empty(T)
    sigma2[0] = np.var(returns) if T > 1 else 1.0  # unconditional var init

    for t in range(1, T):
        sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
        if sigma2[t] <= 0 or not np.isfinite(sigma2[t]):
            return 1e15  # penalty

    # Gaussian log-likelihood
    ll = -0.5 * np.sum(
        np.log(2 * np.pi * sigma2) + returns ** 2 / sigma2
    )
    if not np.isfinite(ll):
        return 1e15
    return -ll  # minimise negative LL


class GARCH11:
    """GARCH(1,1) model with MLE fitting and risk metrics.

    Parameters
    ----------
    returns : array-like of shape (T,)
        Zero-mean (or demeaned) return series.
    """

    def __init__(self, returns: np.ndarray) -> None:
        r = np.asarray(returns, dtype=np.float64).ravel()
        if r.size < 10:
            raise ValueError(
                f"Need at least 10 observations, got {r.size}"
            )
        self.returns = r
        self.T = len(r)

        # Fitted parameters (filled by :meth:`fit`)
        self.omega: Optional[float] = None
        self.alpha: Optional[float] = None
        self.beta: Optional[float] = None
        self.conditional_sigma2: Optional[np.ndarray] = None
        self.log_likelihood: Optional[float] = None
        self.aic: Optional[float] = None
        self.bic: Optional[float] = None

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------
    def fit(
        self,
        x0: Optional[Tuple[float, float, float]] = None,
        method: str = "L-BFGS-B",
        maxiter: int = 2000,
    ) -> "GARCH11":
        """Fit the GARCH(1,1) model via MLE.

        Parameters
        ----------
        x0 : tuple of 3 floats or None
            Initial guess (ω, α, β).  If *None*, uses heuristic.
        method : str
            Optimiser passed to :func:`scipy.optimize.minimize`
            (default ``"L-BFGS-B"``).
        maxiter : int
            Maximum number of iterations.

        Returns
        -------
        self
        """
        var0 = float(np.var(self.returns))
        if var0 < 1e-12:
            var0 = 1e-4

        if x0 is None:
            x0 = (var0 * 0.05, 0.10, 0.80)

        result = minimize(
            _garch_log_likelihood,
            x0=np.array(x0, dtype=np.float64),
            args=(self.returns,),
            method=method,
            bounds=_BOUNDS,
            options={"maxiter": maxiter, "ftol": 1e-12},
        )

        if not result.success:
            # Try Nelder-Mead as a fallback (no bounds)
            result2 = minimize(
                _garch_log_likelihood,
                x0=np.array(x0, dtype=np.float64),
                args=(self.returns,),
                method="Nelder-Mead",
                options={"maxiter": maxiter, "xatol": 1e-10, "fatol": 1e-10},
            )
            if result2.fun < result.fun:
                result = result2

        self.omega, self.alpha, self.beta = result.x
        self.conditional_sigma2 = self._compute_conditional_variance()

        neg_ll = result.fun
        self.log_likelihood = -neg_ll
        k = 3  # number of parameters
        self.aic = 2 * k - 2 * self.log_likelihood
        self.bic = k * np.log(self.T) - 2 * self.log_likelihood

        return self

    def _compute_conditional_variance(self) -> np.ndarray:
        """Return the full conditional variance series σ²_t."""
        if self.omega is None:
            raise RuntimeError("Model has not been fitted yet.")
        T = self.T
        sigma2 = np.empty(T)
        sigma2[0] = float(np.var(self.returns))
        for t in range(1, T):
            sigma2[t] = (
                self.omega
                + self.alpha * self.returns[t - 1] ** 2
                + self.beta * sigma2[t - 1]
            )
            if sigma2[t] <= 0:
                sigma2[t] = 1e-12
        return sigma2

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------
    def forecast(self, n_steps: int = 1) -> np.ndarray:
        """n-step-ahead conditional variance forecast.

        For GARCH(1,1), the recursive forecast converges to the
        unconditional variance:

            σ²_{t+h} → ω / (1 - α - β)  as h → ∞

        Parameters
        ----------
        n_steps : int
            Number of steps ahead (≥ 1).

        Returns
        -------
        np.ndarray of shape (n_steps,)
            Forecasted conditional variances.
        """
        if self.omega is None:
            raise RuntimeError("Model has not been fitted yet.")
        if n_steps < 1:
            raise ValueError("n_steps must be ≥ 1")

        sigma2_last = self.conditional_sigma2[-1]
        eps2_last = self.returns[-1] ** 2

        forecasts = np.empty(n_steps)
        s2 = self.omega + self.alpha * eps2_last + self.beta * sigma2_last
        forecasts[0] = s2

        for h in range(1, n_steps):
            # As h increases the effect of last residual vanishes
            s2 = self.omega + (self.alpha + self.beta) * s2
            forecasts[h] = s2

        return forecasts

    # ------------------------------------------------------------------
    # Risk metrics
    # ------------------------------------------------------------------
    def var(
        self,
        confidence: float = 0.95,
        n_steps: int = 1,
        method: str = "parametric",
    ) -> float:
        """Compute Value-at-Risk.

        Parameters
        ----------
        confidence : float
            Confidence level in (0.5, 1).
        n_steps : int
            Forecast horizon (default 1).
        method : str
            ``"parametric"`` (Gaussian) or ``"historical"`` (empirical
            quantile of the standardised residuals).

        Returns
        -------
        float
            The VaR (a positive number representing the loss at the
            given confidence level).  Callers typically negate this to
            express it as a negative return threshold.
        """
        if self.omega is None:
            raise RuntimeError("Model has not been fitted yet.")

        sigma2_f = self.forecast(n_steps)
        sigma_f = np.sqrt(sigma2_f[-1])  # use last step's volatility

        alpha = 1.0 - confidence
        if method == "parametric":
            z = norm.ppf(alpha)
        elif method == "historical":
            std_resid = self.returns / np.sqrt(self.conditional_sigma2)
            z = float(np.percentile(std_resid, alpha * 100))
        else:
            raise ValueError(f"Unknown method: {method}")

        return abs(z * sigma_f)

    def cvar(
        self,
        confidence: float = 0.95,
        n_steps: int = 1,
        method: str = "parametric",
    ) -> float:
        """Compute Conditional Value-at-Risk (Expected Shortfall).

        For the Gaussian case the analytical formula is:

            CVaR_α = σ · φ(Φ^{-1}(α)) / α

        Parameters
        ----------
        confidence : float
            Confidence level in (0.5, 1).
        n_steps : int
            Forecast horizon.
        method : str
            ``"parametric"`` or ``"historical"``.

        Returns
        -------
        float
            The CVaR (positive number, loss magnitude).
        """
        if self.omega is None:
            raise RuntimeError("Model has not been fitted yet.")

        sigma2_f = self.forecast(n_steps)
        sigma_f = np.sqrt(sigma2_f[-1])
        alpha = 1.0 - confidence

        if method == "parametric":
            z = norm.ppf(alpha)
            cvar = sigma_f * (-norm.pdf(z) / alpha)
        elif method == "historical":
            std_resid = self.returns / np.sqrt(self.conditional_sigma2)
            cutoff = float(np.percentile(std_resid, alpha * 100))
            tail = std_resid[std_resid <= cutoff]
            cvar = sigma_f * abs(float(np.mean(tail)))
        else:
            raise ValueError(f"Unknown method: {method}")

        return cvar
    
    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        """Return a dictionary of fitted model statistics."""
        if self.omega is None:
            raise RuntimeError("Model has not been fitted yet.")
        persistence = self.alpha + self.beta
        unconditional_var = (
            self.omega / (1 - persistence)
            if persistence < 1
            else float("inf")
        )
        return {
            "omega": self.omega,
            "alpha": self.alpha,
            "beta": self.beta,
            "persistence (α+β)": persistence,
            "unconditional_variance": unconditional_var,
            "log_likelihood": self.log_likelihood,
            "aic": self.aic,
            "bic": self.bic,
        }


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)
    T = 2000

    # Simulate GARCH(1,1) process
    omega_true, alpha_true, beta_true = 1e-4, 0.10, 0.85
    sigma2 = np.empty(T)
    sigma2[0] = omega_true / (1 - alpha_true - beta_true)
    rets = np.empty(T)
    for t in range(1, T):
        sigma2[t] = omega_true + alpha_true * rets[t - 1] ** 2 + beta_true * sigma2[t - 1]
        rets[t] = np.random.normal(0, np.sqrt(sigma2[t]))
    rets[0] = np.random.normal(0, np.sqrt(sigma2[0]))

    model = GARCH11(rets).fit()
    stats = model.summary()

    print("=" * 60)
    print("GARCH(1,1) Model — Demo")
    print("=" * 60)
    print(f"  True params:     ω={omega_true:.6f}  α={alpha_true:.4f}  β={beta_true:.4f}")
    print(f"  Estimated params: ω={stats['omega']:.6f}  α={stats['alpha']:.4f}  β={stats['beta']:.4f}")
    print(f"  Persistence (α+β): {stats['persistence (α+β)']:.4f}")
    print(f"  Uncond. variance:   {stats['unconditional_variance']:.6f}")
    print(f"  Log-Likelihood:     {stats['log_likelihood']:.2f}")
    print(f"  AIC: {stats['aic']:.2f}  BIC: {stats['bic']:.2f}")

    fc = model.forecast(10)
    print(f"\n  10-step-ahead σ² forecast: {fc[-1]:.6f}")

    for cl in [0.95, 0.99]:
        v = model.var(confidence=cl)
        c = model.cvar(confidence=cl)
        print(f"  VaR({cl:.0%})  = {v:.6f}")
        print(f"  CVaR({cl:.0%}) = {c:.6f}")
    print("=" * 60)
