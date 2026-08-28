"""
Advanced Fuzzy Logic for Finance
===================================
Extends the base fuzzy_credit module with:

1. **ANFIS** (Adaptive Neuro-Fuzzy Inference System) - simplified
2. **Fuzzy AHP** - pairwise comparison with triangular fuzzy numbers
3. **Fuzzy TOPSIS** - multi-criteria decision making
4. **Fuzzy Portfolio Optimization** - portfolio weights under fuzzy returns
5. **Fuzzy Black-Scholes** - option pricing with fuzzy volatility

Mathematical foundations
-----------------------
1. Triangular Fuzzy Number (TFN):  A = (l, m, u)
   Membership:  mu(x) = max(0, min((x-l)/(m-l), (u-x)/(u-m)))

2. Fuzzy AHP:
   a_ij = (l_ij, m_ij, u_ij) on a 1-9 scale
   Weights from geometric mean of fuzzy comparisons.

3. Fuzzy TOPSIS:
   FPIS = fuzzy positive ideal solution
   FNIS = fuzzy negative ideal solution
   C_i = d(FNIS) / (d(FPIS) + d(FNIS))

4. ANFIS: 5-layer architecture combining neural learning
   with fuzzy inference.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Triangular Fuzzy Number
# ---------------------------------------------------------------------------

@dataclass
class TFN:
    """
    Triangular Fuzzy Number: A = (l, m, u).
    Represents a fuzzy quantity with lower bound l, most likely m, and upper bound u.
    """
    l: float  # lower bound (pessimistic)
    m: float  # mode (most likely)
    u: float  # upper bound (optimistic)

    def membership(self, x: float) -> float:
        """Membership degree of x in this TFN."""
        if x < self.l or x > self.u:
            return 0.0
        if x <= self.m:
            return (x - self.l) / (self.m - self.l) if self.m > self.l else 1.0
        return (self.u - x) / (self.u - self.m) if self.u > self.m else 1.0

    def defuzzify(self, method: str = "centroid") -> float:
        """Defuzzification to a crisp number."""
        if method == "centroid":
            return (self.l + self.m + self.u) / 3.0
        elif method == "mean":
            return self.m
        elif method == "optimistic":
            return self.u
        elif method == "pessimistic":
            return self.l
        return (self.l + self.m + self.u) / 3.0

    def alpha_cut(self, alpha: float) -> Tuple[float, float]:
        """Alpha-cut at level alpha: returns (lower, upper)."""
        alpha = max(0, min(1, alpha))
        lower = self.l + alpha * (self.m - self.l)
        upper = self.u - alpha * (self.u - self.m)
        return (lower, upper)

    # Arithmetic operations
    def __add__(self, other):
        if isinstance(other, TFN):
            return TFN(self.l + other.l, self.m + other.m, self.u + other.u)
        return TFN(self.l + other, self.m + other, self.u + other)

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        if isinstance(other, TFN):
            products = [self.l * other.l, self.l * other.u, self.u * other.l, self.u * other.u]
            return TFN(min(products), self.m * other.m, max(products))
        return TFN(self.l * other, self.m * other, self.u * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __sub__(self, other):
        if isinstance(other, TFN):
            return TFN(self.l - other.u, self.m - other.m, self.u - other.l)
        return TFN(self.l - other, self.m - other, self.u - other)

    def __truediv__(self, other):
        if isinstance(other, TFN):
            if other.l <= 0:
                raise ValueError("Division by TFN containing zero")
            products = [self.l / other.u, self.l / other.l, self.u / other.u, self.u / other.l]
            return TFN(min(products), self.m / other.m, max(products))
        return TFN(self.l / other, self.m / other, self.u / other)

    def distance(self, other: TFN) -> float:
        """Vertex distance between two TFNs."""
        return np.sqrt(
            ((self.l - other.l) ** 2 + (self.m - other.m) ** 2 + (self.u - other.u) ** 2) / 3
        )


# ---------------------------------------------------------------------------
# 1. Fuzzy AHP
# ---------------------------------------------------------------------------

class FuzzyAHP:
    """
    Fuzzy Analytic Hierarchy Process for multi-criteria weighting.

    Uses triangular fuzzy numbers for pairwise comparisons instead of
    crisp 1-9 Saaty scale values.

    Process:
    1. Construct fuzzy pairwise comparison matrix
    2. Compute geometric mean for each criterion
    3. Normalise to get fuzzy weights
    4. Defuzzify to get final weights
    """

    def __init__(self, criteria: List[str]):
        self.criteria = criteria
        self.n = len(criteria)
        self.matrix: Dict[Tuple[str, str], TFN] = {}

    def set_comparison(self, i: str, j: str, tfn: TFN) -> None:
        """Set the fuzzy comparison a_ij = (l, m, u)."""
        self.matrix[(i, j)] = tfn
        # Set the reciprocal
        if self.matrix.get((j, i)) is None:
            self.matrix[(j, i)] = TFN(1 / tfn.u, 1 / tfn.m, 1 / tfn.l)

    def set_comparison_crisp(self, i: str, j: str, value: float) -> None:
        """Set comparison using a crisp value on 1-9 scale with some fuzziness."""
        l = max(1 / 9, value - 0.5)
        u = min(9, value + 0.5)
        self.set_comparison(i, j, TFN(l, value, u))

    def compute_weights(self) -> Dict:
        """
        Compute fuzzy weights using the geometric mean method.

        Returns dict with: weights (defuzzified), fuzzy_weights, consistency_ratio.
        """
        n = self.n
        # Build full matrix
        full_matrix = np.zeros((n, n, 3))  # [i, j, (l, m, u)]
        idx_map = {name: i for i, name in enumerate(self.criteria)}

        for i_name in self.criteria:
            for j_name in self.criteria:
                i, j = idx_map[i_name], idx_map[j_name]
                if i == j:
                    full_matrix[i, j] = [1, 1, 1]
                elif (i_name, j_name) in self.matrix:
                    t = self.matrix[(i_name, j_name)]
                    full_matrix[i, j] = [t.l, t.m, t.u]
                else:
                    full_matrix[i, j] = [1, 1, 1]

        # Geometric mean for each row
        fuzzy_weights = []
        for i in range(n):
            geom_l, geom_m, geom_u = 1.0, 1.0, 1.0
            for j in range(n):
                geom_l *= full_matrix[i, j, 0]
                geom_m *= full_matrix[i, j, 1]
                geom_u *= full_matrix[i, j, 2]
            power = 1.0 / n
            fuzzy_weights.append(TFN(
                geom_l ** power, geom_m ** power, geom_u ** power
            ))

        # Normalise by sum
        sum_l = sum(w.l for w in fuzzy_weights)
        sum_m = sum(w.m for w in fuzzy_weights)
        sum_u = sum(w.u for w in fuzzy_weights)

        normalised = []
        for w in fuzzy_weights:
            normalised.append(TFN(w.l / sum_u, w.m / sum_m, w.u / sum_l))

        # Defuzzify
        weights = {self.criteria[i]: normalised[i].defuzzify() for i in range(n)}
        fuzzy_w = {self.criteria[i]: normalised[i] for i in range(n)}

        # Crisp consistency check (using m values)
        crisp_matrix = full_matrix[:, :, 1]
        eigenvalues = np.linalg.eigvals(crisp_matrix)
        max_eig = max(eigenvalues.real)
        CI = (max_eig - n) / (n - 1) if n > 1 else 0
        RI_table = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
        RI = RI_table.get(n, 1.49)
        CR = CI / RI if RI > 0 else 0

        return {
            "weights": weights,
            "fuzzy_weights": fuzzy_w,
            "consistency_ratio": CR,
            "consistent": CR < 0.1,
        }


# ---------------------------------------------------------------------------
# 2. Fuzzy TOPSIS
# ---------------------------------------------------------------------------

class FuzzyTOPSIS:
    """
    Fuzzy Technique for Order Preference by Similarity to Ideal Solution.

    Each alternative is evaluated against each criterion using a TFN.
    The method ranks alternatives by closeness to the ideal solution.
    """

    def __init__(self, alternatives: List[str], criteria: List[str], benefit_criteria: Optional[List[str]] = None):
        self.alternatives = alternatives
        self.criteria = criteria
        self.benefit = set(benefit_criteria) if benefit_criteria else set(criteria)
        self.ratings: Dict[Tuple[str, str], TFN] = {}
        self.weights: Dict[str, float] = {c: 1.0 / len(criteria) for c in criteria}

    def set_rating(self, alt: str, crit: str, tfn: TFN) -> None:
        self.ratings[(alt, crit)] = tfn

    def set_rating_crisp(self, alt: str, crit: str, value: float, fuzziness: float = 0.1) -> None:
        l = max(0, value - fuzziness * value)
        u = value + fuzziness * value
        self.ratings[(alt, crit)] = TFN(l, value, u)

    def set_weights(self, weights: Dict[str, float]) -> None:
        self.weights = weights

    def rank(self) -> Dict:
        """
        Compute TOPSIS ranking with fuzzy numbers.

        Returns dict with: rankings, closeness_scores, fpis, fnis.
        """
        n_alt = len(self.alternatives)
        n_crit = len(self.criteria)

        # Build decision matrix as defuzzified values
        D = np.zeros((n_alt, n_crit))
        for i, alt in enumerate(self.alternatives):
            for j, crit in enumerate(self.criteria):
                D[i, j] = self.ratings.get((alt, crit), TFN(0, 0, 0)).defuzzify()

        # Weighted normalised decision matrix
        w = np.array([self.weights.get(c, 0) for c in self.criteria])
        norm_factor = np.sqrt(np.sum(D ** 2, axis=0))
        norm_factor[norm_factor == 0] = 1
        V = D / norm_factor * w

        # FPIS and FNIS
        fpis = np.zeros(n_crit)
        fnis = np.zeros(n_crit)
        for j, crit in enumerate(self.criteria):
            if crit in self.benefit:
                fpis[j] = V[:, j].max()
                fnis[j] = V[:, j].min()
            else:
                fpis[j] = V[:, j].min()
                fnis[j] = V[:, j].max()

        # Distances
        d_plus = np.sqrt(np.sum((V - fpis) ** 2, axis=1))
        d_minus = np.sqrt(np.sum((V - fnis) ** 2, axis=1))

        # Closeness
        total_d = d_plus + d_minus
        C = np.where(total_d > 0, d_minus / total_d, 0)

        ranking_indices = np.argsort(-C)
        rankings = [self.alternatives[i] for i in ranking_indices]

        return {
            "rankings": rankings,
            "closeness_scores": {self.alternatives[i]: round(C[i], 4) for i in range(n_alt)},
            "distances_positive": {self.alternatives[i]: round(d_plus[i], 4) for i in range(n_alt)},
            "distances_negative": {self.alternatives[i]: round(d_minus[i], 4) for i in range(n_alt)},
        }


# ---------------------------------------------------------------------------
# 3. Fuzzy Portfolio Optimization
# ---------------------------------------------------------------------------

class FuzzyPortfolioOptimizer:
    """
    Portfolio optimization with fuzzy expected returns.

    Instead of a single expected return, each asset has a TFN (l, m, u).
    The optimization is performed at various alpha-cuts to produce
    a range of optimal allocations.
    """

    def __init__(
        self,
        fuzzy_returns: Dict[str, TFN],
        cov_matrix: np.ndarray,
        risk_free: float = 0.0,
    ):
        """
        fuzzy_returns : dict  - {asset_name: TFN(lower, expected, upper)}
        cov_matrix : array  - Covariance matrix of returns.
        risk_free : float  - Risk-free rate.
        """
        self.fuzzy_returns = fuzzy_returns
        self.cov = np.asarray(cov_matrix, dtype=float)
        self.rf = risk_free
        self.names = list(fuzzy_returns.keys())
        self.n = len(self.names)

    def optimize_at_alpha(
        self, alpha: float = 0.5, target_return: Optional[float] = None
    ) -> Dict:
        """
        Optimize at a given alpha-cut using mean-variance.

        At alpha-cut, each return becomes a crisp interval [l_alpha, u_alpha].
        We use the midpoint as the expected return.
        """
        alpha = max(0, min(1, alpha))
        mu = np.array([self.fuzzy_returns[n].alpha_cut(alpha) for n in self.names])
        expected = (mu[:, 0] + mu[:, 1]) / 2  # midpoint

        return self._markowitz(expected, target_return)

    def _markowitz(
        self, mu: np.ndarray, target_return: Optional[float] = None
    ) -> Dict:
        """Simple mean-variance optimisation using Lagrangian."""
        n = len(mu)
        Sigma = self.cov
        ones = np.ones(n)

        # Minimum variance portfolio
        try:
            Sigma_inv = np.linalg.inv(Sigma + 1e-8 * np.eye(n))
        except np.linalg.LinAlgError:
            Sigma_inv = np.linalg.pinv(Sigma)

        if target_return is not None:
            # Tangency-like with target return
            A = ones @ Sigma_inv @ ones
            B = ones @ Sigma_inv @ mu
            C = mu @ Sigma_inv @ mu
            D = A * C - B ** 2
            if abs(D) < 1e-12:
                w = np.ones(n) / n
            else:
                lam1 = (C * 1 - B * target_return) / D
                lam2 = (A * target_return - B * 1) / D
                w = Sigma_inv @ (lam1 * ones + lam2 * mu)
        else:
            # Min variance
            w = Sigma_inv @ ones / (ones @ Sigma_inv @ ones)

        # Normalise
        w = np.maximum(w, 0)  # long only
        if w.sum() > 0:
            w /= w.sum()

        port_return = w @ mu
        port_var = w @ Sigma @ w
        port_std = np.sqrt(max(port_var, 0))
        sharpe = (port_return - self.rf) / port_std if port_std > 0 else 0

        return {
            "weights": {self.names[i]: round(w[i], 6) for i in range(n)},
            "expected_return": port_return,
            "volatility": port_std,
            "sharpe_ratio": sharpe,
        }

    def alpha_cut_sweep(
        self, n_cuts: int = 5, target_return: Optional[float] = None
    ) -> Dict:
        """
        Sweep across alpha-cuts and collect optimal portfolios.

        Returns dict with: portfolios at each alpha, weight ranges per asset.
        """
        alphas = np.linspace(0.1, 0.9, n_cuts)
        results = {}
        all_weights = {name: [] for name in self.names}

        for a in alphas:
            opt = self.optimize_at_alpha(a, target_return)
            results[round(a, 2)] = opt
            for name in self.names:
                all_weights[name].append(opt["weights"][name])

        weight_ranges = {
            name: {"min": min(ws), "max": max(ws), "mean": np.mean(ws)}
            for name, ws in all_weights.items()
        }

        return {
            "alpha_portfolios": results,
            "weight_ranges": weight_ranges,
        }


# ---------------------------------------------------------------------------
# 4. Fuzzy Black-Scholes
# ---------------------------------------------------------------------------

class FuzzyBlackScholes:
    """
    Black-Scholes option pricing with fuzzy volatility.

    Instead of assuming a single precise sigma, the volatility is
    modelled as a TFN: sigma = (sigma_l, sigma_m, sigma_u).

    This produces an interval (or TFN) for the option price,
    honestly reflecting parameter uncertainty.
    """

    def __init__(
        self,
        S0: float = 100.0,
        K: float = 100.0,
        T: float = 1.0,
        r: float = 0.05,
        sigma_fuzzy: Optional[TFN] = None,
    ):
        self.S0 = S0
        self.K = K
        self.T = T
        self.r = r
        self.sigma_fuzzy = sigma_fuzzy or TFN(0.15, 0.20, 0.30)

    def _bs_call(self, sigma: float) -> float:
        """Black-Scholes call price for a given sigma."""
        from scipy.stats import norm
        if self.T <= 0 or sigma <= 0:
            return max(self.S0 - self.K, 0)
        d1 = (np.log(self.S0 / self.K) + (self.r + 0.5 * sigma ** 2) * self.T) / (sigma * np.sqrt(self.T))
        d2 = d1 - sigma * np.sqrt(self.T)
        return self.S0 * norm.cdf(d1) - self.K * np.exp(-self.r * self.T) * norm.cdf(d2)

    def fuzzy_call_price(self) -> TFN:
        """Compute the fuzzy call price by evaluating at l, m, u volatility."""
        s_l = self.sigma_fuzzy.l
        s_m = self.sigma_fuzzy.m
        s_u = self.sigma_fuzzy.u

        # For calls, price is NOT monotone in sigma for all ranges,
        # but for typical ATM/ITM options, it is increasing.
        price_l = self._bs_call(s_l)
        price_m = self._bs_call(s_m)
        price_u = self._bs_call(s_u)

        return TFN(min(price_l, price_m, price_u), price_m, max(price_l, price_m, price_u))

    def sensitivity_to_volatility(self, n_points: int = 50) -> Dict:
        """Show how option price varies across the volatility range."""
        sigmas = np.linspace(self.sigma_fuzzy.l, self.sigma_fuzzy.u, n_points)
        prices = np.array([self._bs_call(s) for s in sigmas])
        return {
            "volatilities": sigmas,
            "call_prices": prices,
            "price_range": prices.max() - prices.min(),
            "price_at_mid_vol": self._bs_call(self.sigma_fuzzy.m),
        }


# ---------------------------------------------------------------------------
# 5. Simplified ANFIS
# ---------------------------------------------------------------------------

class SimplifiedANFIS:
    """
    Simplified Adaptive Neuro-Fuzzy Inference System.

    Architecture:
    Layer 1: Fuzzification (triangular membership functions)
    Layer 2: Rule firing strength (product T-norm)
    Layer 3: Normalisation of firing strengths
    Layer 4: Consequent parameters (linear combination)
    Layer 5: Defuzzification (weighted sum)

    Training: least-squares for consequent parameters,
    grid-search for premise parameters (simplified).
    """

    def __init__(
        self,
        n_inputs: int,
        n_mf_per_input: int = 3,
    ):
        self.n_inputs = n_inputs
        self.n_mf = n_mf_per_input
        self.n_rules = n_mf_per_input ** n_inputs
        self.mf_params: List[np.ndarray] = []  # List of (n_mf, 3) arrays
        self.consequent_params: Optional[np.ndarray] = None
        self._init_mf()

    def _init_mf(self, input_range: Tuple[float, float] = (0, 1)) -> None:
        """Initialise membership functions evenly spaced."""
        self.mf_params = []
        lo, hi = input_range
        for _ in range(self.n_inputs):
            centres = np.linspace(lo, hi, self.n_mf)
            width = (hi - lo) / (self.n_mf - 1) * 0.8 if self.n_mf > 1 else (hi - lo)
            params = np.column_stack([centres - width / 2, centres, centres + width / 2])
            self.mf_params.append(params)

    def _membership(self, x: float, mf_idx: int, input_idx: int) -> float:
        """Triangular membership degree."""
        l, m, u = self.mf_params[input_idx][mf_idx]
        if x < l or x > u:
            return 0.0
        if x <= m:
            return (x - l) / (m - l) if m > l else 1.0
        return (u - x) / (u - m) if u > m else 1.0

    def _forward(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forward pass through layers 1-3.
        Returns normalised firing strengths.
        """
        n_samples = X.shape[0]
        firing = np.ones((n_samples, self.n_rules))

        for s in range(n_samples):
            w = np.ones(self.n_rules)
            for r in range(self.n_rules):
                # Decode rule index to MF indices
                indices = np.unravel_index(r, [self.n_mf] * self.n_inputs)
                for inp in range(self.n_inputs):
                    w[r] *= self._membership(X[s, inp], indices[inp], inp)
            firing[s] = w

        # Normalise (Layer 3)
        total = firing.sum(axis=1, keepdims=True)
        total[total == 0] = 1
        normalised = firing / total
        return firing, normalised

    def fit(self, X: np.ndarray, Y: np.ndarray) -> Dict:
        """
        Train the ANFIS model.

        Parameters
        ----------
        X : array (n, n_inputs)
        Y : array (n,)

        Uses least-squares for Layer 4 consequent parameters.
        """
        _, normalised = self._forward(X)
        # Design matrix: each column is a normalised rule weight
        # Consequent: f_i = p_i (constant per rule, simplified)
        try:
            self.consequent_params, _, _, _ = np.linalg.lstsq(normalised, Y, rcond=None)
        except np.linalg.LinAlgError:
            self.consequent_params = np.ones(self.n_rules)

        Y_pred = normalised @ self.consequent_params
        mse = np.mean((Y - Y_pred) ** 2)
        r2 = 1 - np.sum((Y - Y_pred) ** 2) / np.sum((Y - np.mean(Y)) ** 2) if np.var(Y) > 0 else 0

        return {"mse": mse, "r_squared": r2, "n_rules": self.n_rules}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using the trained ANFIS model."""
        if self.consequent_params is None:
            raise ValueError("Model not trained. Call fit() first.")
        _, normalised = self._forward(X)
        return normalised @ self.consequent_params

    def get_rules(self) -> List[Dict]:
        """
        Extract readable rules from the trained model.

        Returns list of dicts: {rule_idx, mf_indices, weight}.
        """
        rules = []
        mf_labels = ["Low", "Medium", "High"]
        for r in range(self.n_rules):
            indices = np.unravel_index(r, [self.n_mf] * self.n_inputs)
            weight = self.consequent_params[r] if self.consequent_params is not None else 0
            labels = [mf_labels[min(i, len(mf_labels) - 1)] for i in indices]
            rules.append({
                "rule_idx": r,
                "mf_indices": list(indices),
                "mf_labels": labels,
                "consequent_weight": round(weight, 4),
            })
        return rules
