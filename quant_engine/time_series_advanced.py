r"""
Advanced Time Series Analysis
===============================

A convenience wrapper around :mod:`statsmodels` for common econometric
time-series tasks, plus a pure-numpy CUSUM change-point detector.

Public API
-----------
- :func:`fit_arima`         — ARIMA(p,d,q) fitting & forecasting
- :func:`fit_sarima`        — SARIMA(p,d,q)(P,D,Q,s) fitting & forecasting
- :func:`fit_var`           — Vector Autoregression modelling
- :func:`granger_causality_test` — Granger causality F-test
- :func:`johansen_cointegration_test` — Johansen cointegration test
- :func:`cusum_change_detection`    — CUSUM structural-break detector

All functions accept :class:`pandas.Series` or :class:`pandas.DataFrame`
(where appropriate) and return plain-Python / numpy results.

References
----------
Hamilton, J.D. (1994). Time Series Analysis. Princeton University Press.
Johansen, S. (1991). Estimation and Hypothesis Testing of Cointegration
    Vectors in Gaussian Vector Autoregressive Models. Econometrica,
    59(6), 1551-1580.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ======================================================================
# ARIMA
# ======================================================================

def fit_arima(
    y: Union[pd.Series, np.ndarray, list],
    order: Tuple[int, int, int] = (1, 1, 1),
    forecast_steps: int = 10,
    alpha: float = 0.05,
    **kwargs: Any,
) -> Dict:
    """Fit an ARIMA model and produce point and interval forecasts.

    Parameters
    ----------
    y : pd.Series, ndarray, or list
        Univariate time series.
    order : tuple (p, d, q)
        ARIMA order.
    forecast_steps : int
        Number of periods to forecast.
    alpha : float
        Significance level for confidence intervals.
    **kwargs
        Extra arguments forwarded to
        :class:`statsmodels.tsa.arima.ARIMA`.

    Returns
    -------
    dict with keys:
        - ``model`` : fitted ARIMA result object
        - ``params`` : dict of parameter estimates
        - ``residuals`` : np.ndarray
        - ``aic``, ``bic`` : float
        - ``forecast_mean`` : np.ndarray
        - ``forecast_ci_lower`` : np.ndarray
        - ``forecast_ci_upper`` : np.ndarray
    """
    from statsmodels.tsa.arima.model import ARIMA

    y = _to_series(y, "y")
    if len(y) < max(order) * 3 + 10:
        raise ValueError(
            f"Insufficient data ({len(y)} obs) for ARIMA{order}"
        )

    model = ARIMA(y, order=order, **kwargs)
    result = model.fit()

    fc = result.get_forecast(steps=forecast_steps)
    ci = fc.conf_int(alpha=alpha)

    return {
        "model": result,
        "params": dict(zip(
            result.param_names, result.params.tolist()
        )),
        "residuals": result.resid.values,
        "aic": float(result.aic),
        "bic": float(result.bic),
        "forecast_mean": fc.predicted_mean.values,
        "forecast_ci_lower": ci.iloc[:, 0].values,
        "forecast_ci_upper": ci.iloc[:, 1].values,
    }


# ======================================================================
# SARIMA
# ======================================================================

def fit_sarima(
    y: Union[pd.Series, np.ndarray, list],
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12),
    forecast_steps: int = 10,
    alpha: float = 0.05,
    **kwargs: Any,
) -> Dict:
    """Fit a SARIMA model and produce forecasts.

    Parameters
    ----------
    y : pd.Series, ndarray, or list
        Univariate time series.
    order : tuple (p, d, q)
        Non-seasonal ARIMA order.
    seasonal_order : tuple (P, D, Q, s)
        Seasonal ARIMA order and periodicity.
    forecast_steps : int
        Number of periods to forecast.
    alpha : float
        Significance level for confidence intervals.
    **kwargs
        Extra arguments forwarded to
        :class:`statsmodels.tsa.arima.ARIMA`.

    Returns
    -------
    dict — same structure as :func:`fit_arima`.
    """
    from statsmodels.tsa.arima.model import ARIMA

    y = _to_series(y, "y")
    if len(y) < sum(order) * 3 + sum(seasonal_order[:3]) * 3 + 20:
        raise ValueError("Insufficient data for SARIMA")

    model = ARIMA(
        y, order=order, seasonal_order=seasonal_order, **kwargs
    )
    result = model.fit()

    fc = result.get_forecast(steps=forecast_steps)
    ci = fc.conf_int(alpha=alpha)

    return {
        "model": result,
        "params": dict(zip(
            result.param_names, result.params.tolist()
        )),
        "residuals": result.resid.values,
        "aic": float(result.aic),
        "bic": float(result.bic),
        "forecast_mean": fc.predicted_mean.values,
        "forecast_ci_lower": ci.iloc[:, 0].values,
        "forecast_ci_upper": ci.iloc[:, 1].values,
    }


# ======================================================================
# VAR
# ======================================================================

def fit_var(
    data: Union[pd.DataFrame, np.ndarray],
    maxlags: int = 4,
    ic: str = "aic",
    forecast_steps: int = 10,
) -> Dict:
    """Fit a Vector Autoregression (VAR) model.

    Parameters
    ----------
    data : pd.DataFrame or ndarray of shape (T, K)
        K-variate time series.
    maxlags : int
        Maximum lags to consider for lag-order selection.
    ic : str
        Information criterion ("aic", "bic", "hqic").
    forecast_steps : int
        Steps to forecast ahead.

    Returns
    -------
    dict with keys:
        - ``model`` : fitted VAR result object
        - ``selected_lag`` : int
        - ``params`` : pd.DataFrame of coefficient estimates
        - ``forecast`` : pd.DataFrame (forecast_steps × K)
        - ``irf`` : IRF object (for impulse-response analysis)
    """
    from statsmodels.tsa.api import VAR

    if isinstance(data, np.ndarray):
        data = pd.DataFrame(data, columns=[f"V{i}" for i in range(data.shape[1])])
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be pd.DataFrame or np.ndarray")

    model = VAR(data)
    result = model.fit(maxlags=maxlags, ic=ic)
    lag_order = result.k_ar

    fc = result.forecast(data.values[-lag_order:], steps=forecast_steps)
    fc_df = pd.DataFrame(
        fc, columns=data.columns,
        index=pd.RangeIndex(
            start=len(data), stop=len(data) + forecast_steps
        ),
    )
    irf = result.irf(periods=20)

    return {
        "model": result,
        "selected_lag": int(lag_order),
        "params": result.params,
        "forecast": fc_df,
        "irf": irf,
    }


# ======================================================================
# Granger Causality
# ======================================================================

def granger_causality_test(
    x: Union[pd.Series, np.ndarray, list],
    y: Union[pd.Series, np.ndarray, list],
    maxlag: int = 4,
    significance: float = 0.05,
) -> Dict[str, Any]:
    """Test whether *y* Granger-causes *x*.

    Parameters
    ----------
    x : pd.Series, ndarray, or list
        The variable being predicted (dependent).
    y : pd.Series, ndarray, or list
        The candidate causal variable (independent).
    maxlag : int
        Maximum lag order to test.
    significance : float
        Significance threshold.

    Returns
    -------
    dict with keys:
        - ``ssr_ftest`` : (F-stat, p-value, df_denom, df_num)
        - ``ssr_chi2test`` : (chi2-stat, p-value, df)
        - ``params_ftest`` : (F-stat, p-value, df_denom, df_num)
        - ``lrtest`` : (LR-stat, p-value, df)
        - ``lag_order`` : optimal lag chosen by F-test
        - ``is_significant`` : bool
    """
    from statsmodels.tsa.stattools import grangercausalitytests

    x = _to_series(x, "x")
    y = _to_series(y, "y")
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < maxlag * 3 + 10:
        raise ValueError("Insufficient data for Granger test")

    # statsmodels expects columns (target, candidate_cause)
    # grangercausalitytests returns {lag: (dict_of_tests, [results, ...])}
    test_result: Dict[str, Any] = grangercausalitytests(
        df[[df.columns[0], df.columns[1]]],
        maxlag=maxlag,
        verbose=False,
    )

    # Extract test dicts — handle both dict and tuple returns
    def _get_tests(entry):
        if isinstance(entry, tuple):
            return entry[0]  # first element is the test dict
        return entry

    # Find the best (lowest p-value) lag
    best_lag = 1
    best_p = 1.0
    best_fstat = 0.0
    for lag, entry in test_result.items():
        tests = _get_tests(entry)
        fssr = tests.get("ssr_ftest")
        if fssr is not None:
            pval = float(fssr[1])
            if pval < best_p:
                best_p = pval
                best_lag = int(lag)
                best_fstat = float(fssr[0])

    best_tests = _get_tests(test_result.get(best_lag, {}))
    return {
        "ssr_ftest": best_tests.get("ssr_ftest"),
        "ssr_chi2test": best_tests.get("ssr_chi2test"),
        "params_ftest": best_tests.get("params_ftest"),
        "lrtest": best_tests.get("lrtest"),
        "lag_order": best_lag,
        "f_statistic": best_fstat,
        "p_value": best_p,
        "is_significant": best_p < significance,
        "all_lags": {int(lag): _get_tests(entry) for lag, entry in test_result.items()},
    }


# ======================================================================
# Johansen Cointegration Test
# ======================================================================

def johansen_cointegration_test(
    data: Union[pd.DataFrame, np.ndarray],
    det_order: int = -1,
    k_ar_diff: int = 2,
    significance: float = 0.05,
) -> Dict:
    """Johansen cointegration test for multiple time series.

    Parameters
    ----------
    data : pd.DataFrame or ndarray of shape (T, K)
        K-variate time series (should be I(1)).
    det_order : int
        Deterministic trend: -1 = no constant/trend, 0 = constant,
        1 = trend.
    k_ar_diff : int
        Number of lags in the VAR (differenced form).
    significance : float
        Significance level for critical-value comparison.

    Returns
    -------
    dict with keys:
        - ``eigenvalues`` : np.ndarray (K,)
        - ``trace_stat`` : np.ndarray (K,)  — trace test statistics
        - ``trace_cv`` : np.ndarray (K, 3) — 90%, 95%, 99% CVs
        - ``maxeig_stat`` : np.ndarray (K,)
        - ``maxeig_cv`` : np.ndarray (K, 3)
        - ``r" : int — number of cointegrating vectors at *significance*
    """
    from statsmodels.tsa.vector_ar.vecm import coint_johansen

    if isinstance(data, np.ndarray):
        data = pd.DataFrame(data)
    data = data.dropna()
    K = data.shape[1]

    result = coint_johansen(data, det_order=det_order, k_ar_diff=k_ar_diff)

    trace_stat = result.lr1
    trace_cv = result.cvt  # (K, 3)  → 90%, 95%, 99%
    maxeig_stat = result.lr2
    maxeig_cv = result.cvm

    # Determine r (number of cointegrating vectors) via trace test
    sig_idx = {0.10: 0, 0.05: 1, 0.01: 2}.get(significance, 1)
    r = 0
    for i in range(K):
        if trace_stat[i] > trace_cv[i, sig_idx]:
            r = i + 1
        else:
            break

    return {
        "eigenvalues": result.eig,
        "eigenvectors": result.evec,
        "trace_stat": trace_stat,
        "trace_cv": trace_cv,
        "maxeig_stat": maxeig_stat,
        "maxeig_cv": maxeig_cv,
        "r": r,
        "significance_level": significance,
    }


# ======================================================================
# CUSUM Change-Point Detection
# ======================================================================

def cusum_change_detection(
    y: Union[pd.Series, np.ndarray, list],
    threshold: float = 1.0,
    drift: Optional[float] = None,
) -> Dict:
    """CUSUM change-point detection (pure numpy).

    Implements the cumulative-sum (CUSUM) algorithm for detecting
    structural breaks in the mean of a univariate series.

    The standardised CUSUM statistic is:

        S_t = max(0, S_{t-1} + (x_t - μ₀ - δ) / σ)

    where μ₀ is the in-control mean and δ is a drift parameter
    (typically ½ of the expected shift magnitude).

    Parameters
    ----------
    y : pd.Series, ndarray, or list
        Univariate time series.
    threshold : float
        Decision threshold h.  A changepoint is signalled when
        S_t exceeds h (default 1.0).
    drift : float or None
        Allowance / drift parameter δ.  If *None*, set to
        0.25 × standard deviation of *y*.

    Returns
    -------
    dict with keys:
        - ``cusum" : np.ndarray — the CUSUM statistic series
        - ``change_points" : list of int — indices where threshold
          was exceeded
        - ``threshold" : float
    """
    y = np.asarray(y, dtype=np.float64).ravel()
    if y.size < 5:
        return {
            "cusum": np.array([]),
            "change_points": [],
            "threshold": threshold,
        }

    mu0 = np.mean(y[: max(1, len(y) // 4)])  # initial in-control mean
    sigma = np.std(y, ddof=1)
    if sigma < 1e-12:
        sigma = 1.0
    if drift is None:
        drift = 0.25 * sigma

    T = len(y)
    S = np.zeros(T)
    change_points: List[int] = []

    for t in range(1, T):
        S[t] = max(0.0, S[t - 1] + (y[t] - mu0 - drift) / sigma)
        if S[t] > threshold:
            change_points.append(t)

    return {
        "cusum": S,
        "change_points": change_points,
        "threshold": threshold,
        "drift": drift,
        "in_control_mean": mu0,
    }


# ======================================================================
# Helpers
# ======================================================================

def _to_series(
    obj: Union[pd.Series, np.ndarray, list],
    name: str = "y",
) -> pd.Series:
    """Coerce to :class:`pandas.Series` with a single index."""
    if isinstance(obj, pd.Series):
        return obj.astype(float)
    if isinstance(obj, (np.ndarray, list)):
        return pd.Series(obj, dtype=float, name=name)
    raise TypeError(f"Cannot convert {type(obj)} to pd.Series")


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    np.random.seed(42)
    T = 300

    # --- ARIMA demo ---
    print("=" * 60)
    print("Advanced Time Series — Demo")
    print("=" * 60)

    # Simulate AR(2) + drift
    ar_coefs = np.array([0.6, -0.3])
    noise = np.random.randn(T) * 0.5
    y_arima = np.zeros(T)
    for t in range(2, T):
        y_arima[t] = (
            ar_coefs[0] * y_arima[t - 1]
            + ar_coefs[1] * y_arima[t - 2]
            + 0.02
            + noise[t]
        )

    res_arima = fit_arima(y_arima, order=(2, 0, 0), forecast_steps=12)
    print(f"\n  ARIMA(2,0,0) fit:")
    print(f"    AIC={res_arima['aic']:.2f}  BIC={res_arima['bic']:.2f}")
    print(f"    Params: {res_arima['params']}")
    print(f"    12-step forecast: {res_arima['forecast_mean'][:3].round(4)} ...")

    # --- VAR demo ---
    print(f"\n  VAR model:")
    y1 = np.zeros(T)
    y2 = np.zeros(T)
    for t in range(2, T):
        y1[t] = 0.5 * y1[t - 1] + 0.3 * y2[t - 1] + np.random.randn() * 0.3
        y2[t] = 0.2 * y1[t - 1] + 0.6 * y2[t - 1] + np.random.randn() * 0.3
    var_data = pd.DataFrame({"y1": y1, "y2": y2})
    res_var = fit_var(var_data, maxlags=4, forecast_steps=6)
    print(f"    Selected lag: {res_var['selected_lag']}")
    print(f"    Forecast (3 steps):\n{res_var['forecast'].head(3).round(4)}")

    # --- Granger demo ---
    print(f"\n  Granger causality (y2 → y1):")
    gc = granger_causality_test(y1, y2, maxlag=4)
    print(f"    F-stat={gc['f_statistic']:.4f}  p={gc['p_value']:.4f}  significant={gc['is_significant']}")

    # --- Johansen demo ---
    print(f"\n  Johansen cointegration test:")
    jc = johansen_cointegration_test(var_data, det_order=0, k_ar_diff=2)
    print(f"    Eigenvalues: {jc['eigenvalues'].round(4)}")
    print(f"    Trace stats: {jc['trace_stat'].round(4)}")
    print(f"    r (cointegrating vectors at 5%): {jc['r']}")

    # --- CUSUM demo ---
    print(f"\n  CUSUM change-point detection:")
    y_cusum = np.concatenate([
        np.random.normal(0, 1, 100),
        np.random.normal(3, 1, 100),
        np.random.normal(0, 1, 100),
    ])
    cusum_res = cusum_change_detection(y_cusum, threshold=3.0)
    print(f"    Change points detected at indices: {cusum_res['change_points'][:10]}")
    print("=" * 60)
