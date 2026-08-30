"""
macro_models.py — Macroeconomic & Structural Models
====================================================
Provides classic macroeconomic models for the EcoPulse quant engine:

* **TaylorRule**         — Central bank reaction function
* **PhillipsCurve**      — Inflation-unemployment tradeoff
* **DSGESimple**         — 3-equation New Keynesian DSGE model
* **MinskyCycle**        — Financial instability hypothesis (state machine)
* **KondratievWave**     — Long-wave 45-60 year economic cycles

Dependencies: numpy only.
"""

from __future__ import annotations

import numpy as np


class TaylorRule:
    """
    Simulates a central bank reaction function.

    The Taylor rule sets the nominal interest rate as a function of the
    inflation gap and the output gap:

        i_t = r* + π_target + φ_π (π_t - π_target) + φ_y (y_t)

    Parameters
    ----------
    neutral_rate : float
        The long-run neutral real interest rate (r*).
    inflation_target : float
        Central bank's inflation target (π*).
    phi_pi : float
        Response coefficient on the inflation gap (φ_π).  Standard ≈ 1.5.
    phi_y : float
        Response coefficient on the output gap (φ_y).  Standard ≈ 0.5.
    """

    def __init__(
        self,
        neutral_rate: float = 2.0,
        inflation_target: float = 2.0,
        phi_pi: float = 1.5,
        phi_y: float = 0.5,
    ) -> None:
        self.neutral_rate = neutral_rate
        self.inflation_target = inflation_target
        self.phi_pi = phi_pi
        self.phi_y = phi_y

    def predict_rate(self, inflation: float | np.ndarray, output_gap: float | np.ndarray) -> float | np.ndarray:
        """
        Compute the policy interest rate given inflation and output gap.

        Parameters
        ----------
        inflation : float or ndarray
            Current (or series of) inflation rates (%).
        output_gap : float or ndarray
            Current (or series of) output gaps (%).

        Returns
        -------
        float or ndarray
            The implied policy rate (%).
        """
        inflation_gap = inflation - self.inflation_target
        rate = (self.neutral_rate + self.inflation_target
                + self.phi_pi * inflation_gap
                + self.phi_y * output_gap)
        return rate


class PhillipsCurve:
    """
    Models the inflation–unemployment tradeoff (expectations-augmented Phillips curve).

        π_t = π^e - α (u_t - u*) + supply_shock

    Parameters
    ----------
    expected_inflation : float
        Expected inflation π^e (%).
    natural_unemployment : float
        Natural rate of unemployment u* (%).
    alpha : float
        Slope coefficient linking unemployment gap to inflation. Typical 0.5.
    """

    def __init__(
        self,
        expected_inflation: float = 2.0,
        natural_unemployment: float = 5.0,
        alpha: float = 0.5,
    ) -> None:
        self.expected_inflation = expected_inflation
        self.natural_unemployment = natural_unemployment
        self.alpha = alpha

    def predict_inflation(
        self,
        unemployment: float | np.ndarray,
        supply_shock: float = 0.0,
    ) -> float | np.ndarray:
        """
        Predict inflation given unemployment and an optional supply shock.

        Parameters
        ----------
        unemployment : float or ndarray
            Unemployment rate (%).
        supply_shock : float, optional
            Cost-push / supply-side shock (%-points).

        Returns
        -------
        float or ndarray
            Predicted inflation (%).
        """
        unemployment_gap = unemployment - self.natural_unemployment
        inflation = self.expected_inflation - self.alpha * unemployment_gap + supply_shock
        return inflation


class DSGESimple:
    """
    Simplified 3-equation New Keynesian DSGE model.

    The three equations are:
        1. IS curve:       y_t = E_t[y_{t+1}] - σ (i_t - E_t[π_{t+1}] - r*) + demand_shock
        2. Phillips curve:  π_t = β E_t[π_{t+1}] + κ y_t + supply_shock
        3. Taylor rule:     i_t = r* + π* + φ_π (π_t - π*) + φ_y y_t + monetary_shock

    This simplified version assumes static expectations (E_t[x_{t+1}] = x_t) for
    tractability and uses numpy linear algebra to solve the reduced-form system
    for (y_t, π_t, i_t) at each period.
    """

    def __init__(
        self,
        sigma: float = 1.0,
        beta: float = 0.99,
        kappa: float = 0.1,
        phi_pi: float = 1.5,
        phi_y: float = 0.5,
        neutral_rate: float = 0.5,
        inflation_target: float = 2.0,
    ) -> None:
        self.sigma = sigma
        self.beta = beta
        self.kappa = kappa
        self.phi_pi = phi_pi
        self.phi_y = phi_y
        self.neutral_rate = neutral_rate
        self.inflation_target = inflation_target

    def simulate_shocks(
        self,
        monetary_shock: np.ndarray,
        demand_shock: np.ndarray,
        supply_shock: np.ndarray,
        periods: int,
    ) -> dict[str, np.ndarray]:
        """
        Simulate the DSGE under a sequence of shocks.

        Under static expectations the reduced form is a 3×3 linear system:
            A @ [y, π, i]' = b(shocks)

        Parameters
        ----------
        monetary_shock : ndarray of shape (periods,)
        Monetary policy shocks.
        demand_shock : ndarray of shape (periods,)
        Demand-side shocks.
        supply_shock : ndarray of shape (periods,)
        Supply-side shocks.
        periods : int
            Number of simulation periods.

        Returns
        -------
        dict with keys 'output_gap', 'inflation', 'interest_rate'
        """
        shocks = [monetary_shock, demand_shock, supply_shock]
        for s in shocks:
            if len(s) != periods:
                raise ValueError("All shock arrays must have length == periods")

        # Build coefficient matrix A  (3x3)
        # IS:      y - y + σ i - σ π = σ r* + demand  =>  0·y + σ·π + σ·i = σ r* + demand
        # Actually let's write carefully with static exp E[x]=x:
        # IS:      y = y - σ(i - π - r*) + ε_d  =>  0 = -σ i + σ π + σ r* + ε_d
        # Phillips: π = β π + κ y + ε_s          =>  (1-β) π = κ y + ε_s
        # Taylor:  i = r* + π* + φ_π(π-π*) + φ_y y + ε_m
        #          =>  i = r*(1-φ_π) + φ_π π + φ_y y + ε_m   (since r*+π*+φ_π(π-π*)=r*+π*(1-φ_π)+φ_π π)
        # Rearranging in order [y, π, i]:
        # Eq1 (IS):      σ·y_coeff?  Let me redo.
        #
        # IS: y_t = y_t - σ(i_t - π_t - r*) + ε_d
        #     0 = -σ i_t + σ π_t + σ r* + ε_d
        #     0·y + σ·π + (-σ)·i = -σ r* - ε_d   ... wait sign.
        #     => σ π - σ i = -σ r* - ε_d
        #
        # Phillips: (1-β)π = κ y + ε_s
        #     => -κ y + (1-β) π + 0·i = ε_s
        #
        # Taylor: i = r*(1-φ_π) + φ_π π + φ_y y + ε_m
        #     => -φ_y y - φ_π π + 1·i = r*(1-φ_π) + ε_m
        #
        # Hmm but with static expectations IS becomes degenerate (0=0 for y).
        # Better approach: use one-period-ahead dynamic simulation.
        # Use lagged values: assume initial steady state, then iterate forward.

        rstar = self.neutral_rate
        pistar = self.inflation_target

        output_gap = np.zeros(periods)
        inflation = np.full(periods, pistar)
        interest_rate = np.full(periods, rstar + pistar)

        # Lagged values from steady state
        y_lag = 0.0
        pi_lag = pistar

        for t in range(periods):
            eps_m = monetary_shock[t]
            eps_d = demand_shock[t]
            eps_s = supply_shock[t]

            # Solve the 3x3 system for [y_t, π_t, i_t]
            # IS:      y_t = y_lag - σ(i_t - pi_lag - rstar) + eps_d
            # Phillips: π_t = beta * pi_lag + kappa * y_t + eps_s
            # Taylor:  i_t  = rstar + pistar + phi_pi*(π_t - pistar) + phi_y*y_t + eps_m

            # Substitute Taylor into IS:
            # y_t = y_lag - σ(rstar+pistar+φ_π(π_t-π*)+φ_y y_t+eps_m - pi_lag - rstar) + eps_d
            # y_t = y_lag - σ(pistar + φ_π(π_t-π*)+φ_y y_t+eps_m - pi_lag) + eps_d
            # y_t(1+σ φ_y) = y_lag - σ(pistar + φ_π(π_t-π*)+eps_m - pi_lag) + eps_d
            # y_t(1+σ φ_y) = y_lag - σ φ_π π_t + σ φ_π π* - σ pistar - σ eps_m + σ pi_lag + eps_d

            # Substitute Phillips into IS substitution:
            # π_t = beta pi_lag + kappa y_t + eps_s
            # => y_t(1+σ φ_y) = y_lag - σ φ_π (beta pi_lag + kappa y_t + eps_s) + σ φ_π π* - σ pistar - σ eps_m + σ pi_lag + eps_d
            # y_t(1+σ φ_y + σ φ_π kappa) = y_lag + σ pi_lag - σ φ_π beta pi_lag + σ φ_π π* - σ pistar - σ eps_m - σ φ_π eps_s + eps_d

            A_y = 1.0 + self.sigma * self.phi_y + self.sigma * self.phi_pi * self.kappa
            b_y = (y_lag
                    + self.sigma * pi_lag
                    - self.sigma * self.phi_pi * self.beta * pi_lag
                    + self.sigma * self.phi_pi * pistar
                    - self.sigma * pistar
                    - self.sigma * eps_m
                    - self.sigma * self.phi_pi * eps_s
                    + eps_d)
            y_t = b_y / A_y

            pi_t = self.beta * pi_lag + self.kappa * y_t + eps_s
            i_t = rstar + pistar + self.phi_pi * (pi_t - pistar) + self.phi_y * y_t + eps_m

            output_gap[t] = y_t
            inflation[t] = pi_t
            interest_rate[t] = i_t

            y_lag = y_t
            pi_lag = pi_t

        return {
            "output_gap": output_gap,
            "inflation": inflation,
            "interest_rate": interest_rate,
        }


class MinskyCycle:
    """
    Models the Minsky Financial Instability Hypothesis as a state machine.

    The economy cycles through four phases:
        HEDGE  → SPECULATIVE → PONZI → CRISIS → HEDGE → …

    Credit growth feeds leverage, which accelerates transitions.
    After crisis, leverage resets and the cycle restarts.
    """

    HEDGE = "hedge"
    SPECULATIVE = "speculative"
    PONZI = "ponzi"
    CRISIS = "crisis"
    _ALL_PHASES = [HEDGE, SPECULATIVE, PONZI, CRISIS]

    def __init__(
        self,
        credit_growth_threshold_spec: float = 0.08,
        credit_growth_threshold_ponzi: float = 0.15,
        leverage_threshold_crisis: float = 0.85,
        crisis_duration: int = 4,
        recovery_rate: float = 0.3,
    ) -> None:
        self.credit_growth_threshold_spec = credit_growth_threshold_spec
        self.credit_growth_threshold_ponzi = credit_growth_threshold_ponzi
        self.leverage_threshold_crisis = leverage_threshold_crisis
        self.crisis_duration = crisis_duration
        self.recovery_rate = recovery_rate

    def simulate(
        self,
        credit_growth_initial: float = 0.04,
        periods: int = 100,
    ) -> np.ndarray:
        """
        Run the Minsky cycle simulation.

        Parameters
        ----------
        credit_growth_initial : float
            Starting credit growth rate (e.g. 0.04 = 4 %).
        periods : int
            Number of periods to simulate.

        Returns
        -------
        ndarray of shape (periods, 3)
            Each row is [credit, leverage, phase_index].
            Phase index: 0=hedge, 1=speculative, 2=ponzi, 3=crisis.
        """
        results = np.zeros((periods, 3), dtype=object)

        credit = 100.0
        leverage = 0.30
        cg = credit_growth_initial
        phase = self.HEDGE
        crisis_counter = 0

        # Noise generator
        rng = np.random.default_rng(42)

        for t in range(periods):
            phase_idx = self._ALL_PHASES.index(phase)
            results[t] = [credit, leverage, phase]

            if phase == self.HEDGE:
                cg += rng.normal(0.005, 0.01)
                cg = max(cg, 0.01)
                leverage += cg * 0.1
                if cg > self.credit_growth_threshold_spec:
                    phase = self.SPECULATIVE

            elif phase == self.SPECULATIVE:
                cg += rng.normal(0.008, 0.012)
                cg = max(cg, 0.02)
                leverage += cg * 0.15
                if cg > self.credit_growth_threshold_ponzi:
                    phase = self.PONZI
                elif cg < self.credit_growth_threshold_spec * 0.5:
                    phase = self.HEDGE

            elif phase == self.PONZI:
                cg += rng.normal(0.01, 0.02)
                leverage += cg * 0.2
                if leverage >= self.leverage_threshold_crisis or cg > 0.30:
                    phase = self.CRISIS
                    crisis_counter = 0

            elif phase == self.CRISIS:
                crisis_counter += 1
                cg *= 0.3
                leverage *= (1.0 - self.recovery_rate)
                credit *= (1.0 - 0.05)
                if crisis_counter >= self.crisis_duration:
                    phase = self.HEDGE
                    cg = credit_growth_initial

            credit *= (1.0 + cg)
            leverage = np.clip(leverage, 0.05, 0.99)

        return results


class KondratievWave:
    """
    Models long-wave Kondratiev cycles (~45-60 years) driven by
    innovation waves and creative destruction.

    Each wave follows a sinusoidal pattern with an asymmetric shape
    (steeper rise, more gradual decline) to mimic real economic cycles.
    """

    # Approximate start years of historical K-waves
    WAVE_STARTS = [1780, 1840, 1890, 1940, 1990]
    WAVE_LABELS = [
        "Steam & Textiles",
        "Railways & Steel",
        "Electricity & Chemicals",
        "Petrochemicals & Electronics",
        "Information & Digital",
    ]

    def __init__(self, amplitude: float = 1.0, noise_std: float = 0.05) -> None:
        self.amplitude = amplitude
        self.noise_std = noise_std

    def generate_wave(
        self,
        start_year: int = 1780,
        end_year: int = 2020,
        wave_period: float = 54.0,
    ) -> dict[str, np.ndarray]:
        """
        Generate a Kondratiev wave over the specified year range.

        Parameters
        ----------
        start_year : int
            First year of the simulation.
        end_year : int
            Last year of the simulation.
        wave_period : float
            Average duration of one Kondratiev wave in years (default 54).

        Returns
        -------
        dict with keys:
            'years'       : 1-D array of years
            'wave'        : 1-D array of normalised wave values
            'growth_rate' : 1-D array of implied annual growth rates
            'phase'       : 1-D array of phase labels (str)
        """
        years = np.arange(start_year, end_year + 1, dtype=float)
        n = len(years)
        rng = np.random.default_rng(123)

        # Phase within cycle (0 to 2π)
        phase_angle = 2.0 * np.pi * (years - start_year) / wave_period

        # Asymmetric wave: use sin with a harmonic correction for steeper ascent
        wave = (self.amplitude
                * (np.sin(phase_angle - np.pi / 2)
                   + 0.3 * np.sin(2 * phase_angle - np.pi / 2))
                / 1.3)

        wave += rng.normal(0, self.noise_std, n)

        # Growth rate (first difference)
        growth_rate = np.zeros(n)
        growth_rate[1:] = np.diff(wave)

        # Phase labels based on wave position
        phase_labels = np.array([
            "Prosperity" if w > 0.3 * self.amplitude
            else "Recession" if w < -0.3 * self.amplitude
            else "Stagnation"
            for w in wave
        ], dtype=object)

        return {
            "years": years.astype(int),
            "wave": wave,
            "growth_rate": growth_rate,
            "phase": phase_labels,
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("macro_models.py — Demo")
    print("=" * 60)

    # --- Taylor Rule ---
    print("\n--- Taylor Rule ---")
    tr = TaylorRule(neutral_rate=2.0, inflation_target=2.0, phi_pi=1.5, phi_y=0.5)
    inflations = np.array([1.0, 2.0, 3.0, 5.0])
    gaps = np.array([-1.0, 0.0, 1.0, 2.0])
    rates = tr.predict_rate(inflations, gaps)
    for pi, y, r in zip(inflations, gaps, rates):
        print(f"  inflation={pi}%, output_gap={y}% => rate={r:.2f}%")

    # --- Phillips Curve ---
    print("\n--- Phillips Curve ---")
    pc = PhillipsCurve(expected_inflation=2.0, natural_unemployment=5.0, alpha=0.5)
    for u in [3.0, 5.0, 7.0, 9.0]:
        pi = pc.predict_inflation(u)
        print(f"  unemployment={u}% => inflation={pi:.2f}%")
    pi_shock = pc.predict_inflation(5.0, supply_shock=2.0)
    print(f"  unemployment=5% with +2pp supply shock => inflation={pi_shock:.2f}%")

    # --- DSGE Simple ---
    print("\n--- DSGE Simple (Monetary tightening shock) ---")
    dsge = DSGESimple()
    periods = 40
    monetary_shock = np.zeros(periods)
    monetary_shock[5] = 1.0  # 1 pp shock at t=5
    demand_shock = np.zeros(periods)
    supply_shock = np.zeros(periods)
    res = dsge.simulate_shocks(monetary_shock, demand_shock, supply_shock, periods)
    print(f"  Periods: {periods}")
    print(f"  Output gap range:  [{res['output_gap'].min():.4f}, {res['output_gap'].max():.4f}]")
    print(f"  Inflation range:   [{res['inflation'].min():.4f}, {res['inflation'].max():.4f}]")
    print(f"  Interest rate range: [{res['interest_rate'].min():.4f}, {res['interest_rate'].max():.4f}]")

    # --- Minsky Cycle ---
    print("\n--- Minsky Cycle ---")
    mc = MinskyCycle()
    sim = mc.simulate(credit_growth_initial=0.04, periods=120)
    unique_phases = [row[2] for row in sim]
    from collections import Counter
    counts = Counter(unique_phases)
    print(f"  Phase distribution over 120 periods:")
    for phase, cnt in sorted(counts.items()):
        print(f"    {phase}: {cnt}")

    # --- Kondratiev Wave ---
    print("\n--- Kondratiev Wave ---")
    kw = KondratievWave()
    kw_res = kw.generate_wave(start_year=1780, end_year=2020)
    print(f"  Years: {kw_res['years'][0]} - {kw_res['years'][-1]}")
    print(f"  Wave range: [{kw_res['wave'].min():.3f}, {kw_res['wave'].max():.3f}]")
    phase_counts = Counter(kw_res['phase'])
    for ph, cnt in sorted(phase_counts.items()):
        print(f"    {ph}: {cnt} years")

    print("\n[DONE]")
