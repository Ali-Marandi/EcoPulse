r"""
contagion_network.py — Financial Contagion & Network Risk
============================================================
Models systemic risk through network topology for the EcoPulse quant engine:

* **FinancialNetwork**  — Interbank lending network, cascading defaults, SIFI detection
* **CorrelationNetwork** — Dynamic correlation-based asset networks, community detection
* **DebtRank**         — Battiston et al. (2012) systemic importance algorithm

Dependencies: numpy, scipy.sparse.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    from scipy import sparse
    from scipy.sparse.linalg import eigsh
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class FinancialNetwork:
    """
    Models an interbank lending network as a directed graph (adjacency matrix).

    Banks are nodes. Edge (i, j) means bank *i* has lent to bank *j*.
    The weight is the exposure amount.
    """

    def __init__(self, n_banks: int, connectivity_prob: float = 0.15, seed: int = 42) -> None:
        """
        Create a random Erdos–Renyi interbank network.

        Parameters
        ----------
        n_banks : int
            Number of banks in the network.
        connectivity_prob : float
            Probability of a directed edge between any two banks.
        seed : int
            Random seed for reproducibility.
        """
        self.n_banks = n_banks
        self.connectivity_prob = connectivity_prob
        self.rng = np.random.default_rng(seed)

        # Capital for each bank (normalised to 1.0 base + random)
        self.capital = 0.1 + 0.2 * self.rng.random(n_banks)

        # Adjacency matrix: L[i, j] = exposure of bank i to bank j
        # Random exposures
        raw = self.rng.random((n_banks, n_banks))
        mask = (raw < connectivity_prob).astype(float)
        np.fill_diagonal(mask, 0.0)
        exposures = self.rng.uniform(0.01, 0.05, (n_banks, n_banks)) * mask
        # Scale so total interbank assets roughly equal each bank's capital
        self.adjacency = exposures
        self.liabilities = exposures.T.copy()  # liabilities[j, i] = what j owes i

    def simulate_contagion(
        self,
        initial_shock_bank: int = 0,
        threshold: float = 0.5,
    ) -> Dict[str, np.ndarray]:
        """
        Simulate cascading bank defaults.

        If a bank's losses exceed *threshold* × its capital, it defaults.
        On default, its creditors lose the exposed amount, potentially
        triggering further defaults.

        Parameters
        ----------
        initial_shock_bank : int
            Index of the initially shocked bank.
        threshold : float
            Loss-to-capital ratio that triggers default.

        Returns
        -------
        dict with keys:
            'default_sequence' : list of bank indices that defaulted (in order)
            'losses'          : ndarray of cumulative losses per bank
            'n_defaults'      : int, total number of defaults
            'defaulted_mask'  : bool ndarray
        """
        n = self.n_banks
        losses = np.zeros(n)
        defaulted = np.zeros(n, dtype=bool)
        default_sequence: List[int] = []

        # Initial shock: bank loses a fraction of its capital
        initial_loss = threshold * self.capital[initial_shock_bank] * 1.5
        losses[initial_shock_bank] = initial_loss

        if initial_loss >= threshold * self.capital[initial_shock_bank]:
            defaulted[initial_shock_bank] = True
            default_sequence.append(initial_shock_bank)

        changed = True
        max_iter = n * 2  # safety limit
        iteration = 0

        while changed and iteration < max_iter:
            changed = False
            iteration += 1

            for i in range(n):
                if defaulted[i]:
                    # Propagate losses to creditors of bank i
                    # liabilities[i, j] = what bank i owes bank j
                    for j in range(n):
                        if j != i and not defaulted[j]:
                            exposure = self.liabilities[i, j]
                            if exposure > 0:
                                # Loss given default = some recovery rate
                                loss_rate = 0.6  # 40% recovery
                                loss = exposure * loss_rate
                                losses[j] += loss
                                if losses[j] >= threshold * self.capital[j] and not defaulted[j]:
                                    defaulted[j] = True
                                    default_sequence.append(j)
                                    changed = True

        return {
            "default_sequence": np.array(default_sequence),
            "losses": losses,
            "n_defaults": int(np.sum(defaulted)),
            "defaulted_mask": defaulted,
        }

    def systemic_risk_metrics(self) -> Dict[str, np.ndarray]:
        """
        Compute network-based systemic risk metrics.

        Returns
        -------
        dict with keys:
            'degree_centrality'   : out-degree / (n-1)
            'in_degree_centrality': in-degree / (n-1)
            'eigenvector_centrality': principal eigenvector of adjacency
            'debt_rank'          : DebtRank impact scores (Battiston-style)
        """
        n = self.n_banks
        adj = self.adjacency

        # Degree centrality
        out_degree = (adj > 0).sum(axis=1).astype(float)
        in_degree = (adj > 0).sum(axis=0).astype(float)
        degree_centrality = out_degree / max(n - 1, 1)
        in_degree_centrality = in_degree / max(n - 1, 1)

        # Eigenvector centrality (power iteration on adjacency transpose)
        eig = np.ones(n) / n
        for _ in range(200):
            eig_new = adj.T @ eig
            norm = np.linalg.norm(eig_new, 1)
            if norm < 1e-12:
                break
            eig_new /= norm
            if np.allclose(eig, eig_new, atol=1e-8):
                break
            eig = eig_new
        eigenvector_centrality = eig

        # DebtRank (simplified Battiston et al. 2012)
        debt_rank = np.zeros(n)
        for i in range(n):
            # Impact of i on others
            for j in range(n):
                if i != j and self.adjacency[i, j] > 0:
                    # Relative exposure
                    rel_exposure = self.adjacency[i, j] / max(self.capital[j], 1e-10)
                    debt_rank[i] += rel_exposure * (1.0 / max(self.capital[i], 1e-10))

        return {
            "degree_centrality": degree_centrality,
            "in_degree_centrality": in_degree_centrality,
            "eigenvector_centrality": eigenvector_centrality,
            "debt_rank": debt_rank,
        }

    def identify_sifis(self, capital_buffer: float = 0.08) -> Dict[str, np.ndarray]:
        """
        Identify Systemically Important Financial Institutions (SIFIs).

        A bank is a SIFI if its DebtRank exceeds the capital buffer.

        Parameters
        ----------
        capital_buffer : float
            Capital buffer threshold for SIFI designation.

        Returns
        -------
        dict with keys:
            'sifi_indices' : ndarray of SIFI bank indices
            'sifi_scores'  : ndarray of DebtRank scores for SIFIs
            'all_scores'   : ndarray of DebtRank scores for all banks
        """
        metrics = self.systemic_risk_metrics()
        dr = metrics["debt_rank"]
        sifi_mask = dr > capital_buffer
        return {
            "sifi_indices": np.where(sifi_mask)[0],
            "sifi_scores": dr[sifi_mask],
            "all_scores": dr,
        }


class CorrelationNetwork:
    """
    Builds a dynamic correlation network from an asset returns matrix.
    """

    def __init__(self, returns_matrix: np.ndarray) -> None:
        """
        Parameters
        ----------
        returns_matrix : ndarray of shape (T, N)
            T observations of N asset returns.
        """
        returns_matrix = np.asarray(returns_matrix, dtype=float)
        if returns_matrix.ndim != 2:
            raise ValueError("returns_matrix must be 2-D (T x N).")
        if returns_matrix.shape[0] < 2 or returns_matrix.shape[1] < 2:
            raise ValueError("Need at least 2 observations and 2 assets.")
        self.returns = returns_matrix
        self.T, self.N = returns_matrix.shape
        self.corr_matrix = np.corrcoef(returns_matrix, rowvar=False)
        self.adjacency = None

    def build_network(self, threshold: float = 0.5) -> np.ndarray:
        """
        Create adjacency matrix from correlation matrix.

        Edge exists where |corr| > threshold.

        Parameters
        ----------
        threshold : float
            Absolute correlation threshold for edge creation.

        Returns
        -------
        ndarray of shape (N, N)
            Binary adjacency matrix.
        """
        self.adjacency = (np.abs(self.corr_matrix) > threshold).astype(float)
        np.fill_diagonal(self.adjacency, 0.0)
        return self.adjacency

    def community_detection(self, max_iter: int = 100) -> Dict[str, np.ndarray]:
        """
        Simple modularity-based community detection (Louvain-like greedy).

        Uses the standard modularity Q = (1/2m) sum_ij [A_ij - k_i k_j / (2m)] delta(c_i, c_j)
        and iteratively moves nodes to maximise Q.

        Returns
        -------
        dict with keys:
            'labels'      : ndarray of community labels per node
            'n_communities': int
            'modularity'   : float, final modularity score
        """
        if self.adjacency is None:
            self.build_network(0.5)

        A = self.adjacency
        n = self.N
        degrees = A.sum(axis=1)
        m = A.sum() / 2.0

        if m < 1e-10:
            return {"labels": np.arange(n), "n_communities": n, "modularity": 0.0}

        # Start: each node in its own community
        labels = np.arange(n)

        def modularity(comm: np.ndarray, adj: np.ndarray, deg: np.ndarray, total_m: float) -> float:
            q = 0.0
            for i in range(n):
                for j in range(n):
                    if comm[i] == comm[j]:
                        q += adj[i, j] - deg[i] * deg[j] / (2.0 * total_m)
            return q / (2.0 * total_m)

        # Greedy: try to move each node to the best neighbouring community
        for _ in range(max_iter):
            improved = False
            for i in range(n):
                neighbours = np.where(A[i] > 0)[0]
                if len(neighbours) == 0:
                    continue

                best_comm = labels[i]
                best_gain = 0.0

                current_comm = labels[i]
                unique_neighbour_comms = np.unique(labels[neighbours])

                for trial_comm in unique_neighbour_comms:
                    if trial_comm == current_comm:
                        continue
                    old_labels = labels.copy()
                    labels[i] = trial_comm
                    new_q = modularity(labels, A, degrees, m)
                    old_q = modularity(old_labels, A, degrees, m)
                    gain = new_q - old_q
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = trial_comm
                    labels[i] = current_comm

                if best_gain > 1e-8:
                    labels[i] = best_comm
                    improved = True

            if not improved:
                break

        # Relabel communities contiguously
        unique_labels = np.unique(labels)
        label_map = {old: new for new, old in enumerate(unique_labels)}
        relabeled = np.array([label_map[l] for l in labels])

        return {
            "labels": relabeled,
            "n_communities": len(unique_labels),
            "modularity": modularity(relabeled, A, degrees, m),
        }

    def centrality_analysis(self) -> Dict[str, np.ndarray]:
        """
        Compute degree, betweenness, and eigenvector centrality for each node.

        Returns
        -------
        dict with keys:
            'degree'      : ndarray of degree centralities
            'betweenness' : ndarray of betweenness centralities
            'eigenvector' : ndarray of eigenvector centralities
        """
        if self.adjacency is None:
            self.build_network(0.5)

        A = self.adjacency
        n = self.N

        # Degree centrality
        degree = A.sum(axis=1) / max(n - 1, 1)

        # Betweenness centrality (simplified Brandes algorithm)
        betweenness = np.zeros(n)
        for s in range(n):
            # BFS from s
            stack = [s]
            predecessors: List[List[int]] = [[] for _ in range(n)]
            sigma = np.zeros(n)
            sigma[s] = 1.0
            dist = -np.ones(n, dtype=float)
            dist[s] = 0.0

            queue = [s]
            while queue:
                v = queue.pop(0)
                stack.append(v)
                for w in range(n):
                    if A[v, w] > 0:
                        if dist[w] < 0:
                            dist[w] = dist[v] + 1
                            queue.append(w)
                        if dist[w] == dist[v] + 1:
                            sigma[w] += sigma[v]
                            predecessors[w].append(v)

            delta = np.zeros(n)
            while stack:
                w = stack.pop()
                for v in predecessors[w]:
                    delta[v] += (sigma[v] / max(sigma[w], 1e-10)) * (1.0 + delta[w])
                if w != s:
                    betweenness[w] += delta[w]

        # Normalise
        if n > 2:
            betweenness /= ((n - 1) * (n - 2))

        # Eigenvector centrality (power iteration)
        eig = np.ones(n) / n
        for _ in range(200):
            eig_new = A.T @ eig
            norm = np.linalg.norm(eig_new, 1)
            if norm < 1e-12:
                break
            eig_new /= norm
            if np.allclose(eig, eig_new, atol=1e-8):
                break
            eig = eig_new

        return {
            "degree": degree,
            "betweenness": betweenness,
            "eigenvector": eig,
        }


class DebtRank:
    """
    Implements the DebtRank algorithm (Battiston et al. 2012).

    DebtRank measures the systemic importance of each node in a
    financial network by quantifying the total impact of an initial
    distress on that node propagating through the network.
    """

    def __init__(self, adjacency: np.ndarray, capital: np.ndarray) -> None:
        """
        Parameters
        ----------
        adjacency : ndarray of shape (N, N)
            Directed adjacency matrix (exposures). adjacency[i,j] = exposure of i to j.
        capital : ndarray of shape (N,)
            Capital buffer for each node.
        """
        self.adjacency = np.asarray(adjacency, dtype=float)
        self.capital = np.asarray(capital, dtype=float)
        self.N = len(capital)

        # Build weighted adjacency W[i,j] = exposure of i to j / capital[j]
        self.W = np.zeros_like(self.adjacency)
        for i in range(self.N):
            for j in range(self.N):
                if i != j and self.capital[j] > 0:
                    self.W[i, j] = self.adjacency[i, j] / self.capital[j]

    def compute(self, initial_distressed: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute DebtRank impact scores.

        Parameters
        ----------
        initial_distressed : ndarray of shape (N,) or None
            Initial distress level per node (0 to 1). If None, tests
            each node individually.

        Returns
        -------
        ndarray of shape (N,)
            Impact score for each node (how much total distress it
            causes when initially distressed).
        """
        if initial_distressed is not None:
            return self._compute_single(initial_distressed)

        # Test each node individually
        impact_scores = np.zeros(self.N)
        for i in range(self.N):
            distressed = np.zeros(self.N)
            distressed[i] = 1.0  # full distress
            impact_scores[i] = self._compute_single(distressed).sum()
        return impact_scores

    def _compute_single(self, h: np.ndarray) -> np.ndarray:
        """
        Run the DebtRank propagation from initial distress vector h.

        Returns
        -------
        ndarray of shape (N,)
            Final distress level for each node.
        """
        n = self.N
        h = h.copy()
        s = np.zeros(n)  # impact score
        R = np.ones(n, dtype=bool)  # not yet impacted

        # Mark initially distressed as already impacted
        R[h > 0] = False

        W = self.W

        for _ in range(n):
            # Distress propagates: h_new[i] = sum_j W[j,i] * h[j] for impacted j
            h_new = np.zeros(n)
            for j in range(n):
                if not R[j] and h[j] > 0:
                    for i in range(n):
                        if R[i]:
                            h_new[i] += W[j, i] * h[j]

            # Update impacted nodes
            newly_impacted = (h_new > 0) & R
            if not np.any(newly_impacted):
                break

            R[newly_impacted] = False
            s += h_new
            h = h_new

        return s + (h > 0).astype(float)  # include initial distress


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("contagion_network.py — Demo")
    print("=" * 60)

    # --- Financial Network ---
    print("\n--- Financial Network ---")
    fn = FinancialNetwork(n_banks=20, connectivity_prob=0.2, seed=42)
    result = fn.simulate_contagion(initial_shock_bank=0, threshold=0.5)
    print(f"  Banks: {fn.n_banks}")
    print(f"  Defaults: {result['n_defaults']}")
    print(f"  Default sequence: {result['default_sequence']}")
    print(f"  Max loss: {result['losses'].max():.4f}")

    metrics = fn.systemic_risk_metrics()
    print(f"  Top 3 DebtRank banks: {np.argsort(metrics['debt_rank'])[-3:][::-1]}")

    sifis = fn.identify_sifis(capital_buffer=0.08)
    print(f"  SIFIs identified: {len(sifis['sifi_indices'])}")
    print(f"  SIFI indices: {sifis['sifi_indices']}")

    # --- Correlation Network ---
    print("\n--- Correlation Network ---")
    rng = np.random.default_rng(42)
    T, N = 252, 15
    # Create correlated returns
    factor = rng.standard_normal(T)
    returns = 0.3 * factor[:, None] + 0.7 * rng.standard_normal((T, N))
    # Add a cluster: first 5 assets more correlated
    returns[:, :5] += 0.5 * rng.standard_normal(T)[:, None]

    cn = CorrelationNetwork(returns)
    adj = cn.build_network(threshold=0.4)
    print(f"  Edges: {int(adj.sum() / 2)}")

    communities = cn.community_detection()
    print(f"  Communities: {communities['n_communities']}")
    print(f"  Community labels: {communities['labels']}")
    print(f"  Modularity: {communities['modularity']:.4f}")

    cent = cn.centrality_analysis()
    top_betweenness = np.argsort(cent['betweenness'])[-3:][::-1]
    print(f"  Top 3 betweenness nodes: {top_betweenness}")

    # --- DebtRank ---
    print("\n--- DebtRank ---")
    dr = DebtRank(fn.adjacency, fn.capital)
    scores = dr.compute()
    top_dr = np.argsort(scores)[-5:][::-1]
    print(f"  Top 5 systemic banks: {top_dr}")
    print(f"  DebtRank scores (top 5): {scores[top_dr]}")

    print("\n[DONE]")
