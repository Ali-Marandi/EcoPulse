r"""
political_risk.py — Political & Geopolitical Risk Models
=========================================================
Provides models for political and geopolitical risk assessment:

* **PoliticalRiskScore**      — Composite ICRG-style political risk scoring
* **SanctionImpactModel**     — Economic impact of trade sanctions
* **GeopoliticalGameModel**   — Game-theoretic geopolitical risk models
* **ElectionCycleModel**      — Political business cycle effects

Dependencies: numpy, scipy.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple


class PoliticalRiskScore:
    """
    Composite political risk scoring model (ICRG-style).

    Combines economic, political, and financial risk sub-indices into
    a single weighted composite score. Lower scores indicate higher risk.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Parameters
        ----------
        weights : dict or None
            Weights for sub-indices. Keys: 'economic', 'political', 'financial'.
            Must sum to 1.0. Defaults to equal weights.
        """
        if weights is None:
            self.weights = {"economic": 1.0 / 3, "political": 1.0 / 3, "financial": 1.0 / 3}
        else:
            total = sum(weights.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Weights must sum to 1.0, got {total}")
            self.weights = dict(weights)

    def compute(
        self,
        economic_indicators: Dict[str, float],
        political_indicators: Dict[str, float],
        financial_indicators: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute a weighted composite political risk score.

        Each sub-index is the average of its normalised indicators (0–100).
        The composite is the weighted sum of sub-indices.

        Parameters
        ----------
        economic_indicators : dict
            Key-value pairs of economic indicators (GDP growth %, inflation %,
            unemployment %, etc.). Higher values = better economic conditions.
        political_indicators : dict
            Political stability, corruption index, rule of law, etc.
        financial_indicators : dict
            Current account %, FX reserves months, debt/GDP, etc.

        Returns
        -------
        dict with keys:
            'composite_score'   : float, 0–100 (100 = lowest risk)
            'economic_score'    : float
            'political_score'   : float
            'financial_score'   : float
            'risk_rating'       : str, qualitative rating
        """
        # Simple normalisation: each indicator is assumed to be on a 0-100 scale
        # (caller should pre-normalise). We take the mean.
        if not economic_indicators:
            econ_score = 50.0
        else:
            econ_score = float(np.mean(list(economic_indicators.values())))

        if not political_indicators:
            pol_score = 50.0
        else:
            pol_score = float(np.mean(list(political_indicators.values())))

        if not financial_indicators:
            fin_score = 50.0
        else:
            fin_score = float(np.mean(list(financial_indicators.values())))

        composite = (
            self.weights["economic"] * econ_score
            + self.weights["political"] * pol_score
            + self.weights["financial"] * fin_score
        )

        # Risk rating
        if composite >= 80:
            rating = "Very Low Risk"
        elif composite >= 65:
            rating = "Low Risk"
        elif composite >= 50:
            rating = "Moderate Risk"
        elif composite >= 35:
            rating = "High Risk"
        else:
            rating = "Very High Risk"

        return {
            "composite_score": composite,
            "economic_score": econ_score,
            "political_score": pol_score,
            "financial_score": fin_score,
            "risk_rating": rating,
        }

    def country_comparison(
        self,
        country_scores: Dict[str, float],
    ) -> List[Tuple[str, float]]:
        """
        Rank countries by composite risk score.

        Parameters
        ----------
        country_scores : dict
            country_name -> composite_score.

        Returns
        -------
        list of (country, score) tuples, sorted from lowest to highest risk.
        """
        sorted_countries = sorted(country_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_countries


class SanctionImpactModel:
    """
    Models the economic impact of trade sanctions.
    """

    def estimate_gdp_impact(
        self,
        trade_dependency: float,
        sanction_severity: float,
        duration: float,
        adaptation_rate: float = 0.1,
    ) -> Dict[str, np.ndarray]:
        """
        Estimate GDP loss from trade sanctions.

        The model assumes an initial impact proportional to trade
        dependency × severity, with gradual adaptation over time.

        Parameters
        ----------
        trade_dependency : float
            Trade as % of GDP (e.g., 0.4 = 40%).
        sanction_severity : float
            Fraction of trade affected (0 to 1).
        duration : float
            Duration in years.
        adaptation_rate : float
            Annual rate of economic adaptation (0 to 1).

        Returns
        -------
        dict with keys:
            'gdp_loss_path' : ndarray, cumulative GDP loss % over time
            'annual_loss'   : ndarray, annual GDP loss %
            'total_loss'    : float, total GDP loss over duration
        """
        years = np.arange(1, int(duration) + 1, dtype=float)
        initial_impact = trade_dependency * sanction_severity

        # Annual loss decays as adaptation occurs
        annual_loss = initial_impact * np.exp(-adaptation_rate * years)

        # Cumulative GDP loss (integrated)
        gdp_loss_path = np.cumsum(annual_loss)
        total_loss = float(gdp_loss_path[-1]) if len(gdp_loss_path) > 0 else 0.0

        return {
            "gdp_loss_path": gdp_loss_path,
            "annual_loss": annual_loss,
            "total_loss": total_loss,
        }

    def supply_chain_disruption(
        self,
        import_shares: np.ndarray,
        sanction_targets: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """
        Compute supply chain impact matrix from sanctions.

        Parameters
        ----------
        import_shares : ndarray of shape (N, M)
            Import share matrix: import_shares[i, j] = fraction of
            sector i's inputs sourced from country j.
        sanction_targets : ndarray of shape (M,)
            Binary vector: 1 if country j is sanctioned, 0 otherwise.

        Returns
        -------
        dict with keys:
            'sector_impact' : ndarray of shape (N,), impact per sector
            'impact_matrix' : ndarray of shape (N, M), detailed impact
            'total_exposure': float, economy-wide exposure
        """
        import_shares = np.asarray(import_shares, dtype=float)
        sanction_targets = np.asarray(sanction_targets, dtype=float)

        # Impact per sector: sum of import shares from sanctioned countries
        impact_matrix = import_shares * sanction_targets[np.newaxis, :]
        sector_impact = impact_matrix.sum(axis=1)
        total_exposure = float(sector_impact.sum())

        return {
            "sector_impact": sector_impact,
            "impact_matrix": impact_matrix,
            "total_exposure": total_exposure,
        }

    def currency_impact(
        self,
        capital_flow_data: np.ndarray,
        sanction_probability: float,
    ) -> Dict[str, float]:
        """
        Estimate currency pressure from sanction risk.

        Parameters
        ----------
        capital_flow_data : ndarray of shape (T,)
            Historical net capital flows.
        sanction_probability : float
            Probability of sanctions being imposed (0 to 1).

        Returns
        -------
        dict with keys:
            'expected_pressure' : float, expected currency depreciation %
            'tail_risk'         : float, 95th percentile depreciation
            'flight_risk'       : float, capital flight estimate
        """
        capital_flow_data = np.asarray(capital_flow_data, dtype=float)
        if len(capital_flow_data) == 0:
            return {"expected_pressure": 0.0, "tail_risk": 0.0, "flight_risk": 0.0}

        mean_flow = np.mean(capital_flow_data)
        std_flow = np.std(capital_flow_data)

        # Expected depreciation proportional to sanction probability and
        # capital flow vulnerability
        expected_pressure = sanction_probability * abs(mean_flow) * 0.5

        # Tail risk: worse scenario
        tail_risk = sanction_probability * (abs(mean_flow) + 1.65 * std_flow) * 0.5

        # Capital flight estimate
        flight_risk = sanction_probability * max(-mean_flow, 0) * 2.0

        return {
            "expected_pressure": float(expected_pressure),
            "tail_risk": float(tail_risk),
            "flight_risk": float(flight_risk),
        }


class GeopoliticalGameModel:
    """
    Game-theoretic models for geopolitical risk analysis.
    """

    def nash_equilibrium_2x2(
        self,
        payoff_matrix_a: np.ndarray,
        payoff_matrix_b: np.ndarray,
    ) -> Dict[str, object]:
        """
        Find all pure-strategy Nash equilibria in a 2×2 game.

        Parameters
        ----------
        payoff_matrix_a : ndarray of shape (2, 2)
            Row player's payoffs. payoff_matrix_a[i, j] is the payoff
            when player A plays i and player B plays j.
        payoff_matrix_b : ndarray of shape (2, 2)
            Column player's payoffs.

        Returns
        -------
        dict with keys:
            'equilibria'      : list of (row_action, col_action) tuples
            'n_equilibria'    : int
            'payoffs_at_eq'   : list of (payoff_a, payoff_b) at each equilibrium
        """
        A = np.asarray(payoff_matrix_a, dtype=float)
        B = np.asarray(payoff_matrix_b, dtype=float)

        equilibria = []
        payoffs_at_eq = []

        for i in range(2):
            for j in range(2):
                # Check if (i, j) is a Nash equilibrium
                # Player A: row i is best response to column j
                a_payoff = A[i, j]
                a_best = True
                for ii in range(2):
                    if A[ii, j] > a_payoff:
                        a_best = False
                        break

                # Player B: column j is best response to row i
                b_payoff = B[i, j]
                b_best = True
                for jj in range(2):
                    if B[i, jj] > b_payoff:
                        b_best = False
                        break

                if a_best and b_best:
                    equilibria.append((i, j))
                    payoffs_at_eq.append((float(a_payoff), float(b_payoff)))

        return {
            "equilibria": equilibria,
            "n_equilibria": len(equilibria),
            "payoffs_at_eq": payoffs_at_eq,
        }

    def sequential_game_payoffs(
        self,
        player1_actions: int,
        player2_actions: int,
        payoff_func: callable,
    ) -> Dict[str, object]:
        """
        Solve a sequential game via backward induction.

        Player 1 moves first, player 2 observes and responds.

        Parameters
        ----------
        player1_actions : int
            Number of actions available to player 1.
        player2_actions : int
            Number of actions available to player 2.
        payoff_func : callable(a1, a2) -> (payoff_1, payoff_2)
            Function that returns payoffs for any action profile.

        Returns
        -------
        dict with keys:
            'optimal_a1'       : int, optimal first-mover action
            'optimal_response' : dict mapping a1 -> best a2
            'subgame_outcomes' : dict mapping a1 -> (a2, p1, p2)
        """
        optimal_response = {}
        subgame_outcomes = {}

        # For each player 1 action, find player 2's best response
        for a1 in range(player1_actions):
            best_a2 = 0
            best_p2 = -np.inf
            for a2 in range(player2_actions):
                _, p2 = payoff_func(a1, a2)
                if p2 > best_p2:
                    best_p2 = p2
                    best_a2 = a2
            optimal_response[a1] = best_a2
            p1, p2 = payoff_func(a1, best_a2)
            subgame_outcomes[a1] = (best_a2, p1, p2)

        # Player 1 anticipates player 2's response
        best_a1 = 0
        best_p1 = -np.inf
        for a1 in range(player1_actions):
            _, p1, _ = subgame_outcomes[a1]
            if p1 > best_p1:
                best_p1 = p1
                best_a1 = a1

        return {
            "optimal_a1": best_a1,
            "optimal_response": optimal_response,
            "subgame_outcomes": subgame_outcomes,
        }

    def sanction_game(
        self,
        escalation_cost: float = 2.0,
        compliance_benefit: float = 1.0,
        defiance_benefit: float = 3.0,
    ) -> Dict[str, object]:
        """
        Model sanction escalation as a 2×2 game.

        Sender (e.g., Western bloc): Impose Sanctions vs. Negotiate
        Target (e.g., sanctioned country): Comply vs. Defy

        Parameters
        ----------
        escalation_cost : float
            Cost to sender of imposing sanctions.
        compliance_benefit : float
            Benefit to sender if target complies.
        defiance_benefit : float
            Benefit to target of defiance (e.g., sovereignty signal).

        Returns
        -------
        dict with keys:
            'payoff_sender' : ndarray (2, 2)
            'payoff_target' : ndarray (2, 2)
            'nash_result'   : result from nash_equilibrium_2x2
            'dominant_strategy_sender': str or None
            'dominant_strategy_target': str or None
        """
        # Actions: 0 = Negotiate/Comply, 1 = Sanction/Defy
        # Sender × Target payoffs
        # (Negotiate, Comply): both benefit from cooperation
        # (Negotiate, Defy): target gains, sender loses
        # (Sanction, Comply): sender gains from compliance, both pay some cost
        # (Sanction, Defy): both lose from escalation

        payoff_sender = np.array([
            [compliance_benefit, -defiance_benefit * 0.5],
            [compliance_benefit - escalation_cost * 0.5, -escalation_cost],
        ])

        payoff_target = np.array([
            [compliance_benefit * 0.8, defiance_benefit],
            [compliance_benefit * 0.3 - 1.0, -escalation_cost * 0.8],
        ])

        nash = self.nash_equilibrium_2x2(payoff_sender, payoff_target)

        # Check dominant strategies
        actions = ["Negotiate", "Sanction"]
        ds_sender = None
        ds_target = None

        # Sender: is row 1 always better than row 0 regardless of B's action?
        if payoff_sender[1, 0] > payoff_sender[0, 0] and payoff_sender[1, 1] > payoff_sender[0, 1]:
            ds_sender = "Sanction"
        elif payoff_sender[0, 0] > payoff_sender[1, 0] and payoff_sender[0, 1] > payoff_sender[1, 1]:
            ds_sender = "Negotiate"

        # Target: is column 1 always better than column 0?
        if payoff_target[0, 1] > payoff_target[0, 0] and payoff_target[1, 1] > payoff_target[1, 0]:
            ds_target = "Defy"
        elif payoff_target[0, 0] > payoff_target[0, 1] and payoff_target[1, 0] > payoff_target[1, 1]:
            ds_target = "Comply"

        return {
            "payoff_sender": payoff_sender,
            "payoff_target": payoff_target,
            "nash_result": nash,
            "dominant_strategy_sender": ds_sender,
            "dominant_strategy_target": ds_target,
        }


class ElectionCycleModel:
    """
    Models political business cycle effects on financial markets.
    """

    def pre_election_boost(
        self,
        historical_returns: np.ndarray,
        months_before_election: int = 6,
    ) -> Dict[str, float]:
        """
        Estimate the pre-election market boost effect.

        Compares average returns in the months before elections
        to the overall average.

        Parameters
        ----------
        historical_returns : ndarray of shape (T,)
            Monthly market returns.
        months_before_election : int
            Number of months before election to analyse.

        Returns
        -------
        dict with keys:
            'pre_election_mean' : float, mean return in pre-election months
            'overall_mean'      : float, overall mean return
            'boost'             : float, difference (pre-election - overall)
            'boost_annualised'  : float, annualised boost
            't_statistic'       : float, t-statistic of the difference
        """
        returns = np.asarray(historical_returns, dtype=float)
        T = len(returns)

        if T == 0:
            return {"pre_election_mean": 0.0, "overall_mean": 0.0,
                    "boost": 0.0, "boost_annualised": 0.0, "t_statistic": 0.0}

        overall_mean = float(np.mean(returns))
        overall_std = float(np.std(returns, ddof=1))

        # Simulate pre-election periods (every 48 months = 4-year cycle)
        cycle_length = 48
        pre_election_returns = []
        for start in range(0, T - months_before_election, cycle_length):
            pre_election_returns.extend(returns[start:start + months_before_election].tolist())

        if not pre_election_returns:
            pre_election_mean = overall_mean
            t_stat = 0.0
        else:
            pre_election_returns = np.array(pre_election_returns)
            pre_election_mean = float(np.mean(pre_election_returns))
            n_pe = len(pre_election_returns)
            if overall_std > 1e-10:
                t_stat = (pre_election_mean - overall_mean) / (overall_std / np.sqrt(n_pe))
            else:
                t_stat = 0.0

        boost = pre_election_mean - overall_mean
        boost_annualised = boost * 12

        return {
            "pre_election_mean": pre_election_mean,
            "overall_mean": overall_mean,
            "boost": boost,
            "boost_annualised": boost_annualised,
            "t_statistic": float(t_stat),
        }

    def post_election_adjustment(
        self,
        historical_returns: np.ndarray,
        months_after_election: int = 6,
    ) -> Dict[str, float]:
        """
        Estimate post-election market adjustment.

        Parameters
        ----------
        historical_returns : ndarray of shape (T,)
            Monthly market returns.
        months_after_election : int
            Months after election to analyse.

        Returns
        -------
        dict with keys:
            'post_election_mean': float
            'overall_mean'      : float
            'adjustment'        : float, post-election - overall
            't_statistic'       : float
        """
        returns = np.asarray(historical_returns, dtype=float)
        T = len(returns)

        if T == 0:
            return {"post_election_mean": 0.0, "overall_mean": 0.0,
                    "adjustment": 0.0, "t_statistic": 0.0}

        overall_mean = float(np.mean(returns))
        overall_std = float(np.std(returns, ddof=1))

        cycle_length = 48
        post_election_returns = []
        # Post-election months start right after the pre-election period
        for start in range(months_before_election if 'months_before_election' in dir() else 6,
                            T - months_after_election, cycle_length):
            post_election_returns.extend(returns[start:start + months_after_election].tolist())

        # Simpler approach: offset by months_after_election from each cycle start
        post_election_returns = []
        election_offset = 6  # assume election at month 6 of cycle
        for cycle_start in range(0, T, cycle_length):
            pe_start = cycle_start + election_offset
            pe_end = min(pe_start + months_after_election, T)
            if pe_end > pe_start:
                post_election_returns.extend(returns[pe_start:pe_end].tolist())

        if not post_election_returns:
            post_election_mean = overall_mean
            t_stat = 0.0
        else:
            post_election_returns = np.array(post_election_returns)
            post_election_mean = float(np.mean(post_election_returns))
            n_pe = len(post_election_returns)
            if overall_std > 1e-10:
                t_stat = (post_election_mean - overall_mean) / (overall_std / np.sqrt(n_pe))
            else:
                t_stat = 0.0

        adjustment = post_election_mean - overall_mean

        return {
            "post_election_mean": post_election_mean,
            "overall_mean": overall_mean,
            "adjustment": adjustment,
            "t_statistic": float(t_stat),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("political_risk.py — Demo")
    print("=" * 60)

    # --- Political Risk Score ---
    print("\n--- Political Risk Score ---")
    prs = PoliticalRiskScore(weights={"economic": 0.4, "political": 0.35, "financial": 0.25})

    countries = {
        "Country A": {
            "economic": {"GDP growth": 75, "inflation": 60, "unemployment": 70},
            "political": {"stability": 80, "corruption": 55, "rule_of_law": 70},
            "financial": {"current_account": 65, "fx_reserves": 80, "debt_ratio": 50},
        },
        "Country B": {
            "economic": {"GDP growth": 40, "inflation": 30, "unemployment": 35},
            "political": {"stability": 25, "corruption": 20, "rule_of_law": 30},
            "financial": {"current_account": 30, "fx_reserves": 25, "debt_ratio": 85},
        },
    }

    composite_scores = {}
    for name, data in countries.items():
        result = prs.compute(data["economic"], data["political"], data["financial"])
        composite_scores[name] = result["composite_score"]
        print(f"  {name}: composite={result['composite_score']:.1f}, rating={result['risk_rating']}")

    ranking = prs.country_comparison(composite_scores)
    print(f"  Ranking (lowest risk first): {[c for c, _ in ranking]}")

    # --- Sanction Impact Model ---
    print("\n--- Sanction Impact Model ---")
    sim = SanctionImpactModel()

    gdp_impact = sim.estimate_gdp_impact(trade_dependency=0.4, sanction_severity=0.3, duration=10)
    print(f"  GDP impact over 10 years: {gdp_impact['total_loss']:.2f}% total loss")
    print(f"  Year 1 annual loss: {gdp_impact['annual_loss'][0]:.2f}%")
    print(f"  Year 5 annual loss: {gdp_impact['annual_loss'][4]:.2f}%")

    # Supply chain
    import_shares = np.array([
        [0.1, 0.3, 0.05, 0.15],  # Sector 1
        [0.05, 0.2, 0.4, 0.1],   # Sector 2
        [0.15, 0.1, 0.1, 0.2],   # Sector 3
    ])
    sanction_targets = np.array([0, 1, 1, 0])  # Countries 2 and 3 sanctioned
    sc = sim.supply_chain_disruption(import_shares, sanction_targets)
    print(f"  Sector impacts: {sc['sector_impact']}")
    print(f"  Total economy exposure: {sc['total_exposure']:.1%}")

    # Currency impact
    rng = np.random.default_rng(42)
    capital_flows = rng.normal(2e9, 1e9, 60)
    curr = sim.currency_impact(capital_flows, sanction_probability=0.6)
    print(f"  Expected currency pressure: {curr['expected_pressure']:.2f}%")
    print(f"  Tail risk (95%): {curr['tail_risk']:.2f}%")

    # --- Geopolitical Game Model ---
    print("\n--- Geopolitical Game Model ---")
    ggm = GeopoliticalGameModel()

    # Prisoner's dilemma (clean 2x2)
    pd_a = np.array([[3, 0], [5, 1]])
    pd_b = np.array([[3, 5], [0, 1]])
    nash = ggm.nash_equilibrium_2x2(pd_a, pd_b)
    print(f"  Nash equilibria: {nash['equilibria']}")
    print(f"  Payoffs at equilibria: {nash['payoffs_at_eq']}")

    # Sanction game
    sg = ggm.sanction_game(escalation_cost=2.0, compliance_benefit=1.0, defiance_benefit=3.0)
    print(f"  Sanction game Nash equilibria: {sg['nash_result']['equilibria']}")
    print(f"  Sender dominant strategy: {sg['dominant_strategy_sender']}")
    print(f"  Target dominant strategy: {sg['dominant_strategy_target']}")

    # Sequential game
    def payoff_func(a1, a2):
        table = {(0, 0): (4, 3), (0, 1): (2, 5), (1, 0): (5, 2), (1, 1): (1, 1)}
        return table[(a1, a2)]

    seq = ggm.sequential_game_payoffs(2, 2, payoff_func)
    print(f"  Sequential game: Player 1 chooses action {seq['optimal_a1']}")
    print(f"  Subgame outcomes: {seq['subgame_outcomes']}")

    # --- Election Cycle Model ---
    print("\n--- Election Cycle Model ---")
    ecm = ElectionCycleModel()

    rng2 = np.random.default_rng(42)
    monthly_returns = rng2.normal(0.005, 0.04, 480)  # 40 years of monthly returns
    # Add pre-election boost
    for cycle in range(10):
        idx = cycle * 48
        monthly_returns[idx:idx + 6] += 0.01  # 1% monthly boost before election

    pre = ecm.pre_election_boost(monthly_returns, months_before_election=6)
    print(f"  Pre-election mean return: {pre['pre_election_mean']:.4f}")
    print(f"  Overall mean return: {pre['overall_mean']:.4f}")
    print(f"  Pre-election boost: {pre['boost']:.4f} ({pre['boost_annualised']:.2f}% annualised)")
    print(f"  T-statistic: {pre['t_statistic']:.2f}")

    post = ecm.post_election_adjustment(monthly_returns, months_after_election=6)
    print(f"  Post-election mean return: {post['post_election_mean']:.4f}")
    print(f"  Post-election adjustment: {post['adjustment']:.4f}")
    print(f"  T-statistic: {post['t_statistic']:.2f}")

    print("\n[DONE]")
