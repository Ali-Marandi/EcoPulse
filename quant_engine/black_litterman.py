"""
Black-Litterman Bayesian Portfolio Allocation Model
====================================================

Implements the full Black-Litterman (BL) model, which combines market
equilibrium (implied by market-cap weights) with an investor's subjective
views to produce posterior expected returns and a posterior covariance
matrix that are more stable and intuitive than raw sample estimates.

The canonical BL formulae (He & Litterman, 1999):

    Posterior mean:
        μ_BL = [(τΣ)^{-1} + P'Ω^{-1}P]^{-1} [(τΣ)^{-1}Π + P'Ω^{-1}Q]

    Posterior covariance:
        Σ_BL = Σ + [(τΣ)^{-1} + P'Ω^{-1}P]^{-1}

where
    Π  = implied equilibrium excess returns (from market-cap weights)
    τ  = scalar uncertainty parameter (typically 0.025 - 0.05)
    P  = pick matrix mapping views to assets (K × N)
    Q  = view expected returns vector (K × 1)
    Ω  = view uncertainty diagonal matrix (K × K)

References
----------
Black, F. & Litterman, R. (1992). Global Portfolio Optimization.
    Financial Analysts Journal, 48(5), 28-43.
He, G. & Litterman, R. (1999). The Intuition Behind Black-Litterman
    Model Portfolios. Goldman Sachs Investment Management Research.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


def _ensure_2d(arr: np.ndarray, name: str = "array") -> np.ndarray:
    """Coerce *arr* to a 2-D float64 numpy array."""
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 1:
        a = a.reshape(-1, 1)
    if a.ndim != 2:
        raise ValueError(f"{name} must be 1-D or 2-D, got shape {a.shape}")
    return a


def _ensure_positive_definite(
    cov: np.ndarray, eps: float = 1e-8
) -> np.ndarray:
    """Add a small diagonal term if *cov* is not positive-definite."""
    cov = _ensure_2d(cov, "covariance")
    # Ensure symmetry
    cov = (cov + cov.T) / 2.0
    eigvals = np.linalg.eigvalsh(cov)
    if eigvals.min() < eps:
        cov += np.eye(cov.shape[0]) * (eps - eigvals.min() + 1e-10)
    return cov


@dataclass
class BlView:
    """A single investor view for the Black-Litterman model.

    Parameters
    ----------
    asset : str or int
        Identifier (ticker or column index) of the asset the view
        concerns.  Use ``"ALL"`` to specify a relative view across
        multiple assets (see *relative_to*).
    view_return : float
        The investor's expected excess return for the asset (absolute
        view) or the expected return differential (relative view),
        expressed in the same units as the covariance matrix.
    confidence : float
        Confidence in the view, in (0, 1].  1.0 means full confidence;
        lower values increase the variance allocated to the view in Ω.
    relative_to : str or int or None
        If provided, the view is *relative* — ``view_return`` is the
        expected outperformance of *asset* over *relative_to*.
    """

    asset: str | int
    view_return: float
    confidence: float = 1.0
    relative_to: Optional[str | int] = None

    def __post_init__(self) -> None:
        if not (0.0 < self.confidence <= 1.0):
            raise ValueError("confidence must be in (0, 1]")


class BlackLittermanModel:
    """Black-Litterman Bayesian portfolio model.

    Parameters
    ----------
    market_cap_weights : array-like of shape (N,)
        Market-capitalisation weights for *N* assets.  Must sum to 1.
    covariance_matrix : array-like of shape (N, N)
        Covariance matrix of asset excess returns.
    risk_aversion : float, optional
        The coefficient of risk aversion δ used to reverse-engineer
        implied equilibrium returns (default 2.5).
    tau : float, optional
        Scalar parameter capturing the uncertainty in the prior
        (implied returns).  Common values are 0.025 – 0.05
        (default 0.05).
    epsilon : float, optional
        Small constant added to the diagonal of covariance matrices
        to guarantee numerical invertibility (default 1e-8).
    """

    def __init__(
        self,
        market_cap_weights: np.ndarray,
        covariance_matrix: np.ndarray,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
        epsilon: float = 1e-8,
    ) -> None:
        self.tau = float(tau)
        self.risk_aversion = float(risk_aversion)
        self.epsilon = float(epsilon)

        self.w_market = _ensure_2d(market_cap_weights, "market_cap_weights").ravel()
        if abs(self.w_market.sum() - 1.0) > 1e-6:
            # Normalise if close enough, otherwise warn
            self.w_market = self.w_market / self.w_market.sum()

        self.cov = _ensure_positive_definite(covariance_matrix, eps=self.epsilon)
        self.n_assets = len(self.w_market)

    # ------------------------------------------------------------------
    # Implied equilibrium returns
    # ------------------------------------------------------------------
    def compute_implied_equilibrium(
        self, delta: Optional[float] = None
    ) -> np.ndarray:
        """Reverse-engineer implied excess equilibrium returns.

        Π = δ Σ w_market

        Parameters
        ----------
        delta : float or None
            Override risk-aversion coefficient.  If *None*, uses the
            value passed at construction.

        Returns
        -------
        np.ndarray of shape (N,)
            Implied equilibrium excess returns for each asset.
        """
        delta = delta if delta is not None else self.risk_aversion
        cov = self.cov + np.eye(self.n_assets) * self.epsilon
        pi = delta * cov @ self.w_market
        return pi.ravel()

    # ------------------------------------------------------------------
    # Build P, Q, Ω from a list of BlView objects
    # ------------------------------------------------------------------
    @staticmethod
    def _build_view_matrices(
        views: List[BlView],
        asset_identifiers: List[str | int],
        tau_sigma: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Construct P, Q, and Ω from a list of :class:`BlView`.

        The uncertainty matrix Ω is constructed such that:

            Ω_kk = P_k τΣ P_k' / confidence_k

        This ensures that the variance attributed to a view scales with
        its exposure and inversely with the investor's confidence.
        """
        if not views:
            return (
                np.zeros((0, len(asset_identifiers))),
                np.zeros(0),
                np.zeros((0, 0)),
            )

        id_to_idx = {aid: i for i, aid in enumerate(asset_identifiers)}
        K = len(views)
        N = len(asset_identifiers)
        P = np.zeros((K, N))
        Q = np.zeros(K)
        omega_diag = np.zeros(K)

        for k, view in enumerate(views):
            if view.relative_to is not None:
                # Relative view
                i = id_to_idx[view.asset]
                j = id_to_idx[view.relative_to]
                P[k, i] = 1.0
                P[k, j] = -1.0
            else:
                i = id_to_idx[view.asset]
                P[k, i] = 1.0
            Q[k] = view.view_return

            # View variance: higher confidence → lower Ω
            p_k = P[k]
            variance = float(p_k @ tau_sigma @ p_k)
            omega_diag[k] = variance / view.confidence

        Omega = np.diag(omega_diag) + np.eye(K) * 1e-12  # numerical guard
        return P, Q, Omega

    # ------------------------------------------------------------------
    # Main BL computation
    # ------------------------------------------------------------------
    def compute_posterior(
        self,
        views: List[BlView],
        asset_identifiers: Optional[List[str | int]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute the Black-Litterman posterior distribution.

        Parameters
        ----------
        views : list of BlView
            Investor views.
        asset_identifiers : list of str/int or None
            Ordered identifiers (tickers or indices) for each asset column.
            If *None*, integer indices ``0 … N-1`` are used.

        Returns
        -------
        mu_bl : np.ndarray of shape (N,)
            Posterior expected excess returns.
        cov_bl : np.ndarray of shape (N, N)
            Posterior covariance matrix of returns.
        """
        if asset_identifiers is None:
            asset_identifiers = list(range(self.n_assets))
        if len(asset_identifiers) != self.n_assets:
            raise ValueError(
                f"Expected {self.n_assets} identifiers, got {len(asset_identifiers)}"
            )

        # Implied equilibrium returns
        pi = self.compute_implied_equilibrium()

        # τΣ — prior uncertainty
        tau_sigma = self.tau * self.cov
        # Regularise for inversion
        tau_sigma_reg = tau_sigma + np.eye(self.n_assets) * self.epsilon
        tau_sigma_inv = np.linalg.inv(tau_sigma_reg)

        # Build view matrices
        P, Q, Omega = self._build_view_matrices(
            views, asset_identifiers, tau_sigma
        )

        if len(views) == 0:
            # No views — posterior equals prior
            return pi, self.cov

        Omega_inv = np.linalg.inv(Omega)

        # Posterior precision
        M = tau_sigma_inv + P.T @ Omega_inv @ P
        M += np.eye(self.n_assets) * self.epsilon  # numerical guard

        # Posterior mean
        M_inv = np.linalg.inv(M)
        mu_bl = M_inv @ (tau_sigma_inv @ pi + P.T @ Omega_inv @ Q)

        # Posterior covariance
        cov_bl = self.cov + M_inv

        return mu_bl.ravel(), cov_bl

    # ------------------------------------------------------------------
    # Optimal portfolio from posterior
    # ------------------------------------------------------------------
    def optimal_weights(
        self,
        mu_bl: np.ndarray,
        cov_bl: Optional[np.ndarray] = None,
        delta: Optional[float] = None,
    ) -> np.ndarray:
        """Compute the mean-variance optimal weights from posterior returns.

        w* = (δ Σ_BL)^{-1} μ_BL

        Parameters
        ----------
        mu_bl : array-like of shape (N,)
            Posterior expected excess returns.
        cov_bl : array-like of shape (N, N) or None
            Posterior covariance.  If *None*, uses the model's ``cov``.
        delta : float or None
            Risk-aversion coefficient.  If *None*, uses the model's
            ``risk_aversion``.

        Returns
        -------
        np.ndarray of shape (N,)
            Optimal portfolio weights (may sum to > 1 if there is a
            risk-free asset).
        """
        delta = delta if delta is not None else self.risk_aversion
        if cov_bl is None:
            cov_bl = self.cov
        cov_bl = _ensure_positive_definite(cov_bl, eps=self.epsilon)
        w = np.linalg.solve(delta * cov_bl, mu_bl)
        return w.ravel()

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------
    def run(
        self,
        views: List[BlView],
        asset_identifiers: Optional[List[str | int]] = None,
    ) -> dict:
        """Execute the full Black-Litterman pipeline.

        Returns a dictionary with keys:
        - ``implied_returns`` : np.ndarray
        - ``posterior_returns`` : np.ndarray
        - ``posterior_cov`` : np.ndarray
        - ``optimal_weights`` : np.ndarray
        - ``active_weights`` : np.ndarray (difference vs. market)
        """
        pi = self.compute_implied_equilibrium()
        mu_bl, cov_bl = self.compute_posterior(views, asset_identifiers)
        w_opt = self.optimal_weights(mu_bl, cov_bl)

        return {
            "implied_returns": pi,
            "posterior_returns": mu_bl,
            "posterior_cov": cov_bl,
            "optimal_weights": w_opt,
            "active_weights": w_opt - self.w_market,
        }


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)

    # --- Synthetic data ---
    tickers = ["USA", "EUR", "EMG", "JPN", "GBR"]
    N = len(tickers)

    # Random positive-definite covariance matrix
    A = np.random.randn(N, N) * 0.01
    cov = A.T @ A + np.eye(N) * 0.001

    # Market-cap weights
    w_mkt = np.array([0.40, 0.25, 0.10, 0.15, 0.10])

    # Views
    views = [
        BlView(asset="EMG", view_return=0.06, confidence=0.7),
        BlView(asset="USA", view_return=0.04, confidence=0.5),
        BlView(
            asset="EUR", view_return=0.02, confidence=0.6, relative_to="JPN"
        ),
    ]

    bl = BlackLittermanModel(
        market_cap_weights=w_mkt,
        covariance_matrix=cov,
        risk_aversion=2.5,
        tau=0.05,
    )

    result = bl.run(views, tickers)

    print("=" * 60)
    print("Black-Litterman Model — Demo")
    print("=" * 60)
    print(f"\nImplied equilibrium returns (Π):")
    for t, r in zip(tickers, result["implied_returns"]):
        print(f"  {t:4s}: {r:8.4%}")

    print(f"\nPosterior expected returns (μ_BL):")
    for t, r in zip(tickers, result["posterior_returns"]):
        print(f"  {t:4s}: {r:8.4%}")

    print(f"\nOptimal weights (w*) vs market weights (w_mkt):")
    for t, wm, wo, wa in zip(
        tickers, w_mkt, result["optimal_weights"], result["active_weights"]
    ):
        print(f"  {t:4s}: w_mkt={wm:7.2%}  w*={wo:7.2%}  Δ={wa:+7.2%}")
    print("=" * 60)
