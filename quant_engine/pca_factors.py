r"""
PCA Factor Analysis & Fama-French Style Factor Extraction
==========================================================

Provides two complementary tools:

1. **:class:`PCAFactorExtractor`** — General-purpose PCA factor
   extraction from a T × N asset-returns matrix.  Returns the
   principal-component factor time-series, factor loadings
   (exposures), and explained-variance ratios.

2. **:func:`yield_curve_decomposition`** — Decomposes a yield-curve
   matrix (T × M maturities) into the classic three level / slope /
   curvature factors using PCA.

Both use :class:`sklearn.decomposition.PCA` under the hood.

References
----------
Connor, G. & Korajczyk, R.A. (1988). Risk and Return in an
    Equilibrium APT. Journal of Financial Economics, 21(2), 255-289.
Litterman, R. & Scheinkman, J. (1991). Common Factors Affecting Bond
    Returns. Journal of Fixed Income, 1(1), 54-61.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.decomposition import PCA


class PCAFactorExtractor:
    """Extract statistical risk factors via Principal Component Analysis.

    Parameters
    ----------
    n_components : int or float or None, optional
        Number of components to retain.  If an ``int`` in [1, N), that
        many components are kept.  If a ``float`` in (0, 1), components
        are retained until the cumulative explained-variance ratio
        exceeds this threshold.  If *None* (default), all components
        are returned.
    standardise : bool, optional
        If *True* (default), the returns matrix is de-meaned and
        standardised (z-scored) before PCA.
    """

    def __init__(
        self,
        n_components: Optional[int | float] = None,
        standardise: bool = True,
    ) -> None:
        self.n_components = n_components
        self.standardise = standardise
        self._pca: Optional[PCA] = None
        self._factor_names: List[str] = []

    def fit_transform(
        self,
        returns: np.ndarray,
        asset_names: Optional[List[str]] = None,
    ) -> Dict:
        """Fit PCA and return factors, loadings, and variance info.

        Parameters
        ----------
        returns : array-like of shape (T, N)
            Matrix of asset returns (T periods, N assets).
        asset_names : list of str or None
            Human-readable asset identifiers.

        Returns
        -------
        dict with keys:
            - ``factors``       : np.ndarray (T, K) — factor time-series
            - ``loadings``      : np.ndarray (N, K) — asset exposures
            - ``explained_var`` : np.ndarray (K,) — per-component variance
            - ``explained_var_ratio`` : np.ndarray (K,)
            - ``cumulative_var_ratio``  : np.ndarray (K,)
            - ``asset_names``   : list of str
            - ``factor_names``  : list of str  (e.g. "PC1", "PC2", …)
        """
        X = np.asarray(returns, dtype=np.float64)
        if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 2:
            raise ValueError(
                "returns must be a 2-D array with T ≥ 2 and N ≥ 2"
            )
        T, N = X.shape

        # Standardise
        if self.standardise:
            mu = X.mean(axis=0)
            sd = X.std(axis=0, ddof=1)
            sd[sd < 1e-12] = 1.0
            X = (X - mu) / sd

        if asset_names is None:
            asset_names = [f"Asset_{i}" for i in range(N)]

        # Determine n_components
        n_comp = self.n_components
        if isinstance(n_comp, float):
            # MLE to find how many components needed
            pca_full = PCA().fit(X)
            cum = np.cumsum(pca_full.explained_variance_ratio_)
            n_comp = int(np.searchsorted(cum, n_comp) + 1)
            n_comp = min(n_comp, min(T, N))
        elif n_comp is None:
            n_comp = min(T, N)

        self._pca = PCA(n_components=n_comp)
        factors = self._pca.fit_transform(X)  # (T, K)
        K = factors.shape[1]

        loadings = self._pca.components_.T  # (N, K)
        ev = self._pca.explained_variance_
        evr = self._pca.explained_variance_ratio_
        cum_evr = np.cumsum(evr)

        self._factor_names = [f"PC{i + 1}" for i in range(K)]

        return {
            "factors": factors,
            "loadings": loadings,
            "explained_var": ev,
            "explained_var_ratio": evr,
            "cumulative_var_ratio": cum_evr,
            "asset_names": asset_names,
            "factor_names": self._factor_names,
        }

    # ------------------------------------------------------------------
    # Convenience: reconstruct returns from top-K factors
    # ------------------------------------------------------------------
    def reconstruct(
        self,
        returns: np.ndarray,
        n_factors: int,
    ) -> np.ndarray:
        """Reconstruct the return matrix using only *n_factors* PCs.

        Returns
        -------
        np.ndarray of shape (T, N)
        """
        X = np.asarray(returns, dtype=np.float64)
        if self.standardise:
            mu = X.mean(axis=0)
            sd = X.std(axis=0, ddof=1)
            sd[sd < 1e-12] = 1.0
            X_z = (X - mu) / sd
        else:
            mu = np.zeros(X.shape[1])
            sd = np.ones(X.shape[1])
            X_z = X

        pca = PCA(n_components=n_factors).fit(X_z)
        scores = pca.transform(X_z)
        recon_z = scores @ pca.components_  # (T, N)
        recon = recon_z * sd + mu
        return recon


# ======================================================================
# Yield Curve Decomposition
# ======================================================================

def yield_curve_decomposition(
    yields: np.ndarray,
    maturities: Optional[np.ndarray] = None,
) -> Dict:
    """Decompose a yield-curve matrix into level, slope, and curvature.

    Parameters
    ----------
    yields : array-like of shape (T, M)
        Yield-curve observations (T dates, M maturities).  Each row is
        a single cross-section of yields across maturities.
    maturities : array-like of shape (M,) or None
        Maturity points in years.  If *None*, assumes evenly spaced
        maturities starting at 1 year.

    Returns
    -------
    dict with keys:
        - ``level``     : np.ndarray (T,) — 1st PC scores (≈ average yield)
        - ``slope``     : np.ndarray (T,) — 2nd PC scores (≈ long-short spread)
        - ``curvature`` : np.ndarray (T,) — 3rd PC scores (≈ belly of curve)
        - ``level_loading``    : np.ndarray (M,)
        - ``slope_loading``    : np.ndarray (M,)
        - ``curvature_loading``: np.ndarray (M,)
        - ``explained_var_ratio``: np.ndarray (3,)
        - ``maturities`` : np.ndarray (M,)
    """
    Y = np.asarray(yields, dtype=np.float64)
    if Y.ndim != 2 or Y.shape[1] < 3:
        raise ValueError(
            "yields must be 2-D with at least 3 maturities"
        )

    T, M = Y.shape
    if maturities is None:
        maturities = np.arange(1, M + 1, dtype=np.float64)
    else:
        maturities = np.asarray(maturities, dtype=np.float64).ravel()

    # De-mean (but do NOT standardise — we want to preserve the
    # natural shape of the curve for interpretability).
    Y_centered = Y - Y.mean(axis=0)

    pca = PCA(n_components=3).fit(Y_centered)
    scores = pca.transform(Y_centered)  # (T, 3)
    loadings = pca.components_.T  # (M, 3)

    # For interpretability, flip signs so that:
    #   Level loading is mostly positive
    #   Slope loading increases with maturity
    if loadings[0, 0] < 0:
        scores[:, 0] *= -1
        loadings[:, 0] *= -1
    if loadings[0, 1] > loadings[-1, 1]:
        scores[:, 1] *= -1
        loadings[:, 1] *= -1
    # Curvature: make the middle-most maturity have the largest magnitude
    mid = M // 2
    if loadings[mid, 2] < 0:
        scores[:, 2] *= -1
        loadings[:, 2] *= -1

    return {
        "level": scores[:, 0],
        "slope": scores[:, 1],
        "curvature": scores[:, 2],
        "level_loading": loadings[:, 0],
        "slope_loading": loadings[:, 1],
        "curvature_loading": loadings[:, 2],
        "explained_var_ratio": pca.explained_variance_ratio_,
        "maturities": maturities,
    }


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)

    # --- Asset return PCA demo ---
    print("=" * 60)
    print("PCA Factor Extraction — Demo")
    print("=" * 60)

    T, N = 500, 10
    # Build 3 latent factors + noise
    f1 = np.random.randn(T)
    f2 = np.random.randn(T)
    f3 = np.random.randn(T)
    loadings_true = np.random.randn(N, 3) * 0.3
    noise = np.random.randn(T, N) * 0.05
    returns = (loadings_true @ np.vstack([f1, f2, f3])).T + noise

    extractor = PCAFactorExtractor(n_components=0.90)
    res = extractor.fit_transform(returns, [f"Asset_{i}" for i in range(N)])

    print(f"\n  Number of components retained: {len(res['factor_names'])}")
    for i, name in enumerate(res['factor_names']):
        print(
            f"    {name}: explained_var_ratio = "
            f"{res['explained_var_ratio'][i]:.4f}  "
            f"cumulative = {res['cumulative_var_ratio'][i]:.4f}"
        )

    # --- Yield-curve decomposition demo ---
    print("\n" + "=" * 60)
    print("Yield-Curve Decomposition — Demo")
    print("=" * 60)

    maturities = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])
    T_yc = 300
    # Simulate: level ~ N(4%, 0.5%), slope ~ N(2%, 0.3%), curvature ~ N(0, 0.2%)
    level_ts = np.random.normal(4.0, 0.5, T_yc)
    slope_ts = np.random.normal(2.0, 0.3, T_yc)
    curv_ts = np.random.normal(0.0, 0.2, T_yc)

    # Loadings (simplified Litterman-Scheinkman shape)
    L = np.ones(len(maturities)) * 0.8
    S = maturities / 30.0 * 1.5 - 0.3
    C = -((maturities - 5) ** 2) / 50.0 * 0.5

    yc = (
        level_ts[:, None] * L[None, :]
        + slope_ts[:, None] * S[None, :]
        + curv_ts[:, None] * C[None, :]
        + np.random.randn(T_yc, len(maturities)) * 0.1
    )

    ycd = yield_curve_decomposition(yc, maturities)
    print(
        f"\n  Explained variance ratios: "
        f"Level={ycd['explained_var_ratio'][0]:.4f}  "
        f"Slope={ycd['explained_var_ratio'][1]:.4f}  "
        f"Curvature={ycd['explained_var_ratio'][2]:.4f}  "
        f"Total={ycd['explained_var_ratio'].sum():.4f}"
    )
    print(f"  Level loading (first 5 maturities):  {ycd['level_loading'][:5].round(4)}")
    print(f"  Slope loading (first 5 maturities):  {ycd['slope_loading'][:5].round(4)}")
    print(f"  Curvature loading (first 5 maturities): {ycd['curvature_loading'][:5].round(4)}")
    print("=" * 60)
