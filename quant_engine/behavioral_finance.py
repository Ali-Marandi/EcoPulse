"""
behavioral_finance.py — Behavioral Finance Models
===================================================
Provides models grounded in behavioural economics for the EcoPulse quant engine:

* **ProspectTheory**       — Kahneman–Tversky value function & probability weighting
* **DispositionEffect**    — Tendency to sell winners early, hold losers late
* **HerdingModel**         — Banerjee-style sequential herding decisions
* **OverconfidenceBias**   — Overconfidence effects on trading volume & returns

Dependencies: numpy only.
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple


class ProspectTheory:
    """
    Kahneman–Tversky prospect theory model.

    Value function (S-shaped, reference-dependent):
        v(x) =  x**beta           if x >= 0   (gains)
        v(x) = -lambda * |x|**alpha  if x < 0    (losses)

    Probability weighting function (Tversky-Kahneman):
        w(p) = p**delta / (p**delta + (1-p)**delta)**(1/delta)

    Parameters
    ----------
    alpha : float
        Loss aversion exponent (curvature for losses). Typical 0.88.
    beta : float
        Gain exponent (curvature for gains). Typical 0.88.
    lambda_ : float
        Loss aversion coefficient. Typical 2.25 (losses loom larger than gains).
    """

    def __init__(
        self,
        alpha: float = 0.88,
        beta: float = 0.88,
        lambda_: float = 2.25,
    ) -> None:
        if alpha <= 0 or beta <= 0:
            raise ValueError("Exponents alpha and beta must be positive.")
        if lambda_ < 1.0:
            raise ValueError("Loss aversion coefficient lambda_ must be >= 1.")
        self.alpha = alpha
        self.beta = beta
        self.lambda_ = lambda_

    def value_function(self, x: float | np.ndarray) -> float | np.ndarray:
        """
        Compute the prospect-theory value for outcome(s) *x*.

        Parameters
        ----------
        x : float or ndarray
            Gains (x > 0) or losses (x < 0) relative to the reference point.

        Returns
        -------
        float or ndarray
            Subjective value(s).
        """
        x = np.asarray(x, dtype=float)
        gains = np.where(x >= 0, np.power(np.abs(x), self.beta), 0.0)
        losses = np.where(x < 0, -self.lambda_ * np.power(np.abs(x), self.alpha), 0.0)
        return gains + losses

    def probability_weight(self, p: float | np.ndarray) -> float | np.ndarray:
        """
        Compute decision weights from objective probabilities.

        Uses a Tversky–Kahneman weighting function:
            w(p) = p**delta / (p**delta + (1-p)**delta)**(1/delta)
        with delta chosen so that small probabilities are overweighted.

        Parameters
        ----------
        p : float or ndarray
            Objective probability/ies in [0, 1].

        Returns
        -------
        float or ndarray
            Subjective decision weight(s).
        """
        p = np.asarray(p, dtype=float)
        p = np.clip(p, 1e-10, 1.0 - 1e-10)
        delta = 0.61  # Tversky & Kahneman (1992) estimate
        p_d = np.power(p, delta)
        one_minus_p_d = np.power(1.0 - p, delta)
        return p_d / np.power(p_d + one_minus_p_d, 1.0 / delta)

    def weighted_value(
        self,
        outcomes: np.ndarray,
        probabilities: np.ndarray,
    ) -> float:
        """
        Compute the prospect-theory weighted value of a lottery.

        V = sum_i w(p_i) * v(x_i)

        Parameters
        ----------
        outcomes : ndarray of shape (n,)
            Possible outcomes (gains/losses).
        probabilities : ndarray of shape (n,)
            Corresponding objective probabilities (must sum to 1).

        Returns
        -------
        float
            Expected prospect-theory value.
        """
        outcomes = np.asarray(outcomes, dtype=float)
        probabilities = np.asarray(probabilities, dtype=float)
        if len(outcomes) != len(probabilities):
            raise ValueError("outcomes and probabilities must have the same length.")
        if not np.allclose(probabilities.sum(), 1.0, atol=1e-6):
            raise ValueError("Probabilities must sum to 1.")
        w = self.probability_weight(probabilities)
        v = self.value_function(outcomes)
        return float(np.dot(w, v))


class DispositionEffect:
    """
    Models the disposition effect: investors sell winning positions too early
    and hold losing positions too long.
    """

    def __init__(self, sale_propensity_win: float = 0.70, sale_propensity_loss: float = 0.20) -> None:
        """
        Parameters
        ----------
        sale_propensity_win : float
            Probability of selling a winning trade each period.
        sale_propensity_loss : float
            Probability of selling a losing trade each period.
        """
        self.sale_propensity_win = np.clip(sale_propensity_win, 0, 1)
        self.sale_propensity_loss = np.clip(sale_propensity_loss, 0, 1)

    def simulate_trading(
        self,
        winning_trades: np.ndarray,
        losing_trades: np.ndarray,
        holding_period_win: int = 5,
        holding_period_loss: int = 5,
    ) -> dict:
        """
        Simulate trading with disposition-effect bias.

        Parameters
        ----------
        winning_trades : ndarray of shape (n_win,)
            Daily P&L for each winning trade (all positive).
        losing_trades : ndarray of shape (n_loss,)
            Daily P&L for each losing trade (all negative).
        holding_period_win : int
            Optimal holding period for winners.
        holding_period_loss : int
            Optimal holding period for losers.

        Returns
        -------
        dict with keys:
            'realized_pnl'    : total P&L actually realized
            'optimal_pnl'     : total P&L if held optimally
            'disposition_cost': P&L lost due to the bias
            'winners_sold_early': count of winners sold before optimal
            'losers_held_late'  : count of losers held beyond optimal
        """
        winning_trades = np.asarray(winning_trades, dtype=float)
        losing_trades = np.asarray(losing_trades, dtype=float)
        rng = np.random.default_rng(42)

        realized_pnl = 0.0
        optimal_pnl = 0.0
        winners_sold_early = 0
        losers_held_late = 0

        # Process winners
        for trade_daily in winning_trades:
            optimal_pnl += trade_daily * holding_period_win
            cumulative = 0.0
            for day in range(holding_period_win):
                cumulative += trade_daily
                if rng.random() < self.sale_propensity_win:
                    realized_pnl += cumulative
                    if day < holding_period_win - 1:
                        winners_sold_early += 1
                    break
            else:
                realized_pnl += cumulative

        # Process losers
        for trade_daily in losing_trades:
            optimal_pnl += trade_daily * min(holding_period_loss, 1)  # optimal: cut at day 1
            cumulative = 0.0
            for day in range(holding_period_loss):
                cumulative += trade_daily
                if rng.random() < self.sale_propensity_loss:
                    realized_pnl += cumulative
                    if day > 0:
                        losers_held_late += 1
                    break
            else:
                realized_pnl += cumulative
                if holding_period_loss > 0:
                    losers_held_late += 1

        return {
            "realized_pnl": realized_pnl,
            "optimal_pnl": optimal_pnl,
            "disposition_cost": realized_pnl - optimal_pnl,
            "winners_sold_early": winners_sold_early,
            "losers_held_late": losers_held_late,
        }


class HerdingModel:
    """
    Banerjee-style sequential decision-making herding model.

    Agents observe previous decisions and a private signal about an
    investment's quality, then decide whether to invest (1) or not (0).
    Information cascades can form when agents ignore their private
    signal and follow the crowd.
    """

    def __init__(self, precision: float = 2.0) -> None:
        """
        Parameters
        ----------
        precision : float
            Precision of private signals (higher = more informative).
        """
        self.precision = precision

    def simulate_decisions(
        self,
        n_agents: int = 20,
        true_quality_prior: float = 0.5,
        information_precision: float | None = None,
    ) -> dict:
        """
        Simulate sequential investment decisions under herding.

        Parameters
        ----------
        n_agents : int
            Number of agents making decisions sequentially.
        true_quality_prior : float
            Prior probability the investment is good (0.5 = uninformative).
        information_precision : float or None
            Signal precision. If None, uses self.precision.

        Returns
        -------
        dict with keys:
            'decisions'      : ndarray of 0/1 decisions
            'signals'        : ndarray of private signals (+1 or -1)
            'cascade_start'  : int, period when cascade began (n_agents if no cascade)
            'cascade_direction': int, 1=invest cascade, 0=abstain cascade, -1=none
            'true_quality'   : int, actual quality (1=good, 0=bad)
            'efficiency'     : float, fraction of correct decisions
        """
        if information_precision is None:
            information_precision = self.precision

        rng = np.random.default_rng(99)
        true_quality = 1 if rng.random() < true_quality_prior else 0

        decisions = np.zeros(n_agents, dtype=int)
        signals = np.zeros(n_agents, dtype=int)

        # Bayesian posterior tracking: log-odds that quality=1
        # Prior: P(Q=1) = prior => log-odds = log(prior/(1-prior))
        if true_quality_prior <= 0 or true_quality_prior >= 1:
            log_odds = 0.0
        else:
            log_odds = np.log(true_quality_prior / (1.0 - true_quality_prior))

        cascade_start = n_agents
        cascade_direction = -1
        cascade_formed = False

        for i in range(n_agents):
            # Generate private signal: P(signal=+1 | Q=1) = precision/(1+precision)
            if true_quality == 1:
                p_signal_pos = information_precision / (1.0 + information_precision)
            else:
                p_signal_pos = 1.0 / (1.0 + information_precision)

            signal = 1 if rng.random() < p_signal_pos else -1
            signals[i] = signal

            if not cascade_formed:
                # Update posterior
                if signal == 1:
                    log_odds += np.log(information_precision)
                else:
                    log_odds -= np.log(information_precision)

                # Decision based on posterior
                prob_good = 1.0 / (1.0 + np.exp(-log_odds))
                decision = 1 if prob_good > 0.5 else 0
                decisions[i] = decision

                # Check if cascade forms: if the running vote tally makes
                # private signal unable to sway the posterior across 0.5
                invest_count = int(np.sum(decisions[:i + 1]))
                abstain_count = i + 1 - invest_count
                # Cascade forms if |invest - abstain| >= 2 and agent i+1's signal
                # can't flip the majority
                if abs(invest_count - abstain_count) >= 2:
                    cascade_formed = True
                    cascade_start = i + 1
                    cascade_direction = 1 if invest_count > abstain_count else 0
            else:
                # In cascade: follow the crowd
                decisions[i] = cascade_direction

        efficiency = np.mean(decisions == true_quality)

        return {
            "decisions": decisions,
            "signals": signals,
            "cascade_start": cascade_start,
            "cascade_direction": cascade_direction,
            "true_quality": true_quality,
            "efficiency": efficiency,
        }


class OverconfidenceBias:
    """
    Models how overconfidence affects trading behaviour.

    Overconfident traders: (a) trade too frequently, increasing costs;
    (b) underestimate variance, leading to excessive portfolio concentration.
    """

    def __init__(self, transaction_cost: float = 0.001) -> None:
        """
        Parameters
        ----------
        transaction_cost : float
            Per-trade cost as a fraction of portfolio value.
        """
        self.transaction_cost = transaction_cost

    def simulate_portfolio(
        self,
        true_returns: np.ndarray,
        confidence_level: float = 1.5,
        n_periods: int | None = None,
    ) -> dict:
        """
        Simulate the impact of overconfidence on a portfolio.

        Overconfident traders trade more frequently (turnover scales with
        confidence) and concentrate their portfolio more heavily.

        Parameters
        ----------
        true_returns : ndarray of shape (T,)
            True asset returns for each period.
        confidence_level : float
            Degree of overconfidence (1.0 = rational, >1 = overconfident).
        n_periods : int or None
            Number of periods to simulate. If None, uses len(true_returns).

        Returns
        -------
        dict with keys:
            'optimal_path' : ndarray of optimal portfolio values
            'biased_path'  : ndarray of overconfident portfolio values
            'excess_turnover': float, average excess turnover due to overconfidence
            'final_gap'    : float, difference in final portfolio values
        """
        true_returns = np.asarray(true_returns, dtype=float)
        if n_periods is None:
            n_periods = len(true_returns)
        else:
            n_periods = min(n_periods, len(true_returns))

        # Base turnover: rational investor rebalances infrequently
        base_turnover = 0.1  # 10% quarterly rebalancing
        rng = np.random.default_rng(77)

        optimal_path = np.ones(n_periods)
        biased_path = np.ones(n_periods)

        turnover_list = []

        for t in range(1, n_periods):
            r = true_returns[t]

            # Optimal: low turnover, diversified
            optimal_turnover = base_turnover * (0.5 + 0.5 * rng.random())
            tc_optimal = optimal_turnover * self.transaction_cost
            optimal_path[t] = optimal_path[t - 1] * (1.0 + r - tc_optimal)

            # Biased: higher turnover (overconfident), worse signal noise
            biased_turnover = base_turnover * confidence_level * (0.5 + 0.5 * rng.random())
            # Overconfident traders also suffer from worse entry timing
            noise = rng.normal(0, 0.005 * confidence_level)
            tc_biased = biased_turnover * self.transaction_cost
            # Concentration risk: variance scales with confidence
            concentration_penalty = 0.002 * (confidence_level - 1.0) * rng.random()
            biased_path[t] = biased_path[t - 1] * (1.0 + r + noise - tc_biased - concentration_penalty)

            turnover_list.append(biased_turnover - optimal_turnover)

        return {
            "optimal_path": optimal_path,
            "biased_path": biased_path,
            "excess_turnover": float(np.mean(turnover_list)),
            "final_gap": float(biased_path[-1] - optimal_path[-1]),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("behavioral_finance.py — Demo")
    print("=" * 60)

    # --- Prospect Theory ---
    print("\n--- Prospect Theory ---")
    pt = ProspectTheory(alpha=0.88, beta=0.88, lambda_=2.25)
    test_outcomes = np.array([-100, -50, 0, 50, 100])
    values = pt.value_function(test_outcomes)
    print("  Value function:")
    for x, v in zip(test_outcomes, values):
        print(f"    x={x:>6} => v={v:>10.2f}")

    test_probs = np.array([0.05, 0.20, 0.50, 0.20, 0.05])
    weights = pt.probability_weight(test_probs)
    print("  Probability weighting:")
    for p, w in zip(test_probs, weights):
        print(f"    p={p:.2f} => w={w:.4f}")

    wv = pt.weighted_value(test_outcomes, test_probs)
    print(f"  Weighted value of lottery: {wv:.4f}")

    # --- Disposition Effect ---
    print("\n--- Disposition Effect ---")
    de = DispositionEffect(sale_propensity_win=0.70, sale_propensity_loss=0.20)
    rng = np.random.default_rng(10)
    winners = np.abs(rng.normal(50, 20, 30))  # 30 winning trades
    losers = -np.abs(rng.normal(30, 15, 30))  # 30 losing trades
    result = de.simulate_trading(winners, losers, holding_period_win=5, holding_period_loss=5)
    print(f"  Realized P&L:  ${result['realized_pnl']:.2f}")
    print(f"  Optimal P&L:   ${result['optimal_pnl']:.2f}")
    print(f"  Disposition cost: ${result['disposition_cost']:.2f}")
    print(f"  Winners sold early: {result['winners_sold_early']}")
    print(f"  Losers held late:   {result['losers_held_late']}")

    # --- Herding Model ---
    print("\n--- Herding Model ---")
    hm = HerdingModel(precision=2.0)
    herd = hm.simulate_decisions(n_agents=20, true_quality_prior=0.5, information_precision=2.0)
    print(f"  True quality: {'Good' if herd['true_quality'] == 1 else 'Bad'}")
    print(f"  Decisions: {herd['decisions'].tolist()}")
    print(f"  Cascade start: agent {herd['cascade_start']}")
    print(f"  Cascade direction: {herd['cascade_direction']}")
    print(f"  Decision efficiency: {herd['efficiency']:.1%}")

    # --- Overconfidence Bias ---
    print("\n--- Overconfidence Bias ---")
    ob = OverconfidenceBias(transaction_cost=0.001)
    rng2 = np.random.default_rng(10)
    true_rets = rng2.normal(0.0005, 0.02, 252)  # daily returns, 1 year
    res = ob.simulate_portfolio(true_rets, confidence_level=2.0)
    print(f"  Optimal final value: ${res['optimal_path'][-1]:.4f}")
    print(f"  Biased final value:  ${res['biased_path'][-1]:.4f}")
    print(f"  Final gap: ${res['final_gap']:.4f}")
    print(f"  Avg excess turnover: {res['excess_turnover']:.4f}")

    print("\n[DONE]")
