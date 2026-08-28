r"""
Monte Carlo Simulation & Risk Metrics
=========================================

A comprehensive toolkit for portfolio risk analysis using Monte Carlo
methods and analytical approximations.

Capabilities
-------------
1. **Geometric Brownian Motion (GBM)** simulation of portfolio paths
2. **VaR** — Historical, Parametric (Gaussian), and Monte Carlo
3. **CVaR / Expected Shortfall** — from all three VaR methods
4. **Correlation stress testing** — perturb the correlation matrix
   and re-evaluate portfolio risk
5. **Portfolio optimisation** — mean-variance (min variance) and
   maximum Sharpe ratio

All heavy computation uses vectorised NumPy operations for speed.

References
----------
Hull, J.C. (2018). Options, Futures, and Other Derivatives (10th ed.).
Markowitz, H. (1952). Portfolio Selection. Journal of Finance,
    7(1), 77-91.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ======================================================================
# Geometric Brownian Motion
# ======================================================================

def simulate_gbm(
    S0: float,
    mu: float,
    sigma: float,
    T: float = 1.0,
    n_steps: int = 252,
    n_paths: int = 10_000,
    seed: Optional[int] = None,
) -> np.ndarray:
    r"""Simulate Geometric Brownian Motion paths.

    .. math::

        dS_t = \mu S_t \, dt + \sigma S_t \, dW_t

    Euler-Maruyama discretisation:

        S_{t+\Delta t} = S_t \exp\!
            \bigl[(\mu - \tfrac{1}{2}\sigma^2)\Delta t
                  + \sigma\sqrt{\Delta t}\, Z\bigr]

    Parameters
    ----------
    S0 : float
        Initial value.
    mu : float
        Annualised drift (expected return).
    sigma : float
        Annualised volatility.
    T : float
        Time horizon in years (default 1.0).
    n_steps : int
        Number of time steps per path.
    n_paths : int
        Number of simulation paths.
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    np.ndarray of shape (n_paths, n_steps + 1)
        Simulated paths (each row is a path).
    """
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()

    dt = T / n_steps
    drift = (mu - 0.5 * sigma ** 2) * dt
    diffusion = sigma * np.sqrt(dt)

    Z = rng.standard_normal((n_paths, n_steps))
    log_increments = drift + diffusion * Z
    log_prices = np.zeros((n_paths, n_steps + 1))
    log_prices[:, 0] = np.log(S0)
    log_prices[:, 1:] = np.log(S0) + np.cumsum(log_increments, axis=1)

    return np.exp(log_prices)


def simulate_portfolio_gbm(
    weights: np.ndarray,
    mu_vec: np.ndarray,
    cov_matrix: np.ndarray,
    T: float = 1.0,
    n_steps: int = 252,
    n_paths: int = 10_000,
    seed: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """Simulate correlated GBM paths for a portfolio.

    Parameters
    ----------
    weights : ndarray (N,)
        Portfolio weights (need not sum to 1 — cash is implicit).
    mu_vec : ndarray (N,)
        Expected returns for each asset.
    cov_matrix : ndarray (N, N)
        Covariance matrix of asset returns.
    T, n_steps, n_paths, seed
        Forwarded to :func:`simulate_gbm`.

    Returns
    -------
    dict with keys:
        - ``paths`` : ndarray (N, n_paths, n_steps + 1)
        - ``portfolio_paths`` : ndarray (n_paths, n_steps + 1)
        - ``terminal_returns`` : ndarray (n_paths,)
    """
    weights = np.asarray(weights, dtype=np.float64).ravel()
    mu_vec = np.asarray(mu_vec, dtype=np.float64).ravel()
    cov_matrix = np.asarray(cov_matrix, dtype=np.float64)
    N = len(weights)

    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()

    # Cholesky decomposition
    try:
        L = np.linalg.cholesky(cov_matrix)
    except np.linalg.LinAlgError:
        # Add small epsilon to diagonal for numerical stability
        cov_reg = cov_matrix + np.eye(N) * 1e-8
        L = np.linalg.cholesky(cov_reg)

    dt = T / n_steps
    Z = rng.standard_normal((n_paths, n_steps, N))
    correlated_Z = Z @ L.T  # (n_paths, n_steps, N)

    # GBM increments for each asset
    drifts = (mu_vec - 0.5 * np.diag(cov_matrix)) * dt
    diffs = np.sqrt(dt) * correlated_Z
    increments = drifts[None, None, :] + diffs

    # Cumulative log-prices (start at S0 = 100 for each asset)
    S0 = 100.0
    log_prices = np.zeros((n_paths, n_steps + 1, N))
    log_prices[:, 0, :] = np.log(S0)
    log_prices[:, 1:, :] = np.log(S0) + np.cumsum(increments, axis=1)
    prices = np.exp(log_prices)

    # Portfolio value paths
    portfolio_paths = prices @ weights  # (n_paths, n_steps + 1)
    # Terminal returns (simple)
    terminal_returns = (portfolio_paths[:, -1] - portfolio_paths[:, 0]) / portfolio_paths[:, 0]

    return {
        "paths": prices,
        "portfolio_paths": portfolio_paths,
        "terminal_returns": terminal_returns,
    }


# ======================================================================
# Value-at-Risk
# ======================================================================

def var_historical(
    returns: np.ndarray,
    confidence: float = 0.95,
    weights: Optional[np.ndarray] = None,
) -> float:
    """Historical (empirical) VaR.

    Parameters
    ----------
    returns : ndarray (T, N) or (T,)
        Historical return series.
    confidence : float
        Confidence level.
    weights : ndarray (N,) or None
        If *returns* is (T, N) and weights are provided, portfolio
        returns are computed first.

    Returns
    -------
    float
        VaR (positive number, loss magnitude).
    """
    returns = np.asarray(returns, dtype=np.float64)
    if weights is not None:
        weights = np.asarray(weights, dtype=np.float64).ravel()
        if returns.ndim == 2:
            port_ret = returns @ weights
        else:
            port_ret = returns
    else:
        port_ret = returns.ravel()

    alpha = 1.0 - confidence
    var = float(np.percentile(port_ret, alpha * 100))
    return abs(var)


def var_parametric(
    mu: float,
    sigma: float,
    confidence: float = 0.95,
    T: float = 1.0,
) -> float:
    r"""Parametric (Gaussian) VaR.

    .. math::

        VaR_\alpha = -(\mu T + z_\alpha \sigma \sqrt{T})

    Parameters
    ----------
    mu : float
        Expected portfolio return (annualised).
    sigma : float
        Portfolio volatility (annualised).
    confidence : float
    T : float
        Horizon in years.

    Returns
    -------
    float
        VaR (positive number).
    """
    from scipy.stats import norm

    alpha = 1.0 - confidence
    z = norm.ppf(alpha)
    var = -(mu * T + z * sigma * np.sqrt(T))
    return float(max(var, 0.0))


def var_monte_carlo(
    simulated_returns: np.ndarray,
    confidence: float = 0.95,
) -> float:
    """Monte Carlo VaR from simulated terminal returns.

    Parameters
    ----------
    simulated_returns : ndarray (n_paths,)
    confidence : float

    Returns
    -------
    float
    """
    alpha = 1.0 - confidence
    var = float(np.percentile(simulated_returns, alpha * 100))
    return abs(var)


# ======================================================================
# CVaR / Expected Shortfall
# ======================================================================

def cvar_historical(
    returns: np.ndarray,
    confidence: float = 0.95,
    weights: Optional[np.ndarray] = None,
) -> float:
    """Historical CVaR (Expected Shortfall).

    Parameters
    ----------
    returns : ndarray
    confidence : float
    weights : ndarray or None

    Returns
    -------
    float
    """
    returns = np.asarray(returns, dtype=np.float64)
    if weights is not None:
        weights = np.asarray(weights, dtype=np.float64).ravel()
        if returns.ndim == 2:
            port_ret = returns @ weights
        else:
            port_ret = returns
    else:
        port_ret = returns.ravel()

    alpha = 1.0 - confidence
    cutoff = float(np.percentile(port_ret, alpha * 100))
    tail = port_ret[port_ret <= cutoff]
    if len(tail) == 0:
        return abs(cutoff)
    return abs(float(np.mean(tail)))


def cvar_parametric(
    mu: float,
    sigma: float,
    confidence: float = 0.95,
    T: float = 1.0,
) -> float:
    r"""Parametric (Gaussian) CVaR.

    .. math::

        CVaR_\alpha = -\mu T + \sigma\sqrt{T}
            \frac{\varphi(\Phi^{-1}(\alpha))}{\alpha}

    Parameters
    ----------
    mu, sigma, confidence, T
        Same as :func:`var_parametric`.
    """
    from scipy.stats import norm

    alpha = 1.0 - confidence
    z = norm.ppf(alpha)
    cvar = -mu * T + sigma * np.sqrt(T) * norm.pdf(z) / alpha
    return float(max(cvar, 0.0))


def cvar_monte_carlo(
    simulated_returns: np.ndarray,
    confidence: float = 0.95,
) -> float:
    """Monte Carlo CVaR from simulated terminal returns."""
    alpha = 1.0 - confidence
    cutoff = float(np.percentile(simulated_returns, alpha * 100))
    tail = simulated_returns[simulated_returns <= cutoff]
    if len(tail) == 0:
        return abs(cutoff)
    return abs(float(np.mean(tail)))


# ======================================================================
# Correlation Stress Testing
# ======================================================================

def stress_correlation(
    cov_matrix: np.ndarray,
    pair: Tuple[int, int],
    new_corr: float,
) -> np.ndarray:
    r"""Perturb a single correlation pair and rebuild a valid
    covariance matrix.

    The routine:
    1. Converts covariance → correlation matrix.
    2. Sets corr[i,j] = corr[j,i] = *new_corr*.
    3. Repairs the matrix to be positive semi-definite via
       eigenvalue clipping.
    4. Rescales back to a covariance matrix using the original
       standard deviations.

    Parameters
    ----------
    cov_matrix : ndarray (N, N)
    pair : tuple (i, j)
        The correlation pair to stress.
    new_corr : float
        New correlation value in [-1, 1].

    Returns
    -------
    np.ndarray (N, N)
        Stressed covariance matrix.
    """
    cov = np.asarray(cov_matrix, dtype=np.float64).copy()
    N = cov.shape[0]
    i, j = pair

    std = np.sqrt(np.diag(cov))
    corr = cov / np.outer(std, std)

    new_corr = float(np.clip(new_corr, -0.999, 0.999))
    corr[i, j] = new_corr
    corr[j, i] = new_corr

    # Repair PSD via eigenvalue clipping
    eigvals, eigvecs = np.linalg.eigh(corr)
    eigvals = np.maximum(eigvals, 1e-8)
    corr = eigvecs @ np.diag(eigvals) @ eigvecs.T
    corr = (corr + corr.T) / 2.0

    # Rescale to covariance
    stressed_cov = corr * np.outer(std, std)
    return stressed_cov


def stress_correlation_uniform(
    cov_matrix: np.ndarray,
    shock: float = 0.2,
) -> np.ndarray:
    r"""Apply a uniform correlation shock to all off-diagonal elements.

    .. math::

        \rho^{new}_{ij} = \rho_{ij} + \text{shock} \cdot
        \text{sign}(\rho_{ij})

    Clamped to [-0.999, 0.999] and repaired to PSD.

    Parameters
    ----------
    cov_matrix : ndarray (N, N)
    shock : float
        Magnitude of the correlation shock.

    Returns
    -------
    np.ndarray (N, N)
    """
    cov = np.asarray(cov_matrix, dtype=np.float64).copy()
    N = cov.shape[0]

    std = np.sqrt(np.diag(cov))
    corr = cov / np.outer(std, std)

    # Apply shock
    for i in range(N):
        for j in range(i + 1, N):
            sgn = 1.0 if corr[i, j] >= 0 else -1.0
            new_val = corr[i, j] + shock * sgn
            new_val = float(np.clip(new_val, -0.999, 0.999))
            corr[i, j] = new_val
            corr[j, i] = new_val

    # Repair PSD
    eigvals, eigvecs = np.linalg.eigh(corr)
    eigvals = np.maximum(eigvals, 1e-8)
    corr = eigvecs @ np.diag(eigvals) @ eigvecs.T
    corr = (corr + corr.T) / 2.0

    stressed_cov = corr * np.outer(std, std)
    return stressed_cov


# ======================================================================
# Portfolio Optimisation
# ======================================================================

def optimize_min_variance(
    cov_matrix: np.ndarray,
) -> Dict[str, Any]:
    r"""Minimum-variance portfolio (long-only, fully invested).

    .. math::

        \min_w \; w' \Sigma w \quad\text{s.t.}\; \sum w_i = 1,
        \; w_i \ge 0

    Uses scipy SLSQP.

    Parameters
    ----------
    cov_matrix : ndarray (N, N)

    Returns
    -------
    dict with keys:
        - ``weights" : ndarray (N,)
        - ``portfolio_variance" : float
        - ``portfolio_volatility" : float
    """
    from scipy.optimize import minimize

    cov = np.asarray(cov_matrix, dtype=np.float64)
    N = cov.shape[0]

    def objective(w):
        return float(w @ cov @ w)

    def jac(w):
        return 2.0 * cov @ w

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * N
    w0 = np.ones(N) / N

    result = minimize(
        objective, w0, jac=jac, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"ftol": 1e-15, "maxiter": 1000},
    )
    w_opt = result.x
    var_opt = float(w_opt @ cov @ w_opt)

    return {
        "weights": w_opt,
        "portfolio_variance": var_opt,
        "portfolio_volatility": np.sqrt(var_opt),
        "success": result.success,
    }


def optimize_max_sharpe(
    mu_vec: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.0,
) -> Dict[str, Any]:
    r"""Maximum Sharpe ratio portfolio (long-only, fully invested).

    .. math::

        \max_w \; \frac{w'\mu - r_f}{\sqrt{w'\Sigma w}}

    Implemented as minimisation of negative Sharpe via SLSQP.

    Parameters
    ----------
    mu_vec : ndarray (N,)
    cov_matrix : ndarray (N, N)
    risk_free_rate : float

    Returns
    -------
    dict with keys:
        - ``weights" : ndarray (N,)
        - ``expected_return" : float
        - ``portfolio_volatility" : float
        - ``sharpe_ratio" : float
    """
    from scipy.optimize import minimize

    mu = np.asarray(mu_vec, dtype=np.float64).ravel()
    cov = np.asarray(cov_matrix, dtype=np.float64)
    N = len(mu)

    def neg_sharpe(w):
        ret = w @ mu
        vol = np.sqrt(w @ cov @ w)
        if vol < 1e-12:
            return 0.0
        return -(ret - risk_free_rate) / vol

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * N
    w0 = np.ones(N) / N

    result = minimize(
        neg_sharpe, w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"ftol": 1e-15, "maxiter": 1000},
    )
    w_opt = result.x
    ret_opt = float(w_opt @ mu)
    vol_opt = float(np.sqrt(w_opt @ cov @ w_opt))
    sharpe = (ret_opt - risk_free_rate) / vol_opt if vol_opt > 1e-12 else 0.0

    return {
        "weights": w_opt,
        "expected_return": ret_opt,
        "portfolio_volatility": vol_opt,
        "sharpe_ratio": sharpe,
        "success": result.success,
    }


# ======================================================================
# Engine class (convenience)
# ======================================================================

class MonteCarloRiskEngine:
    """All-in-one Monte Carlo risk engine.

    Parameters
    ----------
    weights : array-like (N,)
    mu_vec : array-like (N,)
    cov_matrix : array-like (N, N)
    """

    def __init__(
        self,
        weights: np.ndarray,
        mu_vec: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> None:
        self.weights = np.asarray(weights, dtype=np.float64).ravel()
        self.mu_vec = np.asarray(mu_vec, dtype=np.float64).ravel()
        self.cov_matrix = np.asarray(cov_matrix, dtype=np.float64)
        self.N = len(self.weights)

    def simulate(
        self,
        T: float = 1.0,
        n_steps: int = 252,
        n_paths: int = 10_000,
        seed: Optional[int] = None,
    ) -> Dict[str, np.ndarray]:
        """Run portfolio GBM simulation.

        Returns the dict from :func:`simulate_portfolio_gbm`.
        """
        return simulate_portfolio_gbm(
            self.weights, self.mu_vec, self.cov_matrix,
            T=T, n_steps=n_steps, n_paths=n_paths, seed=seed,
        )

    def risk_report(
        self,
        historical_returns: Optional[np.ndarray] = None,
        confidence: float = 0.95,
        n_paths: int = 50_000,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive risk report.

        Returns a dict with parametric, historical (if data given),
        and Monte Carlo VaR and CVaR, plus optimal portfolio weights.
        """
        # Parametric
        port_mu = float(self.weights @ self.mu_vec)
        port_sigma = float(np.sqrt(self.weights @ self.cov_matrix @ self.weights))

        report: Dict[str, Any] = {
            "parametric": {
                "var": var_parametric(port_mu, port_sigma, confidence),
                "cvar": cvar_parametric(port_mu, port_sigma, confidence),
                "mu": port_mu,
                "sigma": port_sigma,
            },
            "monte_carlo": {},
        }

        # Monte Carlo
        sim = self.simulate(n_paths=n_paths, seed=seed)
        mc_ret = sim["terminal_returns"]
        report["monte_carlo"] = {
            "var": var_monte_carlo(mc_ret, confidence),
            "cvar": cvar_monte_carlo(mc_ret, confidence),
            "mean_return": float(np.mean(mc_ret)),
            "std_return": float(np.std(mc_ret)),
        }

        # Historical (if provided)
        if historical_returns is not None:
            hr = np.asarray(historical_returns, dtype=np.float64)
            report["historical"] = {
                "var": var_historical(hr, confidence, self.weights),
                "cvar": cvar_historical(hr, confidence, self.weights),
            }

        # Optimisation
        report["min_variance"] = optimize_min_variance(self.cov_matrix)
        report["max_sharpe"] = optimize_max_sharpe(
            self.mu_vec, self.cov_matrix
        )

        return report


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)

    tickers = ["Equity", "Bonds", "Commod", "REITs"]
    N = len(tickers)
    mu_vec = np.array([0.08, 0.03, 0.06, 0.05])

    # Build a valid covariance matrix
    A = np.array([
        [ 0.04,  0.005, 0.01,  0.015],
        [ 0.005, 0.01,  0.002, 0.003],
        [ 0.01,  0.002, 0.025, 0.008],
        [ 0.015, 0.003, 0.008, 0.02 ],
    ])
    weights = np.array([0.4, 0.3, 0.15, 0.15])

    engine = MonteCarloRiskEngine(weights, mu_vec, A)

    print("=" * 60)
    print("Monte Carlo Risk Engine — Demo")
    print("=" * 60)

    report = engine.risk_report(
        confidence=0.95, n_paths=20_000, seed=42
    )

    # Parametric
    p = report["parametric"]
    print(f"\n  Parametric (Gaussian):")
    print(f"    μ = {p['mu']:.4f}   σ = {p['sigma']:.4f}")
    print(f"    VaR(95%)  = {p['var']:.4f}")
    print(f"    CVaR(95%) = {p['cvar']:.4f}")

    # Monte Carlo
    mc = report["monte_carlo"]
    print(f"\n  Monte Carlo (20,000 paths):")
    print(f"    VaR(95%)  = {mc['var']:.4f}")
    print(f"    CVaR(95%) = {mc['cvar']:.4f}")
    print(f"    E[R] = {mc['mean_return']:.4f}  std = {mc['std_return']:.4f}")

    # Optimisation
    mv = report["min_variance"]
    ms = report["max_sharpe"]
    print(f"\n  Min-Variance portfolio:")
    for t, w in zip(tickers, mv["weights"]):
        print(f"    {t:>10s}: {w:7.2%}  (σ = {mv['portfolio_volatility']:.4f})")
    print(f"\n  Max-Sharpe portfolio:")
    for t, w in zip(tickers, ms["weights"]):
        print(f"    {t:>10s}: {w:7.2%}  (SR = {ms['sharpe_ratio']:.4f})")

    # Stress test
    print(f"\n  Stress test (shock Equity-Commod corr to 0.8):")
    stressed = stress_correlation(A, pair=(0, 2), new_corr=0.8)
    stressed_engine = MonteCarloRiskEngine(weights, mu_vec, stressed)
    sim_s = stressed_engine.simulate(n_paths=10_000, seed=42)
    print(f"    MC VaR(95%) under stress = {var_monte_carlo(sim_s['terminal_returns'], 0.95):.4f}")

    print("\n" + "=" * 60)
