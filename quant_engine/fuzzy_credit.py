r"""
Fuzzy Inference System for Credit Scoring
==========================================

Implements a Mamdani-style fuzzy inference system (FIS) that maps four
economic/demographic input variables to a credit-score output:

Inputs
-------
- **income**          : Annual income (USD thousands)
- **debt_ratio**      : Debt-to-income ratio (%)
- **payment_history** : On-time payment percentage (0 – 100)
- **employment_years** : Years of continuous employment

Output
-------
- **credit_score**     : Composite score in [0, 100]

The system uses triangular and trapezoidal membership functions,
a hand-crafted rule base (24 rules), min-max composition, and
centroid defuzzification.

Pure numpy implementation — no external fuzzy-logic library required.

References
----------
Mamdani, E.H. & Assilian, S. (1975). An Experiment in Linguistic
    Synthesis with a Fuzzy Logic Controller. Int. J. Man-Machine
    Studies, 7(1), 1-13.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ======================================================================
# Membership Functions
# ======================================================================

def trimf(x: float | np.ndarray, abc: Tuple[float, float, float]) -> float | np.ndarray:
    """Triangular membership function.

    Parameters
    ----------
    x : float or ndarray
        Input value(s).
    abc : tuple of 3 floats
        (a, b, c) — left foot, peak, right foot.

    Returns
    -------
    float or ndarray
        Membership degree(s) in [0, 1].
    """
    a, b, c = abc
    x = np.asarray(x, dtype=np.float64)
    y = np.zeros_like(x)
    # Left ramp
    mask1 = (x >= a) & (x < b)
    y = np.where(mask1, (x - a) / (b - a + 1e-12), y)
    # Right ramp
    mask2 = (x >= b) & (x <= c)
    y = np.where(mask2, (c - x) / (c - b + 1e-12), y)
    # Peak
    y = np.where(x == b, 1.0, y)
    return float(y) if y.ndim == 0 else y


def trapmf(
    x: float | np.ndarray,
    abcd: Tuple[float, float, float, float],
) -> float | np.ndarray:
    """Trapezoidal membership function.

    Parameters
    ----------
    x : float or ndarray
    abcd : tuple of 4 floats
        (a, b, c, d) — left foot, left shoulder, right shoulder,
        right foot.
    """
    a, b, c, d = abcd
    x = np.asarray(x, dtype=np.float64)
    y = np.zeros_like(x)
    y = np.where((x >= a) & (x < b), (x - a) / (b - a + 1e-12), y)
    y = np.where((x >= b) & (x <= c), 1.0, y)
    y = np.where((x > c) & (x <= d), (d - x) / (d - c + 1e-12), y)
    return float(y) if y.ndim == 0 else y


def centroid_defuzzify(
    x: np.ndarray,
    y: np.ndarray,
    n_points: int = 200,
) -> float:
    """Centroid (centre-of-gravity) defuzzification.

    Computes the centroid of the area under the aggregate output
    membership function using the discrete approximation:

        c = Σ x_i · μ(x_i) / Σ μ(x_i)

    Parameters
    ----------
    x : np.ndarray of shape (M,)
        Discrete universe of discourse.
    y : np.ndarray of shape (M,)
        Aggregate membership values.
    n_points : int
        Number of integration points (used only if ``x`` is not
        already fine enough).

    Returns
    -------
    float
        The defuzzified (crisp) output value.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    # If needed, resample onto a finer grid
    if len(x) < n_points:
        x_fine = np.linspace(x.min(), x.max(), n_points)
        y_fine = np.interp(x_fine, x, y)
        x, y = x_fine, y_fine

    try:
        _trapz = np.trapezoid
    except AttributeError:
        _trapz = np.trapz  # type: ignore[attr-defined]
    total_area = _trapz(y, x)
    if total_area < 1e-12:
        return float(np.mean(x))  # fallback
    centroid_val = _trapz(x * y, x) / total_area
    return float(centroid_val)


# ======================================================================
# Linguistic Variable Definition
# ======================================================================

@dataclass
class LinguisticVariable:
    """A fuzzy linguistic variable with named term sets.

    Attributes
    ----------
    name : str
        Variable name.
    universe : tuple (lo, hi)
        The range of the universe of discourse.
    terms : dict[str, tuple]
        Mapping from term label to MF parameters.  Each value is
        either a 3-tuple (triangular) or 4-tuple (trapezoidal).
        A 4-tuple is automatically detected and routed to
        :func:`trapmf`; a 3-tuple goes to :func:`trimf`.
    mf_type : dict[str, str]
        Optional explicit MF type per term ("tri" or "trap").
    """

    name: str
    universe: Tuple[float, float]
    terms: Dict[str, Tuple] = field(default_factory=dict)
    mf_type: Dict[str, str] = field(default_factory=dict)

    def evaluate(self, term: str, x: float | np.ndarray) -> float | np.ndarray:
        """Evaluate the membership function for *term* at *x*."""
        params = self.terms[term]
        mf = self.mf_type.get(term, "tri" if len(params) == 3 else "trap")
        if mf == "tri":
            return trimf(x, params)  # type: ignore[arg-type]
        return trapmf(x, params)  # type: ignore[arg-type]

    def get_mf_data(
        self, term: str, n_points: int = 200
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return (x_array, y_array) for plotting the MF of *term*."""
        x = np.linspace(self.universe[0], self.universe[1], n_points)
        y = self.evaluate(term, x)
        return x, np.asarray(y)


# ======================================================================
# Rule
# ======================================================================

@dataclass
class FuzzyRule:
    """A single Mamdani fuzzy rule.

    ``IF antecedent THEN consequent``

    Parameters
    ----------
    antecedents : dict[str, str]
        Mapping from input variable name → fuzzy term.
    consequent : str
        Output fuzzy term.
    weight : float
        Rule weight (default 1.0).
    """

    antecedents: Dict[str, str]
    consequent: str
    weight: float = 1.0


# ======================================================================
# Fuzzy Credit Scorer
# ======================================================================

class FuzzyCreditScorer:
    """Mamdani-style FIS for credit scoring.

    Inputs (with default linguistic partitions):
    - income          (0 – 200 k USD) : Low, Medium, High
    - debt_ratio      (0 – 100 %)     : Low, Medium, High
    - payment_history (0 – 100 %)     : Poor, Fair, Good
    - employment_years (0 – 40)       : Short, Medium, Long

    Output:
    - credit_score    (0 – 100)        : VeryPoor, Poor, Fair, Good, Excellent

    Usage
    -----
    >>> scorer = FuzzyCreditScorer()
    >>> result = scorer.evaluate(income=80, debt_ratio=25,
    ...                          payment_history=95, employment_years=8)
    >>> result["credit_score"]  # doctest: +SKIP
    78.5
    """

    def __init__(self) -> None:
        # --- Define input linguistic variables ---
        self.income = LinguisticVariable(
            name="income",
            universe=(0, 200),
            terms={
                "Low":    (0, 0, 50),
                "Medium": (25, 70, 120),
                "High":   (80, 200, 200),
            },
            mf_type={"Low": "tri", "Medium": "tri", "High": "tri"},
        )

        self.debt_ratio = LinguisticVariable(
            name="debt_ratio",
            universe=(0, 100),
            terms={
                "Low":    (0, 0, 25),
                "Medium": (15, 40, 60),
                "High":   (45, 100, 100),
            },
            mf_type={"Low": "tri", "Medium": "tri", "High": "tri"},
        )

        self.payment_history = LinguisticVariable(
            name="payment_history",
            universe=(0, 100),
            terms={
                "Poor": (0, 0, 60),
                "Fair": (40, 75, 85),
                "Good": (75, 100, 100),
            },
            mf_type={"Poor": "tri", "Fair": "tri", "Good": "tri"},
        )

        self.employment_years = LinguisticVariable(
            name="employment_years",
            universe=(0, 40),
            terms={
                "Short":  (0, 0, 3),
                "Medium": (1.5, 8, 15),
                "Long":   (10, 40, 40),
            },
            mf_type={"Short": "tri", "Medium": "tri", "Long": "tri"},
        )

        self._inputs = {
            "income": self.income,
            "debt_ratio": self.debt_ratio,
            "payment_history": self.payment_history,
            "employment_years": self.employment_years,
        }

        # --- Output linguistic variable ---
        self.credit_score = LinguisticVariable(
            name="credit_score",
            universe=(0, 100),
            terms={
                "VeryPoor":   (0, 0, 25),
                "Poor":       (15, 35, 50),
                "Fair":       (35, 55, 70),
                "Good":       (55, 75, 90),
                "Excellent":  (78, 100, 100),
            },
            mf_type={
                "VeryPoor": "tri",
                "Poor": "tri",
                "Fair": "tri",
                "Good": "tri",
                "Excellent": "tri",
            },
        )

        # --- Build rule base ---
        self.rules = self._build_rules()

    def _build_rules(self) -> List[FuzzyRule]:
        """Construct the rule base.

        24 rules covering the main input combinations.  The logic
        follows standard credit-underwriting heuristics:
        - High income + low debt + good payment history → excellent
        - Low income + high debt + poor payment → very poor
        - etc.
        """
        rules = [
            # --- High income ---
            FuzzyRule({"income": "High", "debt_ratio": "Low",
                        "payment_history": "Good", "employment_years": "Long"},
                       "Excellent", weight=1.0),
            FuzzyRule({"income": "High", "debt_ratio": "Low",
                        "payment_history": "Good"},
                       "Excellent", weight=0.9),
            FuzzyRule({"income": "High", "debt_ratio": "Medium",
                        "payment_history": "Good"},
                       "Good", weight=0.9),
            FuzzyRule({"income": "High", "debt_ratio": "Low",
                        "payment_history": "Fair"},
                       "Good", weight=0.8),
            FuzzyRule({"income": "High", "debt_ratio": "High",
                        "payment_history": "Fair"},
                       "Fair", weight=0.7),
            FuzzyRule({"income": "High", "debt_ratio": "High",
                        "payment_history": "Poor"},
                       "Poor", weight=0.6),
            # --- Medium income ---
            FuzzyRule({"income": "Medium", "debt_ratio": "Low",
                        "payment_history": "Good", "employment_years": "Long"},
                       "Good", weight=0.9),
            FuzzyRule({"income": "Medium", "debt_ratio": "Low",
                        "payment_history": "Good"},
                       "Good", weight=0.85),
            FuzzyRule({"income": "Medium", "debt_ratio": "Medium",
                        "payment_history": "Good"},
                       "Fair", weight=0.8),
            FuzzyRule({"income": "Medium", "debt_ratio": "Low",
                        "payment_history": "Fair"},
                       "Fair", weight=0.75),
            FuzzyRule({"income": "Medium", "debt_ratio": "Medium",
                        "payment_history": "Fair"},
                       "Fair", weight=0.7),
            FuzzyRule({"income": "Medium", "debt_ratio": "High",
                        "payment_history": "Poor"},
                       "Poor", weight=0.7),
            FuzzyRule({"income": "Medium", "debt_ratio": "High",
                        "payment_history": "Good"},
                       "Fair", weight=0.6),
            # --- Low income ---
            FuzzyRule({"income": "Low", "debt_ratio": "Low",
                        "payment_history": "Good", "employment_years": "Long"},
                       "Fair", weight=0.8),
            FuzzyRule({"income": "Low", "debt_ratio": "Low",
                        "payment_history": "Good"},
                       "Fair", weight=0.7),
            FuzzyRule({"income": "Low", "debt_ratio": "Medium",
                        "payment_history": "Good"},
                       "Poor", weight=0.7),
            FuzzyRule({"income": "Low", "debt_ratio": "Low",
                        "payment_history": "Fair"},
                       "Poor", weight=0.65),
            FuzzyRule({"income": "Low", "debt_ratio": "Medium",
                        "payment_history": "Fair"},
                       "Poor", weight=0.7),
            FuzzyRule({"income": "Low", "debt_ratio": "High",
                        "payment_history": "Poor"},
                       "VeryPoor", weight=0.9),
            FuzzyRule({"income": "Low", "debt_ratio": "High",
                        "payment_history": "Fair"},
                       "Poor", weight=0.7),
            # --- Employment-based overrides ---
            FuzzyRule({"employment_years": "Short", "debt_ratio": "High",
                        "payment_history": "Poor"},
                       "VeryPoor", weight=0.85),
            FuzzyRule({"employment_years": "Long", "income": "Medium",
                        "payment_history": "Good"},
                       "Good", weight=0.75),
            FuzzyRule({"employment_years": "Short", "income": "Low",
                        "payment_history": "Poor"},
                       "VeryPoor", weight=0.8),
        ]
        return rules

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------
    def evaluate(
        self,
        income: float,
        debt_ratio: float,
        payment_history: float,
        employment_years: float,
    ) -> Dict[str, float]:
        """Run the FIS and return the defuzzified credit score.

        Parameters
        ----------
        income : float
            Annual income in thousands of USD.
        debt_ratio : float
            Debt-to-income ratio in percent.
        payment_history : float
            On-time payment percentage (0–100).
        employment_years : float
            Continuous employment duration in years.

        Returns
        -------
        dict with keys:
            - ``credit_score`` : float in [0, 100]
            - ``firing_strengths`` : list of per-rule firing strengths
            - ``input_memberships`` : dict of {var: {term: degree}}
        """
        crisp_inputs = {
            "income": float(income),
            "debt_ratio": float(debt_ratio),
            "payment_history": float(payment_history),
            "employment_years": float(employment_years),
        }

        # Evaluate input memberships
        input_memberships: Dict[str, Dict[str, float]] = {}
        for var_name, lv in self._inputs.items():
            val = crisp_inputs[var_name]
            input_memberships[var_name] = {}
            for term in lv.terms:
                input_memberships[var_name][term] = float(lv.evaluate(term, val))

        # Evaluate rules
        firing_strengths: List[float] = []
        for rule in self.rules:
            ant_degrees = []
            for var_name, term in rule.antecedents.items():
                deg = input_memberships.get(var_name, {}).get(term, 0.0)
                ant_degrees.append(deg)
            strength = float(np.min(ant_degrees)) * rule.weight if ant_degrees else 0.0
            firing_strengths.append(strength)

        # Aggregate output (max composition)
        x_out = np.linspace(
            self.credit_score.universe[0],
            self.credit_score.universe[1],
            500,
        )
        aggregate = np.zeros_like(x_out)

        for rule, strength in zip(self.rules, firing_strengths):
            if strength < 1e-12:
                continue
            mf_vals = np.asarray(
                self.credit_score.evaluate(rule.consequent, x_out)
            )
            clipped = np.minimum(mf_vals, strength)
            aggregate = np.maximum(aggregate, clipped)

        # Defuzzify
        score = centroid_defuzzify(x_out, aggregate)

        return {
            "credit_score": float(np.clip(score, 0, 100)),
            "firing_strengths": firing_strengths,
            "input_memberships": input_memberships,
        }

    # ------------------------------------------------------------------
    # Visualisation helpers
    # ------------------------------------------------------------------
    def get_all_mf_data(
        self, n_points: int = 200
    ) -> Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]:
        """Return membership-function data for all variables.

        Returns
        -------
        dict
            ``{var_name: {term: (x_array, y_array)}}`` — ready for
            plotting with pyqtgraph or matplotlib.
        """
        data: Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]] = {}
        for var_name, lv in self._inputs.items():
            data[var_name] = {}
            for term in lv.terms:
                data[var_name][term] = lv.get_mf_data(term, n_points)
        # Output
        data[self.credit_score.name] = {}
        for term in self.credit_score.terms:
            data[self.credit_score.name][term] = self.credit_score.get_mf_data(
                term, n_points
            )
        return data


# ======================================================================
# Demo
# ======================================================================
if __name__ == "__main__":
    scorer = FuzzyCreditScorer()

    print("=" * 60)
    print("Fuzzy Credit Scorer — Demo")
    print("=" * 60)

    test_cases = [
        {"income": 150, "debt_ratio": 10, "payment_history": 98, "employment_years": 15},
        {"income": 50, "debt_ratio": 35, "payment_history": 80, "employment_years": 5},
        {"income": 20, "debt_ratio": 60, "payment_history": 45, "employment_years": 1},
        {"income": 80, "debt_ratio": 20, "payment_history": 92, "employment_years": 10},
        {"income": 30, "debt_ratio": 70, "payment_history": 30, "employment_years": 0.5},
    ]

    for i, case in enumerate(test_cases):
        result = scorer.evaluate(**case)
        print(
            f"\n  Case {i + 1}: "
            f"income={case['income']:>6}k  "
            f"debt={case['debt_ratio']:>5.1f}%  "
            f"pay_hist={case['payment_history']:>5.1f}%  "
            f"emp_yrs={case['employment_years']:>5.1f}"
        )
        print(f"    → Credit Score: {result['credit_score']:.1f}")

        # Show top-3 firing rules
        strengths = result["firing_strengths"]
        top_idx = np.argsort(strengths)[::-1][:3]
        for idx in top_idx:
            if strengths[idx] > 0.01:
                rule = scorer.rules[idx]
                ants = ", ".join(
                    f"{k}={v}" for k, v in rule.antecedents.items()
                )
                print(
                    f"      Rule {idx + 1:2d} [{strengths[idx]:.3f}]: "
                    f"IF {ants} THEN {rule.consequent}"
                )
    print("\n" + "=" * 60)
