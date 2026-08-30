"""
Causal Inference for Financial Applications
============================================
Implements causal inference frameworks relevant to finance:
- DAG-based causal identification (do-calculus)
- Double/Debiased Machine Learning (DML)
- Instrumental Variables estimation
- Difference-in-Differences
- Propensity Score Matching

Mathematical foundations
-----------------------
1. **do-calculus** (Pearl):  P(Y | do(X=x)) removes confounding by
   surgically setting X, cutting incoming arrows.

2. **Double ML** (Chernozhukov et al., 2018):
   theta_hat = (1/n) sum_i * residual_Y_i * residual_X_i
   where residuals come from cross-fitted ML models.

3. **IV / 2SLS**:  X_hat = Z * (Z'Z)^-1 * Z'X
   then  Y = X_hat * beta_IV.

4. **DID**:  ATT = E[Y_post - Y_pre | treated] - E[Y_post - Y_pre | control]

5. **PSM**:  propensity = P(T=1 | covariates), then match on propensity.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. DAG-Based Causal Identification
# ---------------------------------------------------------------------------

@dataclass
class DAGNode:
    """A node in a Directed Acyclic Graph."""
    name: str
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)


class CausalDAG:
    """
    Directed Acyclic Graph for causal reasoning.

    Supports:
    - Backdoor criterion checking
    - Front-door criterion checking
    - Adjustment set identification
    - Simple do-calculus queries (backdoor adjustment)

    Example
    -------
    >>> dag = CausalDAG()
    >>> dag.add_edges([('rate_hike', 'inflation'), ('rate_hike', 'growth'),
    ...                 ('oil_shock', 'inflation'), ('oil_shock', 'growth')])
    >>> dag.find_adjustment_set('rate_hike', 'growth')
    """

    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
        self.edges: List[Tuple[str, str]] = []

    def add_node(self, name: str) -> None:
        if name not in self.nodes:
            self.nodes[name] = DAGNode(name=name)

    def add_edge(self, parent: str, child: str) -> None:
        self.add_node(parent)
        self.add_node(child)
        self.edges.append((parent, child))
        if child not in self.nodes[parent].children:
            self.nodes[parent].children.append(child)
        if parent not in self.nodes[child].parents:
            self.nodes[child].parents.append(parent)

    def add_edges(self, edges: List[Tuple[str, str]]) -> None:
        for p, c in edges:
            self.add_edge(p, c)

    def _descendants(self, node: str) -> set:
        """Return all descendants of a node."""
        visited = set()
        stack = [node]
        while stack:
            n = stack.pop()
            for c in self.nodes.get(n, DAGNode(n)).children:
                if c not in visited:
                    visited.add(c)
                    stack.append(c)
        return visited

    def _ancestors(self, node: str) -> set:
        """Return all ancestors of a node."""
        visited = set()
        stack = [node]
        while stack:
            n = stack.pop()
            for p in self.nodes.get(n, DAGNode(n)).parents:
                if p not in visited:
                    visited.add(p)
                    stack.append(p)
        return visited

    def _all_paths(self, start: str, end: str) -> List[List[str]]:
        """Find all directed paths from start to end."""
        results = []
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if node == end:
                results.append(path)
                continue
            for child in self.nodes.get(node, DAGNode(node)).children:
                if child not in path:
                    stack.append((child, path + [child]))
        return results

    def is_d_separated(self, X: str, Y: str, Z: set) -> bool:
        """
        Check if X and Y are d-separated given Z (simplified).

        In a simplified version, we check whether all paths from X to Y
        are blocked by Z. A path is blocked if:
        - A non-collider on the path is in Z, or
        - A collider on the path has no descendant in Z.

        This is a simplified implementation for moderate-sized DAGs.
        """
        paths = self._all_paths(X, Y)
        if not paths:
            return True

        Z_set = set(Z)
        for path in paths:
            path_blocked = False
            for i in range(1, len(path) - 1):
                node = path[i]
                parent_in_path = path[i - 1]
                child_in_path = path[i + 1]

                # Check if node is a collider (both arrows in)
                parents_of_node = set(self.nodes.get(node, DAGNode(node)).parents)
                is_collider = parent_in_path in parents_of_node and child_in_path in parents_of_node

                if is_collider:
                    # Collider blocks unless a descendant is in Z
                    desc = self._descendants(node)
                    if not (node in Z_set or desc & Z_set):
                        path_blocked = True
                        break
                else:
                    # Non-collider blocks if in Z
                    if node in Z_set:
                        path_blocked = True
                        break

            if not path_blocked:
                return False  # At least one active path

        return True  # All paths blocked

    def find_adjustment_set(self, treatment: str, outcome: str) -> Dict:
        """
        Find a valid adjustment set for the backdoor criterion.

        The backdoor criterion says a set Z satisfies:
        1. No node in Z is a descendant of treatment.
        2. Z blocks every backdoor path from treatment to outcome.

        Returns
        -------
        dict with: adjustment_set, is_valid, backdoor_paths, all_variables.
        """
        descendants = self._descendants(treatment)
        all_vars = set(self.nodes.keys()) - {treatment, outcome}
        non_descendants = all_vars - descendants

        # Try all subsets of non-descendants (for small graphs)
        best_set = None
        for size in range(len(non_descendants) + 1):
            from itertools import combinations
            for combo in combinations(sorted(non_descendants), size):
                Z = set(combo)
                if self.is_d_separated(treatment, outcome, Z | {treatment, outcome}):
                    # Verify no descendant of treatment
                    if not (Z & descendants):
                        best_set = Z
                        break
            if best_set is not None:
                break

        # Find backdoor paths (paths with an arrow into treatment)
        all_paths = self._all_paths(treatment, outcome)
        backdoor_paths = []
        for path in all_paths:
            # A backdoor path starts with an arrow INTO treatment
            if len(path) >= 2:
                first_parent = path[1] if path[0] == treatment else None
                if first_parent and treatment in self.nodes.get(first_parent, DAGNode(first_parent)).children:
                    backdoor_paths.append(path)

        return {
            "adjustment_set": sorted(best_set) if best_set else [],
            "is_valid": best_set is not None,
            "backdoor_paths": backdoor_paths,
            "all_variables": sorted(self.nodes.keys()),
        }

    def backdoor_adjustment(
        self, treatment: str, outcome: str,
        data: Dict[str, np.ndarray], adjustment_set: List[str]
    ) -> Dict:
        """
        Compute the causal effect using backdoor adjustment (linear regression).

        For each level of the adjustment set, we regress Y on X.
        This is a simplified parametric version.

        Parameters
        ----------
        data : dict mapping variable names to 1D arrays of equal length.
        adjustment_set : list of variable names to condition on.

        Returns
        -------
        dict with: causal_effect, std_error, adjusted_r_squared.
        """
        X = data[treatment]
        Y = data[outcome]
        n = len(X)

        # Build design matrix: [X, Z1, Z2, ...]
        cols = [X]
        col_names = [treatment]
        for z in adjustment_set:
            cols.append(data[z])
            col_names.append(z)
        cols.append(np.ones(n))
        col_names.append("intercept")
        A = np.column_stack(cols)

        # OLS: beta = (A'A)^-1 A'Y
        try:
            beta = np.linalg.lstsq(A, Y, rcond=None)[0]
            Y_hat = A @ beta
            resid = Y - Y_hat
            k = len(col_names)
            sse = np.sum(resid ** 2)
            sst = np.sum((Y - np.mean(Y)) ** 2)
            r2 = 1 - sse / sst if sst > 0 else 0
            adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k) if n > k else 0
            se = np.sqrt(sse / (n - k)) if n > k else float("inf")
        except np.linalg.LinAlgError:
            return {"causal_effect": float("nan"), "std_error": float("nan"), "adjusted_r_squared": 0}

        return {
            "causal_effect": beta[0],
            "std_error": se / np.sqrt(np.sum((X - np.mean(X)) ** 2)) if np.sum((X - np.mean(X)) ** 2) > 0 else float("inf"),
            "adjusted_r_squared": adj_r2,
            "coefficients": dict(zip(col_names, beta.tolist())),
        }


# ---------------------------------------------------------------------------
# 2. Double / Debiased Machine Learning (DML)
# ---------------------------------------------------------------------------

class DoubleML:
    """
    Double/Debiased Machine Learning for causal effect estimation.

    The target parameter is theta such that:
        Y - g(X) = theta * (T - m(X)) + epsilon

    where g(X) = E[Y | X] and m(X) = E[T | X].

    Steps:
    1. Cross-fit: split data into K folds.
    2. On each fold, train g_hat and m_hat on the other folds.
    3. Compute residuals: Y_tilde = Y - g_hat(X),  T_tilde = T - m_hat(X).
    4. Estimate theta = (T_tilde' * T_tilde)^-1 * T_tilde' * Y_tilde.

    This uses numpy-based ridge regression as the "ML" learner for
    portability. In production, replace with any ML model.
    """

    def __init__(self, n_folds: int = 5, ridge_alpha: float = 1.0):
        self.n_folds = n_folds
        self.ridge_alpha = ridge_alpha

    @staticmethod
    def _ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
        """Ridge regression: beta = (X'X + alpha*I)^-1 X'y."""
        n, k = X.shape
        A = X.T @ X + alpha * np.eye(k)
        b = X.T @ y
        try:
            return np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(A, b, rcond=None)[0]

    def estimate(
        self, Y: np.ndarray, T: np.ndarray, X: np.ndarray
    ) -> Dict:
        """
        Estimate the Average Treatment Effect (ATE) using Double ML.

        Parameters
        ----------
        Y : array (n,)  - Outcome variable.
        T : array (n,)  - Treatment variable (can be continuous).
        X : array (n, p) - Confounders / control variables.

        Returns
        -------
        dict with: ate, standard_error, y_residuals, t_residuals.
        """
        n = len(Y)
        indices = np.arange(n)
        np.random.shuffle(indices)
        fold_size = n // self.n_folds

        Y_tilde = np.zeros(n)
        T_tilde = np.zeros(n)

        for k in range(self.n_folds):
            test_start = k * fold_size
            test_end = test_start + fold_size if k < self.n_folds - 1 else n
            test_idx = indices[test_start:test_end]
            train_idx = np.concatenate([indices[:test_start], indices[test_end:]])

            X_train, X_test = X[train_idx], X[test_idx]
            Y_train = Y[train_idx]
            T_train = T[train_idx]

            # Add intercept
            X_train_c = np.column_stack([X_train, np.ones(len(X_train))])
            X_test_c = np.column_stack([X_test, np.ones(len(X_test))])

            # Learn g_hat: E[Y | X]
            beta_y = self._ridge_fit(X_train_c, Y_train, self.ridge_alpha)
            g_hat = X_test_c @ beta_y

            # Learn m_hat: E[T | X]
            beta_t = self._ridge_fit(X_train_c, T_train, self.ridge_alpha)
            m_hat = X_test_c @ beta_t

            Y_tilde[test_idx] = Y[test_idx] - g_hat
            T_tilde[test_idx] = T[test_idx] - m_hat

        # Orthogonal moment: theta = (T_tilde' T_tilde)^-1 T_tilde' Y_tilde
        denom = T_tilde @ T_tilde
        if abs(denom) < 1e-12:
            return {"ate": float("nan"), "standard_error": float("nan"), "y_residuals": Y_tilde, "t_residuals": T_tilde}

        theta = (T_tilde @ Y_tilde) / denom

        # Standard error via residual variance
        eps = Y_tilde - theta * T_tilde
        sigma2 = np.sum(eps ** 2) / (n - 1)
        se = np.sqrt(sigma2) / np.sqrt(denom)

        return {
            "ate": theta,
            "standard_error": se,
            "t_statistic": theta / se if se > 0 else float("nan"),
            "p_value": 2 * (1 - 0.5 * (1 + np.sign(theta / se if se > 0 else 0) * np.tanh(abs(theta / se if se > 0 else 0) * 0.797885))),
            "y_residuals": Y_tilde,
            "t_residuals": T_tilde,
        }


# ---------------------------------------------------------------------------
# 3. Instrumental Variables (2SLS)
# ---------------------------------------------------------------------------

class InstrumentalVariables:
    """
    Two-Stage Least Squares (2SLS) estimation.

    Stage 1:  X_hat = Z * (Z'Z)^-1 * Z'X
    Stage 2:  Y = X_hat * beta_IV

    Conditions for a valid instrument Z:
    1. Relevance:  Cov(Z, X) != 0
    2. Exogeneity:  Cov(Z, epsilon) = 0
    """

    def __init__(self):
        self.first_stage_f_stat: float = 0.0
        self.beta_iv: Optional[np.ndarray] = None
        self.first_stage_r2: float = 0.0

    def estimate(
        self, Y: np.ndarray, X: np.ndarray, Z: np.ndarray
    ) -> Dict:
        """
        Estimate causal effect using 2SLS.

        Parameters
        ----------
        Y : array (n,)    - Outcome.
        X : array (n,)    - Endogenous treatment.
        Z : array (n, k)  - Instrument(s). Add a constant column if needed.

        Returns
        -------
        dict with: iv_estimate, standard_error, first_stage_f_stat,
                   first_stage_r2, weak_instrument_warning.
        """
        n = len(Y)

        # Ensure 2D
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if Z.ndim == 1:
            Z = Z.reshape(-1, 1)

        # Add intercept to Z if not present
        Z_aug = np.column_stack([Z, np.ones(n)])

        # Stage 1: regress X on Z
        try:
            beta_1 = np.linalg.lstsq(Z_aug, X, rcond=None)[0]
        except np.linalg.LinAlgError:
            return {"iv_estimate": float("nan"), "standard_error": float("nan"),
                    "first_stage_f_stat": 0, "weak_instrument_warning": True}

        X_hat = Z_aug @ beta_1

        # First-stage F-statistic
        X_mean = X.mean(axis=0)
        TSS = np.sum((X - X_mean) ** 2)
        RSS = np.sum((X - X_hat) ** 2)
        self.first_stage_r2 = 1 - RSS / TSS if TSS > 0 else 0
        k_instruments = Z_aug.shape[1]
        F_stat = ((TSS - RSS) / (k_instruments - 1)) / (RSS / (n - k_instruments)) if n > k_instruments else 0
        self.first_stage_f_stat = F_stat

        # Stage 2: regress Y on X_hat
        X_hat_aug = np.column_stack([X_hat, np.ones(n)])
        try:
            beta_2 = np.linalg.lstsq(X_hat_aug, Y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return {"iv_estimate": float("nan"), "standard_error": float("nan"),
                    "first_stage_f_stat": F_stat, "weak_instrument_warning": True}

        self.beta_iv = beta_2
        Y_hat = X_hat_aug @ beta_2
        resid = Y - Y_hat
        k_params = X_hat_aug.shape[1]
        sigma2 = np.sum(resid ** 2) / (n - k_params)
        se = np.sqrt(sigma2) / np.sqrt(np.sum((X_hat - X_hat.mean(axis=0)) ** 2)) if np.sum((X_hat - X_hat.mean(axis=0)) ** 2) > 0 else float("inf")

        return {
            "iv_estimate": beta_2[0],
            "standard_error": se,
            "t_statistic": beta_2[0] / se if se > 0 else float("nan"),
            "first_stage_f_stat": F_stat,
            "first_stage_r2": self.first_stage_r2,
            "weak_instrument_warning": F_stat < 10,
        }


# ---------------------------------------------------------------------------
# 4. Difference-in-Differences (DID)
# ---------------------------------------------------------------------------

class DifferenceInDifferences:
    """
    Difference-in-Differences estimator for causal effects.

    ATT = E[(Y_post - Y_pre) | treated] - E[(Y_post - Y_pre) | control]

    Parallel trends assumption: in the absence of treatment, the treated
    and control groups would have followed the same trend.
    """

    def __init__(self):
        pass

    def estimate(
        self,
        Y_pre_treated: np.ndarray,
        Y_post_treated: np.ndarray,
        Y_pre_control: np.ndarray,
        Y_post_control: np.ndarray,
    ) -> Dict:
        """
        Compute the DID estimate.

        Returns
        -------
        dict with: att, standard_error, t_statistic, p_value,
                   mean_diff_treated, mean_diff_control, n_treated, n_control.
        """
        diff_treated = Y_post_treated - Y_pre_treated
        diff_control = Y_post_control - Y_pre_control

        att = np.mean(diff_treated) - np.mean(diff_control)

        # Standard error using pooled variance
        n_t = len(diff_treated)
        n_c = len(diff_control)
        var_t = np.var(diff_treated, ddof=1)
        var_c = np.var(diff_control, ddof=1)
        se = np.sqrt(var_t / n_t + var_c / n_c)

        t_stat = att / se if se > 0 else float("nan")
        # Approximate p-value using normal
        p_val = 2 * (1 - 0.5 * (1 + np.sign(t_stat) * np.tanh(abs(t_stat) * 0.797885)))

        return {
            "att": att,
            "standard_error": se,
            "t_statistic": t_stat,
            "p_value": p_val,
            "mean_diff_treated": np.mean(diff_treated),
            "mean_diff_control": np.mean(diff_control),
            "n_treated": n_t,
            "n_control": n_c,
        }

    def parallel_trends_test(
        self,
        Y_pre_treated: np.ndarray,
        Y_pre_control: np.ndarray,
    ) -> Dict:
        """
        Test the parallel trends assumption using a pre-treatment period.

        If the pre-treatment trends are significantly different, the DID
        estimate may be biased.

        Returns dict with: mean_pre_treated, mean_pre_control, difference, t_stat, p_value.
        """
        n_t = len(Y_pre_treated)
        n_c = len(Y_pre_control)
        diff = np.mean(Y_pre_treated) - np.mean(Y_pre_control)
        se = np.sqrt(np.var(Y_pre_treated, ddof=1) / n_t + np.var(Y_pre_control, ddof=1) / n_c)
        t_stat = diff / se if se > 0 else 0
        return {
            "mean_pre_treated": np.mean(Y_pre_treated),
            "mean_pre_control": np.mean(Y_pre_control),
            "pre_treatment_difference": diff,
            "t_statistic": t_stat,
            "p_value": 2 * (1 - 0.5 * (1 + np.sign(t_stat) * np.tanh(abs(t_stat) * 0.797885))),
            "parallel_trends_plausible": abs(t_stat) < 1.96,
        }


# ---------------------------------------------------------------------------
# 5. Propensity Score Matching
# ---------------------------------------------------------------------------

class PropensityScoreMatching:
    """
    Propensity Score Matching for estimating treatment effects.

    The propensity score is e(X) = P(T=1 | X).
    After estimating e(X), we match treated and control units with
    similar scores and compute the average treatment effect.
    """

    def __init__(self, ridge_alpha: float = 1.0, caliper: float = 0.2):
        """
        Parameters
        ----------
        ridge_alpha : float  - Regularisation for logistic regression.
        caliper : float  - Maximum propensity score distance for matching.
        """
        self.ridge_alpha = ridge_alpha
        self.caliper = caliper

    def _estimate_propensity(self, T: np.ndarray, X: np.ndarray) -> np.ndarray:
        """Estimate propensity scores using a simple logistic-like ridge model."""
        # Use linear probability model with ridge for simplicity
        n = len(T)
        X_aug = np.column_stack([X, np.ones(n)])
        k = X_aug.shape[1]
        beta = np.linalg.lstsq(X_aug.T @ X_aug + self.ridge_alpha * np.eye(k), X_aug.T @ T, rcond=None)[0]
        scores = X_aug @ beta
        return np.clip(scores, 0.01, 0.99)

    def match_and_estimate(
        self, Y: np.ndarray, T: np.ndarray, X: np.ndarray
    ) -> Dict:
        """
        Match treated and control units, then estimate ATT.

        Parameters
        ----------
        Y : array (n,)    - Outcome.
        T : array (n,)    - Treatment indicator (0 or 1).
        X : array (n, p) - Covariates.

        Returns
        -------
        dict with: att, standard_error, n_matched, propensity_scores, etc.
        """
        propensity = self._estimate_propensity(T, X)
        treated_idx = np.where(T == 1)[0]
        control_idx = np.where(T == 0)[0]

        matched_outcomes = []
        matched_controls = []
        matched_treated = []
        used_controls = set()

        for ti in treated_idx:
            best_ci = None
            best_dist = float("inf")
            for ci in control_idx:
                if ci in used_controls:
                    continue
                dist = abs(propensity[ti] - propensity[ci])
                if dist < best_dist:
                    best_dist = dist
                    best_ci = ci
            if best_ci is not None and best_dist <= self.caliper:
                matched_treated.append(Y[ti])
                matched_controls.append(Y[best_ci])
                used_controls.add(best_ci)

        if not matched_treated:
            return {
                "att": float("nan"),
                "standard_error": float("nan"),
                "n_matched": 0,
                "n_treated": len(treated_idx),
                "n_control": len(control_idx),
                "propensity_scores": propensity,
            }

        matched_treated = np.array(matched_treated)
        matched_controls = np.array(matched_controls)
        pair_diffs = matched_treated - matched_controls
        att = np.mean(pair_diffs)
        se = np.std(pair_diffs, ddof=1) / np.sqrt(len(pair_diffs))

        return {
            "att": att,
            "standard_error": se,
            "t_statistic": att / se if se > 0 else float("nan"),
            "n_matched": len(matched_treated),
            "n_treated": len(treated_idx),
            "n_control": len(control_idx),
            "propensity_scores": propensity,
            "mean_propensity_treated": np.mean(propensity[T == 1]),
            "mean_propensity_control": np.mean(propensity[T == 0]),
        }
