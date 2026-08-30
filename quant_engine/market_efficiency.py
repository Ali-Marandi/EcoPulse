"""
Market Efficiency Testing Framework (EMH)
============================================
Implements statistical tests for the three forms of the Efficient
Market Hypothesis (Fama, 1970).

1. **Weak Form**: Returns are unpredictable from past prices.
   Tests: Runs test, Variance ratio test, Autocorrelation test, Lo-MacKinlay.

2. **Semi-Strong Form**: Prices fully reflect public information.
   Tests: Event study abnormal returns (simplified).

3. **Strong Form**: Even private information is reflected.
   (Not directly testable; we provide an insider trading metric.)

Mathematical foundations
-----------------------
Runs Test:
    Z = (R - E[R]) / sqrt(Var[R])
    E[R] = (2*n1*n2)/(n1+n2) + 1
    Var[R] = 2*n1*n2*(2*n1*n2 - n1 - n2) / ((n1+n2)^2 * (n1+n2-1))

Variance Ratio (Lo-MacKinlay, 1988):
    VR(q) = Var(R_q) / (q * Var(R_1))
    Under H0 (iid): VR(q) = 1
    Z = (VR(q) - 1) / sqrt(phi(q))

    phi(q) = 2*(2q-1)*(q-1) / (3*q*n)

Autocorrelation (Ljung-Box):
    Q = n*(n+2) * sum_{k=1}^m rho_k^2 / (n-k)
    Under H0: Q ~ chi^2(m)
"""
from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional


class WeakFormEMHTests:
    """
    Statistical tests for the weak form of the Efficient Market Hypothesis.

    Tests whether past returns contain predictive information about future
    returns. If the null is rejected, the market may not be weak-form efficient.
    """

    def __init__(self, returns: np.ndarray):
        """
        Parameters
        ----------
        returns : array (n,)  - Log returns or simple returns.
        """
        self.returns = np.asarray(returns, dtype=float)
        self.n = len(returns)

    # --- Runs Test ---

    def runs_test(self) -> Dict:
        """
        Wald-Wolfowitz runs test for randomness.

        H0: The sequence is random (no serial dependence).

        Returns
        -------
        dict with: n_runs, expected_runs, z_statistic, p_value, reject_h0.
        """
        signs = np.sign(self.returns)
        # Remove zeros
        signs = signs[signs != 0]
        if len(signs) < 10:
            return {"n_runs": 0, "z_statistic": 0, "p_value": 1, "reject_h0": False}

        n_pos = np.sum(signs > 0)
        n_neg = np.sum(signs < 0)
        n = n_pos + n_neg

        # Count runs
        runs = 1
        for i in range(1, len(signs)):
            if signs[i] != signs[i - 1]:
                runs += 1

        # Expected runs and variance
        E_R = (2 * n_pos * n_neg) / n + 1
        var_R = (2 * n_pos * n_neg * (2 * n_pos * n_neg - n)) / (n ** 2 * (n - 1))
        std_R = np.sqrt(var_R) if var_R > 0 else 1

        z = (runs - E_R) / std_R
        # Approximate p-value (two-tailed, using normal)
        p_val = 2 * (1 - 0.5 * (1 + np.tanh(abs(z) * 0.797885)))

        return {
            "n_runs": runs,
            "n_positive": int(n_pos),
            "n_negative": int(n_neg),
            "expected_runs": E_R,
            "z_statistic": z,
            "p_value": p_val,
            "reject_h0": p_val < 0.05,
        }

    # --- Variance Ratio Test (Lo-MacKinlay) ---

    def variance_ratio_test(self, q: int = 2) -> Dict:
        """
        Lo-MacKinlay (1988) variance ratio test.

        VR(q) = Var(R_q) / (q * Var(R_1))

        Under H0 (iid returns): VR(q) = 1.
        VR(q) > 1 suggests positive autocorrelation (momentum).
        VR(q) < 1 suggests negative autocorrelation (mean reversion).

        Parameters
        ----------
        q : int  - Aggregation period (e.g. 2 for 2-day returns).

        Returns dict with: vr, z_statistic, z_heteroskedastic, p_value, reject_h0.
        """
        n = self.n
        if n < 2 * q + 1:
            return {"vr": 1, "z_statistic": 0, "p_value": 1, "reject_h0": False}

        mu = np.mean(self.returns)
        # Variance of 1-period returns
        var_1 = np.sum((self.returns - mu) ** 2) / n
        # Variance of q-period returns
        n_q = n // q
        returns_q = np.array([np.sum(self.returns[i * q:(i + 1) * q]) for i in range(n_q)])
        mu_q = np.mean(returns_q)
        var_q = np.sum((returns_q - mu_q) ** 2) / n_q

        vr = var_q / (q * var_1) if var_1 > 0 else 1

        # Lo-MacKinlay test statistic (homoskedastic)
        phi_q = 2 * (2 * q - 1) * (q - 1) / (3 * q * n_q)
        z_hom = (vr - 1) / np.sqrt(phi_q) if phi_q > 0 else 0

        # Heteroskedastic-robust statistic
        m = q - 1
        theta = 0
        for j in range(1, q):
            delta_j = np.sum((self.returns[j:] - mu) * (self.returns[:-j] - mu)) / n
            theta += 2 * (q - j) ** 2 * delta_j / var_1
        phi_het = (3 * q ** 2 - 2 * q + 3) / (3 * q) + theta / (var_1 * q)
        z_het = (vr - 1) / np.sqrt(phi_het / n_q) if phi_het > 0 else 0

        p_val = 2 * (1 - 0.5 * (1 + np.tanh(abs(z_het) * 0.797885)))

        return {
            "vr": vr,
            "aggregation_period": q,
            "z_statistic_homoskedastic": z_hom,
            "z_statistic_heteroskedastic": z_het,
            "p_value": p_val,
            "reject_h0": p_val < 0.05,
            "evidence_of": "momentum" if vr > 1 else "mean_reversion" if vr < 1 else "random_walk",
        }

    # --- Autocorrelation (Ljung-Box) ---

    def autocorrelation_test(self, max_lags: int = 20) -> Dict:
        """
        Ljung-Box Q-test for serial correlation.

        Q = n*(n+2) * sum_{k=1}^m rho_k^2 / (n-k)
        Under H0 (no autocorrelation): Q ~ chi^2(m)

        Returns dict with: q_statistic, lags, autocorrelations, significant_lags.
        """
        n = self.n
        mu = np.mean(self.returns)
        var_0 = np.sum((self.returns - mu) ** 2) / n
        if var_0 <= 0:
            return {"q_statistic": 0, "p_value": 1, "reject_h0": False}

        m = min(max_lags, n // 2 - 1)
        acf = []
        q_stat = 0.0
        for k in range(1, m + 1):
            rho_k = np.sum((self.returns[k:] - mu) * (self.returns[:-k] - mu)) / (n * var_0)
            acf.append(rho_k)
            q_stat += rho_k ** 2 / (n - k)
        q_stat *= n * (n + 2)

        # Approximate p-value (chi-squared with m df)
        # Using Wilson-Hilferty approximation
        df = m
        if df > 0:
            x = q_stat / df
            if x > 0:
                z_approx = (x ** (1 / 3) - (1 - 2 / (9 * df))) / np.sqrt(2 / (9 * df))
            else:
                z_approx = -10
            p_val = 2 * (1 - 0.5 * (1 + np.tanh(abs(z_approx) * 0.797885)))
        else:
            p_val = 1

        sig_lags = [i + 1 for i, r in enumerate(acf) if abs(r) > 2 / np.sqrt(n)]

        return {
            "q_statistic": q_stat,
            "degrees_of_freedom": m,
            "p_value": p_val,
            "reject_h0": p_val < 0.05,
            "autocorrelations": {i + 1: round(r, 6) for i, r in enumerate(acf)},
            "significant_lags_95": sig_lags,
            "critical_value_95": 2 / np.sqrt(n),
        }

    # --- Combined Report ---

    def full_report(self, vr_periods: Optional[List[int]] = None) -> Dict:
        """
        Run all weak-form EMH tests and produce a summary report.
        """
        if vr_periods is None:
            vr_periods = [2, 4, 8]

        runs = self.runs_test()
        ac = self.autocorrelation_test()
        vr_results = {q: self.variance_ratio_test(q) for q in vr_periods}

        # Aggregate verdict
        rejections = []
        if runs["reject_h0"]:
            rejections.append("Runs test")
        if ac["reject_h0"]:
            rejections.append("Ljung-Box")
        for q, vr in vr_results.items():
            if vr["reject_h0"]:
                rejections.append(f"VR(q={q})")

        return {
            "runs_test": runs,
            "autocorrelation_test": ac,
            "variance_ratio_tests": vr_results,
            "summary": {
                "tests_rejecting_efficiency": rejections,
                "total_tests": 2 + len(vr_periods),
                "tests_rejecting": len(rejections),
                "market_appears_efficient": len(rejections) == 0,
                "conclusion": (
                    "Evidence supports weak-form efficiency"
                    if len(rejections) == 0
                    else "Evidence against weak-form efficiency"
                ),
            },
        }


class EventStudy:
    """
    Simplified event study for semi-strong form EMH testing.

    Measures abnormal returns (AR) and cumulative abnormal returns (CAR)
    around an event date.

    AR_t = R_t - E[R_t | market]
    CAR = sum of AR over the event window.

    Under EMH semi-strong form, CAR should not be significantly different
    from zero after the event announcement (no predictable drift).
    """

    def __init__(
        self,
        asset_returns: np.ndarray,
        market_returns: np.ndarray,
        event_date: int,
        estimation_window: tuple = (-250, -11),
        event_window: tuple = (-10, 10),
    ):
        self.asset = np.asarray(asset_returns, dtype=float)
        self.market = np.asarray(market_returns, dtype=float)
        self.event_date = event_date
        self.est_window = estimation_window
        self.evt_window = event_window

    def estimate_market_model(self) -> Dict:
        """
        Estimate the single-index model: R_i = alpha + beta * R_m + epsilon.
        Using the estimation window.
        """
        e_start = self.event_date + self.est_window[0]
        e_end = self.event_date + self.est_window[1]
        if e_start < 0 or e_end >= len(self.asset):
            return {"alpha": 0, "beta": 1, "r_squared": 0}

        R_a = self.asset[e_start:e_end]
        R_m = self.market[e_start:e_end]
        n = len(R_a)
        X = np.column_stack([R_m, np.ones(n)])
        beta_vec = np.linalg.lstsq(X, R_a, rcond=None)[0]
        beta, alpha = beta_vec[0], beta_vec[1]
        R_hat = X @ beta_vec
        SSR = np.sum((R_a - R_hat) ** 2)
        SST = np.sum((R_a - np.mean(R_a)) ** 2)
        r2 = 1 - SSR / SST if SST > 0 else 0

        return {"alpha": alpha, "beta": beta, "r_squared": r2, "residual_std": np.sqrt(SSR / (n - 2))}

    def compute_abnormal_returns(self) -> Dict:
        """
        Compute AR and CAR for the event window.
        """
        model = self.estimate_market_model()
        alpha, beta = model["alpha"], model["beta"]

        w_start = self.event_date + self.evt_window[0]
        w_end = self.event_date + self.evt_window[1] + 1
        w_start = max(0, w_start)
        w_end = min(len(self.asset), w_end)

        R_a = self.asset[w_start:w_end]
        R_m = self.market[w_start:w_end]
        expected = alpha + beta * R_m
        AR = R_a - expected
        CAR = np.cumsum(AR)

        days = np.arange(self.evt_window[0], self.evt_window[0] + len(AR))

        return {
            "abnormal_returns": AR,
            "cumulative_abnormal_returns": CAR,
            "event_days": days,
            "total_CAR": CAR[-1] if len(CAR) > 0 else 0,
            "model_params": model,
        }
