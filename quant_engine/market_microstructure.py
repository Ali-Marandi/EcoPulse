"""
Market Microstructure & Asymmetric Information Models
=====================================================
Implements key models from market microstructure theory, mechanism design,
IPO auction theory, and the three pillars of asymmetric information economics:
Akerlof's Lemons, Spence Signalling, and Stiglitz Screening.

Mathematical foundations
-----------------------
1. **Nash Equilibrium in Market Making**:  r_t = S_t - q_t * gamma * sigma^2 * (T-t)
   The market maker adjusts the reservation price inversely to inventory.

2. **Glosten-Milgrom Spread**:  s = P(informed | buy) * (V_high - V_low) / (1 - P(informed | buy))
   Adverse selection component of the bid-ask spread.

3. **Vickrey (Second-Price) Auction**:  dominant strategy is truthful bidding.

4. **Akerlof Quality Collapse**:  if quality is unobservable, average quality
   falls as price falls, potentially collapsing the market.

5. **Spence Separating Equilibrium**:  education level e* such that
   high-type finds it affordable but low-type does not.

6. **Stiglitz Screening (Rothschild-Stiglitz)**:  contract menu designed so
   each risk type self-selects.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. Market Making & Nash Equilibrium
# ---------------------------------------------------------------------------

class MarketMakerModel:
    """
    Inventory-based market-making model inspired by Avellaneda-Stoikov.

    The reservation price is:
        r_t = S_t - q_t * gamma * sigma^2 * (T - t)

    where
        S_t   : mid-price
        q_t   : current inventory (positive = long)
        gamma : risk-aversion parameter
        sigma : volatility
        T - t : time remaining in trading horizon

    Parameters
    ----------
    sigma : float
        Annualised volatility of the asset.
    gamma : float
        Risk-aversion coefficient (>= 0).
    T : float
        Trading horizon in years (e.g. 1/252 for one day).
    kappa : float, optional
        Intensity of Poisson order arrivals (orders per unit time).
    A : float, optional
        Maximum probability an order arrives per dt.
    """

    def __init__(
        self,
        sigma: float = 0.2,
        gamma: float = 0.1,
        T: float = 1.0 / 252,
        kappa: float = 1.0,
        A: float = 0.5,
    ):
        self.sigma = sigma
        self.gamma = gamma
        self.T = T
        self.kappa = kappa
        self.A = A

    def reservation_price(self, S: float, q: int, t: float) -> float:
        """Compute the reservation price given mid-price, inventory, and time."""
        dt = max(self.T - t, 1e-12)
        return S - q * self.gamma * self.sigma ** 2 * dt

    def optimal_quotes(
        self, S: float, q: int, t: float
    ) -> Tuple[float, float, float]:
        """
        Compute optimal bid, ask, and half-spread.

        Returns
        -------
        bid, ask, half_spread : tuple of float
        """
        r = self.reservation_price(S, q, t)
        # Avellaneda-Stoikov closed-form half-spread
        delta = r + (1.0 / self.gamma) * np.log(1.0 + self.gamma * self.kappa / self.A)
        half_spread = 0.5 * self.sigma * np.sqrt(self.T - max(t, 0))
        bid = S - half_spread - abs(q) * self.gamma * self.sigma ** 2 * max(self.T - t, 1e-12) * 0.5
        ask = S + half_spread + abs(q) * self.gamma * self.sigma ** 2 * max(self.T - t, 1e-12) * 0.5
        return bid, ask, (ask - bid) / 2.0

    def inventory_trajectory(
        self, S0: float, q0: int, n_steps: int = 100, seed: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """
        Simulate inventory and PnL over the trading horizon.

        Returns dict with keys: time, inventory, mid_price, bid, ask, pnl.
        """
        rng = np.random.default_rng(seed)
        dt = self.T / n_steps
        times = np.linspace(0, self.T, n_steps + 1)
        inventory = np.zeros(n_steps + 1, dtype=int)
        mid = np.zeros(n_steps + 1)
        bids = np.zeros(n_steps + 1)
        asks = np.zeros(n_steps + 1)
        pnl = np.zeros(n_steps + 1)

        inventory[0] = q0
        mid[0] = S0
        bid, ask, _ = self.optimal_quotes(S0, q0, 0)
        bids[0] = bid
        asks[0] = ask

        cash = 0.0
        for i in range(n_steps):
            # Geometric Brownian motion for mid-price
            dW = rng.normal(0, np.sqrt(dt))
            mid[i + 1] = mid[i] * np.exp(-0.5 * self.sigma ** 2 * dt + self.sigma * dW)

            # Order arrival (Poisson)
            if rng.random() < self.kappa * dt:
                side = 1 if rng.random() < 0.5 else -1  # buy or sell
                bid_i, ask_i, _ = self.optimal_quotes(mid[i], inventory[i], times[i])
                if side == 1:  # market buy -> we sell at ask
                    cash += ask_i
                    inventory[i + 1] = inventory[i] - 1
                else:  # market sell -> we buy at bid
                    cash -= bid_i
                    inventory[i + 1] = inventory[i] + 1
            else:
                inventory[i + 1] = inventory[i]

            bids[i + 1], asks[i + 1], _ = self.optimal_quotes(
                mid[i + 1], inventory[i + 1], times[i + 1]
            )
            # Mark-to-market PnL
            pnl[i + 1] = cash + inventory[i + 1] * mid[i + 1]

        return {
            "time": times,
            "inventory": inventory,
            "mid_price": mid,
            "bid": bids,
            "ask": asks,
            "pnl": pnl,
        }


# ---------------------------------------------------------------------------
# 2. Adverse-Selection Spread (Glosten-Milgrom)
# ---------------------------------------------------------------------------

class GlostenMilgromSpread:
    """
    Glosten-Milgrom (1985) model of the bid-ask spread under asymmetric
    information.

    The dealer faces three types of traders:
      - Informed traders who know the true value V in {V_L, V_H}
      - Uninformed (liquidity) buyers and sellers

    Key formulae
    ------------
    P(informed | buy) = alpha * 0.5 / [alpha * 0.5 + (1 - alpha) * nu]

    Ask = E[V | buy],  Bid = E[V | sell]
    """

    def __init__(
        self,
        V_low: float = 80.0,
        V_high: float = 120.0,
        prior_high: float = 0.5,
        alpha: float = 0.2,
        nu_buy: float = 0.5,
    ):
        """
        Parameters
        ----------
        V_low, V_high : float
            Possible fundamental values.
        prior_high : float
            Prior probability that V = V_high.
        alpha : float
            Fraction of traders who are informed (0 < alpha < 1).
        nu_buy : float
            Probability an uninformed trader buys (vs sells).
        """
        self.V_L = V_low
        self.V_H = V_high
        self.pi_H = prior_high
        self.alpha = alpha
        self.nu = nu_buy

    def compute_spread(self) -> Dict[str, float]:
        """
        Compute bid, ask, spread, and adverse-selection component.

        Returns
        -------
        dict with keys: bid, ask, spread, mid, adverse_selection_frac,
        informed_given_buy, informed_given_sell
        """
        a = self.alpha
        nu = self.nu
        pi = self.pi_H
        VL, VH = self.V_L, self.V_H

        # P(buy)
        P_buy = a * (pi * 1 + (1 - pi) * 0) + (1 - a) * nu
        # P(sell)
        P_sell = a * (pi * 0 + (1 - pi) * 1) + (1 - a) * (1 - nu)

        # P(informed | buy)
        P_inf_buy = a * pi / P_buy if P_buy > 0 else 0
        # P(informed | sell)
        P_inf_sell = a * (1 - pi) / P_sell if P_sell > 0 else 0

        # E[V | buy]
        E_V_buy = (P_inf_buy * VH + (1 - P_inf_buy) * (pi * VH + (1 - pi) * VL))
        # E[V | sell]
        E_V_sell = (P_inf_sell * VL + (1 - P_inf_sell) * (pi * VH + (1 - pi) * VL))

        ask = E_V_buy
        bid = E_V_sell
        mid = (ask + bid) / 2
        spread = ask - bid

        # Adverse-selection fraction of spread
        E_V_uncond = pi * VH + (1 - pi) * VL
        total_spread = spread
        adverse_selection = abs(E_V_buy - E_V_sell)
        as_frac = adverse_selection / total_spread if total_spread > 0 else 0

        return {
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "mid": mid,
            "adverse_selection_component": adverse_selection,
            "adverse_selection_fraction": as_frac,
            "informed_given_buy": P_inf_buy,
            "informed_given_sell": P_inf_sell,
        }


# ---------------------------------------------------------------------------
# 3. Auction Mechanisms
# ---------------------------------------------------------------------------

@dataclass
class AuctionResult:
    """Result of an auction simulation."""
    winner: str
    winning_bid: float
    second_price: float
    revenue: float
    allocative_efficiency: float  # fraction of max surplus captured
    all_bids: Dict[str, float] = field(default_factory=dict)


class AuctionMechanism:
    """
    Implements common auction mechanisms for IPO / asset allocation.

    Supported types:
    - "vickrey"      : Second-price sealed-bid (dominant strategy: truthful)
    - "first_price"   : First-price sealed-bid (strategic shading)
    - "dutch"         : Descending-price auction
    - "uniform_price" : All winners pay the same clearing price
    """

    def __init__(self, mechanism: str = "vickrey"):
        self.mechanism = mechanism

    def run(
        self, bids: Dict[str, float], reserve_price: float = 0.0
    ) -> AuctionResult:
        """
        Run the auction with the given bids.

        Parameters
        ----------
        bids : dict
            Mapping of bidder_id -> bid_amount.
        reserve_price : float
            Minimum acceptable price.

        Returns
        -------
        AuctionResult
        """
        if not bids:
            raise ValueError("At least one bid is required.")

        # Filter by reserve price
        valid = {k: v for k, v in bids.items() if v >= reserve_price}

        if not valid:
            return AuctionResult(
                winner="none", winning_bid=0, second_price=0,
                revenue=0, allocative_efficiency=0, all_bids=bids,
            )

        sorted_bidders = sorted(valid.items(), key=lambda x: x[1], reverse=True)

        if self.mechanism == "vickrey":
            winner, w_bid = sorted_bidders[0]
            second_price = sorted_bidders[1][1] if len(sorted_bidders) > 1 else reserve_price
            revenue = second_price

        elif self.mechanism == "first_price":
            winner, w_bid = sorted_bidders[0]
            second_price = w_bid  # winner pays own bid
            revenue = w_bid

        elif self.mechanism == "dutch":
            # In Dutch auction, price descends; first to accept wins.
            # We simulate by finding the highest bidder.
            winner, w_bid = sorted_bidders[0]
            second_price = sorted_bidders[1][1] if len(sorted_bidders) > 1 else reserve_price
            revenue = w_bid

        elif self.mechanism == "uniform_price":
            # All winners pay the clearing price (lowest winning bid)
            # Here we just allocate to the single highest bidder.
            winner, w_bid = sorted_bidders[0]
            clearing = sorted_bidders[-1][1]  # lowest winning bid
            second_price = clearing
            revenue = clearing

        else:
            raise ValueError(f"Unknown mechanism: {self.mechanism}")

        # Allocative efficiency: winner's value capture / max possible
        max_surplus = sorted_bidders[0][1] - reserve_price
        captured = max_surplus - (w_bid - second_price) if self.mechanism == "vickrey" else max_surplus - 0
        efficiency = captured / max_surplus if max_surplus > 0 else 0

        return AuctionResult(
            winner=winner, winning_bid=w_bid, second_price=second_price,
            revenue=revenue, allocative_efficiency=efficiency,
            all_bids=bids,
        )


# ---------------------------------------------------------------------------
# 4. Akerlof's Lemons Model
# ---------------------------------------------------------------------------

class AkerlofLemonsModel:
    """
    Akerlof (1970) Market for Lemons.

    When sellers know quality but buyers cannot observe it, the market
    may collapse as average quality falls with price.

    Model
    -----
    - Seller's valuation of a car of quality q is:  v_s(q) = q
    - Buyer's valuation of a car of quality q is:   v_b(q) = alpha * q,  alpha > 1
    - Quality is uniformly distributed on [q_min, q_max].
    - If the market price is P, only sellers with q <= P will sell.
    - The average quality of cars on the market is E[q | q <= P].
    - Buyers pay at most alpha * E[q | q <= P].
    - Equilibrium:  P* = alpha * E[q | q <= P*]
    """

    def __init__(
        self,
        q_min: float = 0.0,
        q_max: float = 100.0,
        buyer_premium: float = 1.5,
        n_price_points: int = 200,
    ):
        self.q_min = q_min
        self.q_max = q_max
        self.alpha = buyer_premium
        self.n = n_price_points

    def average_quality_given_price(self, P: float) -> float:
        """E[q | q <= P] for uniform quality on [q_min, q_max]."""
        P_eff = np.clip(P, self.q_min, self.q_max)
        return (self.q_min + P_eff) / 2.0

    def buyer_willingness(self, P: float) -> float:
        """Maximum price a buyer is willing to pay given market price P."""
        avg_q = self.average_quality_given_price(P)
        return self.alpha * avg_q

    def find_equilibrium(self) -> Dict[str, float]:
        """
        Find the market equilibrium (if any exists).

        Returns
        -------
        dict with keys: equilibrium_price, average_quality, trades, market_collapsed
        """
        prices = np.linspace(self.q_min, self.q_max, self.n)
        buyer_wtp = np.array([self.buyer_willingness(p) for p in prices])

        # Equilibrium where buyer WTP = price
        diff = buyer_wtp - prices

        # Find the highest fixed point
        equilibria = []
        for i in range(len(prices) - 1):
            if diff[i] >= 0 and diff[i + 1] < 0:
                # Linear interpolation
                f1, f2 = diff[i], diff[i + 1]
                p1, p2 = prices[i], prices[i + 1]
                p_star = p1 - f1 * (p2 - p1) / (f2 - f1)
                equilibria.append(p_star)

        if not equilibria:
            # No interior equilibrium: check corner
            if buyer_wtp[0] < prices[0]:
                # Market collapses
                return {
                    "equilibrium_price": 0.0,
                    "average_quality": 0.0,
                    "trades": 0.0,
                    "market_collapsed": True,
                }
            else:
                p_star = prices[-1]
        else:
            p_star = max(equilibria)

        avg_q = self.average_quality_given_price(p_star)
        trade_fraction = (p_star - self.q_min) / (self.q_max - self.q_min) if self.q_max > self.q_min else 0

        return {
            "equilibrium_price": p_star,
            "average_quality": avg_q,
            "trades": trade_fraction,
            "market_collapsed": p_star <= self.q_min * 1.01,
        }

    def quality_vs_price_curve(self) -> Dict[str, np.ndarray]:
        """Return arrays for plotting the quality-price feedback loop."""
        prices = np.linspace(self.q_min, self.q_max, self.n)
        avg_quality = np.array([self.average_quality_given_price(p) for p in prices])
        buyer_wtp = np.array([self.buyer_willingness(p) for p in prices])
        return {
            "price": prices,
            "average_quality": avg_quality,
            "buyer_willingness": buyer_wtp,
        }


# ---------------------------------------------------------------------------
# 5. Spence Signalling Model
# ---------------------------------------------------------------------------

class SpenceSignallingModel:
    """
    Spence (1973) Job-Market Signalling.

    Two types of workers:
      - High ability:  productivity = theta_H, cost of education = c_H * e
      - Low  ability:  productivity = theta_L, cost of education = c_L * e

    with theta_H > theta_L and c_H < c_L  (education is cheaper for high type).

    A separating equilibrium exists when:
        e* in [w_L * delta / c_L,  w_H * delta / c_H)
    where delta = theta_H - theta_L.
    """

    def __init__(
        self,
        theta_high: float = 2.0,
        theta_low: float = 1.0,
        c_high: float = 0.5,
        c_low: float = 1.5,
        frac_high: float = 0.5,
    ):
        self.theta_H = theta_high
        self.theta_L = theta_low
        self.c_H = c_high
        self.c_L = c_low
        self.pi = frac_high  # prior fraction of high type

    def separating_equilibrium(self) -> Dict[str, float]:
        """
        Compute the range of education levels that sustain a separating
        equilibrium.

        Returns
        -------
        dict with: e_min, e_max, wage_high, wage_low, exists (bool)
        """
        w_H = self.theta_H
        w_L = self.theta_L
        delta = w_H - w_L

        e_min = w_L * delta / self.c_L if self.c_L > 0 else float("inf")
        e_max = w_H * delta / self.c_H if self.c_H > 0 else float("inf")

        exists = e_min < e_max and e_max > 0

        # Pick a midpoint education level as the threshold
        e_star = (e_min + e_max) / 2 if exists else 0

        return {
            "e_min": e_min,
            "e_max": e_max,
            "e_star": e_star,
            "wage_high": w_H,
            "wage_low": w_L,
            "separating_exists": exists,
            "productivity_gap": delta,
        }

    def pooling_wage(self) -> float:
        """Compute the wage in a pooling equilibrium (average productivity)."""
        return self.pi * self.theta_H + (1 - self.pi) * self.theta_L

    def signalling_cost_curve(
        self, max_e: float = 10.0, n_points: int = 100
    ) -> Dict[str, np.ndarray]:
        """Return education level vs. net benefit for each type."""
        e_arr = np.linspace(0, max_e, n_points)
        # Net benefit = wage - education_cost
        w_pool = self.pooling_wage()
        net_high = np.full(n_points, self.theta_H) - self.c_H * e_arr
        net_low = np.full(n_points, self.theta_L) - self.c_L * e_arr
        return {
            "education": e_arr,
            "net_benefit_high": net_high,
            "net_benefit_low": net_low,
            "pooling_wage": w_pool,
        }


# ---------------------------------------------------------------------------
# 6. Stiglitz Screening (Rothschild-Stiglitz Insurance Model)
# ---------------------------------------------------------------------------

class RothschildStiglitzScreening:
    """
    Rothschild-Stiglitz (1976) competitive insurance screening model.

    Two risk types with different loss probabilities:
      - Low-risk:  loss probability = p_L
      - High-risk: loss probability = p_H > p_L

    Insurance contract: (premium, coverage) = (pi, q)
    Full insurance: q = L (loss amount), then pi = p * L.

    A separating equilibrium has:
      - High-risk gets full insurance at p_H * L
      - Low-risk gets partial coverage (q* < L) at a lower premium
    """

    def __init__(
        self,
        loss_amount: float = 100.0,
        p_low: float = 0.1,
        p_high: float = 0.3,
        frac_low: float = 0.6,
        risk_aversion: float = 1.0,
    ):
        self.L = loss_amount
        self.p_L = p_low
        self.p_H = p_high
        self.alpha = frac_low  # fraction of low-risk
        self.risk_aversion = risk_aversion

    def full_insurance_premium(self, p: float) -> float:
        """Actuarially fair full-insurance premium for risk type p."""
        return p * self.L

    def expected_utility(
        self, p: float, premium: float, coverage: float
    ) -> float:
        """
        Expected utility with CARA utility: U(W) = -exp(-rho * W).

        Wealth states:  W - premium (no loss)  or  W - premium - L + coverage (loss).
        """
        rho = self.risk_aversion
        W = 200.0  # normalised initial wealth
        no_loss_util = -np.exp(-rho * (W - premium))
        loss_util = -np.exp(-rho * (W - premium - self.L + coverage))
        return (1 - p) * no_loss_util + p * loss_util

    def separating_equilibrium(self) -> Dict[str, float]:
        """
        Find the low-risk contract (pi_L, q_L) in the separating equilibrium.

        The high-risk gets (p_H * L, L).
        The low-risk contract must:
          1. Satisfy IR:  EU_low(pi_L, q_L) >= EU_low(0, 0)
          2. Satisfy IC:  EU_high(p_H*L, L) >= EU_high(pi_L, q_L)

        We solve for the maximum q_L < L such that the IC binds.
        """
        pi_H = self.full_insurance_premium(self.p_H)
        EU_H_full = self.expected_utility(self.p_H, pi_H, self.L)
        EU_L_no_ins = self.expected_utility(self.p_L, 0, 0)

        # Search for the coverage level where high-type is indifferent
        best = None
        for q in np.linspace(0.01 * self.L, 0.99 * self.L, 200):
            # IC: high type must prefer their contract
            # Solve for premium that makes high type indifferent
            for pi_try in np.linspace(0.01 * self.L, pi_H - 0.01, 200):
                EU_H_try = self.expected_utility(self.p_H, pi_try, q)
                if EU_H_try >= EU_H_full - 1e-6:
                    # High type would deviate; too generous
                    continue
            # Try actuarially fair for low risk at this coverage
            pi_fair = self.p_L * q
            if pi_fair <= 0:
                continue
            EU_L_try = self.expected_utility(self.p_L, pi_fair, q)
            if EU_L_try >= EU_L_no_ins - 1e-6:
                if best is None or q > best["q_L"]:
                    best = {"pi_L": pi_fair, "q_L": q}

        if best is None:
            best = {"pi_L": 0.0, "q_L": 0.0}

        best.update({
            "pi_H": pi_H,
            "q_H": self.L,
            "separating_exists": best["q_L"] > 0.01 * self.L,
        })
        return best

    def pooling_contract(self) -> Dict[str, float]:
        """Compute the pooling contract (single contract for both types)."""
        p_avg = self.alpha * self.p_L + (1 - self.alpha) * self.p_H
        pi_pool = p_avg * self.L
        return {
            "premium": pi_pool,
            "coverage": self.L,
            "p_average": p_avg,
        }


# ---------------------------------------------------------------------------
# 7. Mechanism Design Score
# ---------------------------------------------------------------------------

class MechanismDesignAnalyzer:
    """
    Analyzes market mechanism properties: allocative efficiency,
    revenue equivalence, incentive compatibility.

    Useful for evaluating exchange rules, IPO mechanisms, and
    order-matching algorithms.
    """

    @staticmethod
    def revenue_equivalence_check(mechanism_a: AuctionResult, mechanism_b: AuctionResult) -> Dict[str, float]:
        """
        Check if Revenue Equivalence Theorem approximately holds.
        Under standard assumptions (risk-neutral bidders, independent
        private values, symmetric), expected revenue should be the same
        across standard auctions.
        """
        return {
            "revenue_A": mechanism_a.revenue,
            "revenue_B": mechanism_b.revenue,
            "difference": abs(mechanism_a.revenue - mechanism_b.revenue),
            "pct_difference": abs(mechanism_a.revenue - mechanism_b.revenue)
                           / max(mechanism_a.revenue, 1e-12) * 100,
        }

    @staticmethod
    def winner_curse_bid_adjustment(
        n_bidders: int, value_std: float, n_simulations: int = 10000, seed: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Estimate the Winner's Curse effect via simulation.

        Each bidder observes a noisy signal of the true value:
            signal_i = true_value + noise_i
        The winner is the most optimistic bidder.

        Returns estimated overpayment and optimal shading factor.
        """
        rng = np.random.default_rng(seed)
        true_values = rng.normal(100, value_std, n_simulations)
        overpayments = []

        for v in true_values:
            signals = rng.normal(v, value_std * 0.5, n_bidders)
            winner_idx = np.argmax(signals)
            overpayments.append(signals[winner_idx] - v)

        avg_overpayment = np.mean(overpayments)
        optimal_shade = avg_overpayment / 100.0  # fraction of signal to shade

        return {
            "average_overpayment": avg_overpayment,
            "optimal_bid_shading_fraction": optimal_shade,
            "winner_curse_severity": avg_overpayment / value_std,
        }
