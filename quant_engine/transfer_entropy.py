r"""
Transfer Entropy for Information Flow Analysis
===============================================

Implements Shannon entropy, conditional entropy, and transfer entropy
(TE) using histogram-based probability estimation.

Transfer entropy (Schreiber, 2000) measures the amount of directed
(time-asymmetric) transfer of information between two random
processes X and Y:

    TE(Y→X) = Σ p(x_{t+1}, x_t, y_t) · log[ p(x_{t+1} | x_t, y_t) / p(x_{t+1} | x_t) ]

A non-zero TE(Y→X) indicates that the past of Y contains
information about the future of X beyond what is contained in the
past of X alone.

The module also provides:

- **Normalised TE (effect size)**: TE / H(X_{t+1} | X_t)
- **Network analysis**: pairwise TE matrix for N time series.

References
----------
Schreiber, T. (2000). Measuring Information Transfer. Physical
    Review Letters, 85(2), 461-464.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


# ======================================================================
# Probability estimation
# ======================================================================

def _histogram_prob(
    data: np.ndarray,
    bins: int,
    range_: Optional[Tuple[float, float]] = None,
) -> Tuple[np.ndarray, List]:
    """Compute normalised histogram probabilities.

    Returns (prob_array, bin_edges).
    """
    if range_ is None:
        range_ = (float(data.min()), float(data.max()))
        # Avoid degenerate range
        if range_[1] - range_[0] < 1e-12:
            range_ = (range_[0] - 0.5, range_[0] + 0.5)
    counts, edges = np.histogram(data, bins=bins, range=range_, density=False)
    total = counts.sum()
    if total == 0:
        probs = np.ones_like(counts, dtype=np.float64) / bins
    else:
        probs = counts / total
    return probs, edges.tolist()


def _joint_histogram_prob(
    data: np.ndarray,
    bins_x: int,
    bins_y: int,
) -> np.ndarray:
    """2-D joint histogram probability matrix (normalised).

    Parameters
    ----------
    data : ndarray of shape (N, 2)
    bins_x, bins_y : int

    Returns
    -------
    np.ndarray of shape (bins_x, bins_y)
    """
    H, _, _ = np.histogram2d(
        data[:, 0], data[:, 1], bins=[bins_x, bins_y]
    )
    total = H.sum()
    if total == 0:
        return np.ones((bins_x, bins_y), dtype=np.float64) / (bins_x * bins_y)
    return H / total


def _triple_histogram_prob(
    data: np.ndarray,
    bins: int,
) -> np.ndarray:
    """3-D joint histogram probability (normalised).

    Parameters
    ----------
    data : ndarray of shape (N, 3)
    bins : int or list of 3 ints

    Returns
    -------
    np.ndarray of shape (bins, bins, bins)
    """
    if isinstance(bins, int):
        bins = [bins, bins, bins]
    H, _ = np.histogramdd(data, bins=bins)
    total = H.sum()
    if total == 0:
        b = bins[0]
        return np.ones((b, b, b), dtype=np.float64) / (b ** 3)
    return H / total


# ======================================================================
# Entropy functions
# ======================================================================

def shannon_entropy(
    x: np.ndarray,
    bins: int = 10,
) -> float:
    r"""Estimate the Shannon entropy H(X) from a 1-D series.

    .. math::

        H(X) = -\sum_{i} p(x_i) \log_2 p(x_i)

    Parameters
    ----------
    x : array-like of shape (N,)
    bins : int
        Number of histogram bins.

    Returns
    -------
    float
        Entropy in bits (base-2 logarithm).
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    if x.size < 2:
        return 0.0
    probs, _ = _histogram_prob(x, bins)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def conditional_entropy(
    x: np.ndarray,
    y: np.ndarray,
    bins: int = 10,
) -> float:
    r"""Estimate the conditional entropy H(X | Y).

    .. math::

        H(X|Y) = H(X,Y) - H(Y)

    Parameters
    ----------
    x, y : array-like of shape (N,)
    bins : int

    Returns
    -------
    float
        Conditional entropy in bits.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    if n < 2:
        return 0.0

    H_xy = shannon_entropy(np.column_stack([x, y]), bins=bins ** 2) if False else 0.0
    # Use joint entropy directly
    joint = _joint_histogram_prob(np.column_stack([x, y]), bins, bins)
    joint_pos = joint[joint > 0]
    H_xy = float(-np.sum(joint_pos * np.log2(joint_pos)))
    H_y = shannon_entropy(y, bins)
    return max(H_xy - H_y, 0.0)


# ======================================================================
# Transfer Entropy
# ======================================================================

def transfer_entropy(
    source: np.ndarray,
    target: np.ndarray,
    lag: int = 1,
    bins: int = 10,
) -> Dict[str, float]:
    r"""Compute transfer entropy from *source* → *target*.

    .. math::

        TE(S→T) = \sum p(t_{n+1}, t_n, s_n)
                  \log \frac{p(t_{n+1} | t_n, s_n)}{p(t_{n+1} | t_n)}

    This is equivalent to:

        TE(S→T) = H(T_{n+1} | T_n) - H(T_{n+1} | T_n, S_n)

    Parameters
    ----------
    source : array-like of shape (N,)
        Source time series S.
    target : array-like of shape (N,)
        Target time series T.
    lag : int, optional
        Embedding lag (default 1).  For lag *k*, the source at *t-k*
        is compared to the target at *t*.
    bins : int, optional
        Number of histogram bins per dimension (default 10).

    Returns
    -------
    dict with keys:
        - ``te`` : float — raw transfer entropy (bits)
        - ``te_normalized`` : float — normalised TE (effect size)
        - ``h_target_lagged`` : float — H(T_{n+1} | T_n)
        - ``h_target_joint`` : float — H(T_{n+1} | T_n, S_n)
    """
    S = np.asarray(source, dtype=np.float64).ravel()
    T = np.asarray(target, dtype=np.float64).ravel()
    N = min(len(S), len(T))
    S, T = S[:N], T[:N]

    if N - lag < 2 * bins:
        return {"te": 0.0, "te_normalized": 0.0,
                "h_target_lagged": 0.0, "h_target_joint": 0.0}

    t_future = T[lag:]          # T_{n+1}
    t_past   = T[:-lag]        # T_n
    s_past   = S[:-lag]        # S_n

    # --- H(T_{n+1} | T_n) = H(T_{n+1}, T_n) - H(T_n) ---
    joint_tt = _joint_histogram_prob(np.column_stack([t_future, t_past]), bins, bins)
    jp = joint_tt[joint_tt > 0]
    H_tt = float(-np.sum(jp * np.log2(jp)))

    p_t, _ = _histogram_prob(t_past, bins)
    p_t = p_t[p_t > 0]
    H_t = float(-np.sum(p_t * np.log2(p_t)))

    h_target_lagged = max(H_tt - H_t, 0.0)

    # --- H(T_{n+1} | T_n, S_n) via 3-D histogram ---
    triple = np.column_stack([t_future, t_past, s_past])
    p_3d = _triple_histogram_prob(triple, bins)
    p3 = p_3d[p_3d > 0]
    H_3d = float(-np.sum(p3 * np.log2(p3)))

    # H(T_n, S_n)
    joint_ts = _joint_histogram_prob(np.column_stack([t_past, s_past]), bins, bins)
    jts = joint_ts[joint_ts > 0]
    H_ts = float(-np.sum(jts * np.log2(jts)))

    h_target_joint = max(H_3d - H_ts, 0.0)

    te = h_target_lagged - h_target_joint
    te = max(te, 0.0)  # numerical guard

    # Normalise by H(T_{n+1} | T_n)
    if h_target_lagged > 1e-12:
        te_norm = te / h_target_lagged
    else:
        te_norm = 0.0

    return {
        "te": te,
        "te_normalized": te_norm,
        "h_target_lagged": h_target_lagged,
        "h_target_joint": h_target_joint,
    }


# ======================================================================
# Network analysis
# ======================================================================

def network_analysis(
    series_matrix: np.ndarray,
    names: Optional[List[str]] = None,
    lag: int = 1,
    bins: int = 10,
) -> Dict:
    """Compute a pairwise transfer-entropy matrix for N time series.

    Parameters
    ----------
    series_matrix : array-like of shape (N_series, T) or (T, N_series)
        If shape is (T, N), the matrix is transposed automatically.
    names : list of str or None
        Series identifiers.  If *None*, uses integer labels.
    lag : int
        Embedding lag for TE computation.
    bins : int
        Histogram bins.

    Returns
    -------
    dict with keys:
        - ``te_matrix``      : np.ndarray (N, N) — raw TE
        - ``te_norm_matrix"" : np.ndarray (N, N) — normalised TE
        - ``names""          : list of str
    """
    X = np.asarray(series_matrix, dtype=np.float64)

    # Auto-detect layout: if T > N, assume (T, N)
    if X.ndim != 2:
        raise ValueError("series_matrix must be 2-D")
    if X.shape[0] > X.shape[1]:
        X = X.T  # now (N, T)

    N_series, T_len = X.shape

    if names is None:
        names = [f"S{i}" for i in range(N_series)]
    if len(names) != N_series:
        raise ValueError("Length of names must equal number of series")

    te_raw = np.zeros((N_series, N_series))
    te_norm = np.zeros((N_series, N_series))

    for i in range(N_series):
        for j in range(N_series):
            if i == j:
                continue
            res = transfer_entropy(X[j], X[i], lag=lag, bins=bins)
            te_raw[i, j] = res["te"]
            te_norm[i, j] = res["te_normalized"]

    return {
        "te_matrix": te_raw,
        "te_norm_matrix": te_norm,
        "names": names,
    }


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)
    T = 2000

    # Build a simple information-flow chain: X → Y → Z
    x = np.random.randn(T)
    y = 0.5 * x[:-1] + 0.7 * np.random.randn(T - 1)
    z = 0.4 * y[:-1] + 0.8 * np.random.randn(T - 2)
    # Pad for equal length
    x = x[:T - 2]
    y = y[:T - 2]

    print("=" * 60)
    print("Transfer Entropy — Demo (chain: X → Y → Z)")
    print("=" * 60)

    pairs = [("X", x, "Y", y), ("Y", y, "Z", z),
             ("Z", z, "Y", y), ("X", x, "Z", z)]

    for s_name, s, t_name, t in pairs:
        res = transfer_entropy(s, t, lag=1, bins=8)
        print(
            f"  TE({s_name}→{t_name}): "
            f"raw={res['te']:.4f} bits  "
            f"normalised={res['te_normalized']:.4f}"
        )

    # Network analysis
    print(f"\n  Full TE matrix (rows=target, cols=source):")
    mat = np.column_stack([x, y, z])
    net = network_analysis(mat, names=["X", "Y", "Z"], lag=1, bins=8)
    print(f"  Raw TE:\n{np.array2string(net['te_matrix'], precision=4, suppress_small=True)}")
    print(f"  Normalised TE:\n{np.array2string(net['te_norm_matrix'], precision=4, suppress_small=True)}")
    print("=" * 60)
