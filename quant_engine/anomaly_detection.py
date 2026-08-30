r"""
anomaly_detection.py — Financial Anomaly Detection
=====================================================
Provides anomaly and fraud detection models for the EcoPulse quant engine:

* **PriceManipulationDetector** — Multi-method price manipulation detection
* **AccountingFraudDetector**  — Beneish M-Score & Altman Z-Score models

Dependencies: numpy, scipy.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Optional

try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class PriceManipulationDetector:
    """
    Detects potential price manipulation using multiple complementary methods.

    Methods:
        - Volume anomaly (z-score based spike detection)
        - Price velocity anomaly (unusual price acceleration)
        - Painting the tape (correlated price-volume wash trading)
        - Spoofing signal (order book imbalance manipulation)
    """

    def volume_anomaly(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        z_threshold: float = 3.0,
    ) -> Dict[str, np.ndarray]:
        """
        Detect volume spikes using rolling z-scores.

        Parameters
        ----------
        prices : ndarray of shape (T,)
            Asset prices.
        volumes : ndarray of shape (T,)
            Trading volumes.
        z_threshold : float
            Z-score threshold for anomaly classification.

        Returns
        -------
        dict with keys:
            'z_scores'  : ndarray of rolling z-scores for volume
            'anomalies' : ndarray of bool, True where |z| > threshold
            'scores'    : ndarray of anomaly severity (0-1 normalised)
        """
        prices = np.asarray(prices, dtype=float)
        volumes = np.asarray(volumes, dtype=float)

        if len(volumes) < 2:
            return {"z_scores": np.array([0.0]), "anomalies": np.array([False]), "scores": np.array([0.0])}

        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)

        if std_vol < 1e-10:
            z_scores = np.zeros_like(volumes)
        else:
            z_scores = (volumes - mean_vol) / std_vol

        anomalies = np.abs(z_scores) > z_threshold
        scores = np.clip(np.abs(z_scores) / (z_threshold * 2), 0, 1)

        return {"z_scores": z_scores, "anomalies": anomalies, "scores": scores}

    def price_velocity_anomaly(
        self,
        prices: np.ndarray,
        window: int = 5,
        z_threshold: float = 3.0,
    ) -> Dict[str, np.ndarray]:
        """
        Detect unusual price acceleration (second derivative of log-price).

        Parameters
        ----------
        prices : ndarray of shape (T,)
        window : int
            Rolling window for velocity computation.
        z_threshold : float

        Returns
        -------
        Same structure as ``volume_anomaly``.
        """
        prices = np.asarray(prices, dtype=float)
        T = len(prices)

        if T < window + 1:
            return {"z_scores": np.zeros(T), "anomalies": np.zeros(T, dtype=bool), "scores": np.zeros(T)}

        # Log returns
        log_prices = np.log(np.maximum(prices, 1e-10))
        returns = np.diff(log_prices)

        # Velocity = rolling mean of returns (first derivative)
        velocity = np.convolve(returns, np.ones(window) / window, mode='valid')

        # Acceleration = change in velocity (second derivative)
        acceleration = np.diff(velocity)
        if len(acceleration) == 0:
            acceleration = np.array([0.0])

        # Pad to match original length
        pad_len = T - len(acceleration)
        acceleration_padded = np.concatenate([np.zeros(pad_len), acceleration])

        mean_acc = np.mean(acceleration)
        std_acc = np.std(acceleration)

        if std_acc < 1e-10:
            z_scores = np.zeros(T)
        else:
            z_scores = np.zeros(T)
            z_scores[pad_len:] = (acceleration - mean_acc) / std_acc

        anomalies = np.abs(z_scores) > z_threshold
        scores = np.clip(np.abs(z_scores) / (z_threshold * 2), 0, 1)

        return {"z_scores": z_scores, "anomalies": anomalies, "scores": scores}

    def painting_the_tape(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        window: int = 10,
        corr_threshold: float = 0.7,
    ) -> Dict[str, np.ndarray]:
        """
        Detect painting-the-tape (correlated price-volume patterns
        indicative of wash trading / coordinated manipulation).

        High correlation between price changes and volume changes in
        a rolling window can indicate artificial coordination.

        Parameters
        ----------
        prices : ndarray of shape (T,)
        volumes : ndarray of shape (T,)
        window : int
            Rolling window size.
        corr_threshold : float
            Correlation threshold for suspicion.

        Returns
        -------
        dict with keys:
            'correlations' : ndarray of rolling correlations
            'anomalies'    : ndarray of bool where |corr| > threshold
            'scores'       : ndarray of severity (0-1)
        """
        prices = np.asarray(prices, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        T = len(prices)

        if T < window:
            return {"correlations": np.array([0.0]), "anomalies": np.array([False]), "scores": np.array([0.0])}

        price_changes = np.diff(prices) / np.maximum(np.abs(prices[:-1]), 1e-10)
        vol_changes = np.diff(volumes)

        n_windows = T - window - 1
        if n_windows <= 0:
            n_windows = 1

        correlations = np.zeros(T)
        for i in range(min(n_windows, len(price_changes) - window + 1)):
            pc = price_changes[i:i + window]
            vc = vol_changes[i:i + window]

            std_pc = np.std(pc)
            std_vc = np.std(vc)
            if std_pc < 1e-10 or std_vc < 1e-10:
                corr = 0.0
            else:
                corr = np.corrcoef(pc, vc)[0, 1]
                if np.isnan(corr):
                    corr = 0.0
            correlations[i + window] = corr

        anomalies = np.abs(correlations) > corr_threshold
        scores = np.clip(np.abs(correlations) / (corr_threshold * 1.5), 0, 1)

        return {"correlations": correlations, "anomalies": anomalies, "scores": scores}

    def spoofing_signal(
        self,
        order_book_imbalance: np.ndarray,
        prices: np.ndarray,
        z_threshold: float = 2.5,
    ) -> Dict[str, np.ndarray]:
        """
        Detect spoofing-like patterns from order book imbalance.

        Spoofing creates large imbalance that reverses before execution.
        Detected by: sudden large imbalance followed by price move in
        the opposite direction of the imbalance.

        Parameters
        ----------
        order_book_imbalance : ndarray of shape (T,)
            (bid_volume - ask_volume) / (bid_volume + ask_volume).
        prices : ndarray of shape (T,)
        z_threshold : float

        Returns
        -------
        dict with keys:
            'imbalance_z'  : ndarray of z-scored imbalance
            'anomalies'    : ndarray of bool
            'scores'       : ndarray of severity (0-1)
        """
        imbalance = np.asarray(order_book_imbalance, dtype=float)
        prices = np.asarray(prices, dtype=float)
        T = len(imbalance)

        if T < 3:
            return {"imbalance_z": np.zeros(T), "anomalies": np.zeros(T, dtype=bool), "scores": np.zeros(T)}

        # Z-score the imbalance
        mean_imb = np.mean(imbalance)
        std_imb = np.std(imbalance)
        if std_imb < 1e-10:
            z = np.zeros(T)
        else:
            z = (imbalance - mean_imb) / std_imb

        # Price return direction
        price_ret = np.diff(prices) / np.maximum(np.abs(prices[:-1]), 1e-10)
        price_ret = np.concatenate([[0.0], price_ret])

        # Spoofing signal: large imbalance in one direction but price
        # moves in the opposite direction
        signal = np.zeros(T)
        for t in range(1, T):
            # Imbalance positive (more bids) but price falling
            if z[t] > z_threshold and price_ret[t] < -0.001:
                signal[t] = abs(z[t]) * abs(price_ret[t]) * 100
            # Imbalance negative (more asks) but price rising
            elif z[t] < -z_threshold and price_ret[t] > 0.001:
                signal[t] = abs(z[t]) * abs(price_ret[t]) * 100

        anomalies = signal > 0
        scores = np.clip(signal / max(signal.max(), 1e-10), 0, 1)

        return {"imbalance_z": z, "anomalies": anomalies, "scores": scores}

    def detect_all(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        order_book: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Run all detectors and return a combined anomaly score.

        Parameters
        ----------
        prices : ndarray of shape (T,)
        volumes : ndarray of shape (T,)
        order_book : ndarray of shape (T,) or None
            Order book imbalance. If None, spoofing is skipped.

        Returns
        -------
        dict with keys:
            'combined_score' : ndarray of combined anomaly severity (0-1)
            'anomaly_count'  : ndarray of int, number of detectors flagging each point
            'volume_scores'  : ndarray
            'velocity_scores': ndarray
            'painting_scores': ndarray
            'spoofing_scores': ndarray (zeros if no order_book)
        """
        prices = np.asarray(prices, dtype=float)
        volumes = np.asarray(volumes, dtype=float)
        T = len(prices)

        vol_res = self.volume_anomaly(prices, volumes)
        vel_res = self.price_velocity_anomaly(prices)
        paint_res = self.painting_the_tape(prices, volumes)

        if order_book is not None:
            spoof_res = self.spoofing_signal(np.asarray(order_book), prices)
        else:
            spoof_res = {"scores": np.zeros(T)}

        # Combine: average of available scores
        all_scores = np.stack([
            vol_res["scores"],
            vel_res["scores"],
            paint_res["scores"],
            spoof_res["scores"],
        ])
        combined = np.mean(all_scores, axis=0)

        anomaly_count = (
            vol_res["anomalies"].astype(int)
            + vel_res["anomalies"].astype(int)
            + paint_res["anomalies"].astype(int)
            + (spoof_res.get("anomalies", np.zeros(T, dtype=bool))).astype(int)
        )

        return {
            "combined_score": combined,
            "anomaly_count": anomaly_count,
            "volume_scores": vol_res["scores"],
            "velocity_scores": vel_res["scores"],
            "painting_scores": paint_res["scores"],
            "spoofing_scores": spoof_res["scores"],
        }


class AccountingFraudDetector:
    """
    Implements accounting fraud detection models.

    * **Beneish M-Score**: 8-variable probit model for detecting earnings
      manipulation (Beneish 1999).
    * **Altman Z-Score**: 5-variable linear model for bankruptcy prediction
      (Altman 1968).
    """

    # Beneish M-Score coefficients (Beneish 1999)
    _M_SCORE_COEFFICIENTS = {
        "intercept": -4.840,
        "DSRI": 0.920,    # Days' sales in receivables index
        "GMI": 0.528,    # Gross margin index
        "AQI": 0.404,    # Asset quality index
        "SGI": 0.892,    # Sales growth index
        "DEPI": 0.115,   # Depreciation index
        "SGAI": 0.102,   # SG&A expenses index
        "TATA": -0.399,  # Total accruals to total assets
        "LVGI": 0.318,   # Leverage index
    }

    def compute_m_score(self, financial_ratios: Dict[str, float]) -> Dict[str, float]:
        """
        Compute the Beneish M-Score and probability of manipulation.

        Parameters
        ----------
        financial_ratios : dict
            Must contain keys: DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI.

        Returns
        -------
        dict with keys:
            'm_score'    : float, the M-Score
            'probability' : float, estimated probability of manipulation
            'interpretation': str, risk level description
        """
        required_keys = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "TATA", "LVGI"]
        missing = [k for k in required_keys if k not in financial_ratios]
        if missing:
            raise ValueError(f"Missing financial ratio(s): {missing}")

        coeff = self._M_SCORE_COEFFICIENTS
        m_score = coeff["intercept"]
        for key in required_keys:
            m_score += coeff[key] * financial_ratios[key]

        interpretation = self.interpret_m_score(m_score)

        # Probability via logistic approximation of the probit model
        probability = 1.0 / (1.0 + np.exp(-1.7 * (m_score - (-1.78))))
        probability = np.clip(probability, 0, 1)

        return {
            "m_score": m_score,
            "probability": probability,
            "interpretation": interpretation,
        }

    def interpret_m_score(self, m_score: float) -> str:
        """
        Interpret the Beneish M-Score.

        Parameters
        ----------
        m_score : float

        Returns
        -------
        str
            Risk level interpretation.
        """
        if m_score > -1.78:
            return "High risk of earnings manipulation"
        elif m_score > -2.22:
            return "Moderate risk — warrants further investigation"
        else:
            return "Low risk — no strong evidence of manipulation"

    def altman_z_score(
        self,
        working_capital: float,
        total_assets: float,
        retained_earnings: float,
        ebit: float,
        market_cap: float,
        total_liabilities: float,
        sales: float,
    ) -> Dict[str, float]:
        """
        Compute the Altman Z-Score for bankruptcy prediction.

        Z = 1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 1.0 X5

        where:
            X1 = Working Capital / Total Assets
            X2 = Retained Earnings / Total Assets
            X3 = EBIT / Total Assets
            X4 = Market Value of Equity / Book Value of Total Liabilities
            X5 = Sales / Total Assets

        Parameters
        ----------
        working_capital : float
        total_assets : float
        retained_earnings : float
        ebit : float
        market_cap : float
        total_liabilities : float
        sales : float

        Returns
        -------
        dict with keys:
            'z_score'        : float
            'zone'           : str, classification zone
            'bankruptcy_prob': str, qualitative probability
        """
        if total_assets <= 0:
            return {"z_score": float('nan'), "zone": "Undefined", "bankruptcy_prob": "Undefined"}

        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = ebit / total_assets
        x4 = market_cap / max(total_liabilities, 1e-10)
        x5 = sales / total_assets

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        if z > 2.99:
            zone = "Safe Zone"
            prob = "Low probability of bankruptcy"
        elif z > 1.81:
            zone = "Grey Zone"
            prob = "Moderate probability of bankruptcy"
        else:
            zone = "Distress Zone"
            prob = "High probability of bankruptcy"

        return {
            "z_score": z,
            "zone": zone,
            "bankruptcy_prob": prob,
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("anomaly_detection.py — Demo")
    print("=" * 60)

    rng = np.random.default_rng(42)
    T = 500

    # Generate synthetic price/volume data
    base_prices = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, T)))
    base_volumes = 1e6 + rng.normal(0, 2e5, T)

    # Inject anomalies
    # Volume spike
    base_volumes[200:205] *= 5.0
    # Price acceleration
    base_prices[350:355] *= np.array([1.0, 1.02, 1.05, 1.03, 1.01])
    # Painting the tape (correlated price-volume)
    for i in range(400, 410):
        base_volumes[i] = 3e6 * (1 + 0.1 * np.sin(i * 0.5))
        base_prices[i] *= (1 + 0.005 * np.sin(i * 0.5))

    # --- Price Manipulation Detector ---
    print("\n--- Price Manipulation Detector ---")
    pmd = PriceManipulationDetector()

    vol_result = pmd.volume_anomaly(base_prices, base_volumes)
    print(f"  Volume anomalies detected: {vol_result['anomalies'].sum()}")
    print(f"  Max volume z-score: {vol_result['z_scores'].max():.2f}")

    vel_result = pmd.price_velocity_anomaly(base_prices)
    print(f"  Velocity anomalies detected: {vel_result['anomalies'].sum()}")

    paint_result = pmd.painting_the_tape(base_prices, base_volumes)
    print(f"  Painting-the-tape anomalies: {paint_result['anomalies'].sum()}")

    # Combined
    combined = pmd.detect_all(base_prices, base_volumes)
    print(f"  Combined anomalies (score > 0.5): {(combined['combined_score'] > 0.5).sum()}")
    print(f"  Max combined score: {combined['combined_score'].max():.4f}")

    # --- Accounting Fraud Detector ---
    print("\n--- Accounting Fraud Detector ---")
    afd = AccountingFraudDetector()

    # Beneish M-Score example
    ratios = {
        "DSRI": 1.05,  # Days' sales in receivables index
        "GMI": 1.10,   # Gross margin decline
        "AQI": 1.15,   # Asset quality deterioration
        "SGI": 1.30,   # High sales growth
        "DEPI": 0.85,  # Depreciation slowing
        "SGAI": 1.05,  # SG&A growing
        "TATA": 0.08,  # Positive accruals
        "LVGI": 1.20,  # Leverage increasing
    }
    m_result = afd.compute_m_score(ratios)
    print(f"  M-Score: {m_result['m_score']:.4f}")
    print(f"  Manipulation probability: {m_result['probability']:.1%}")
    print(f"  Interpretation: {m_result['interpretation']}")

    # Altman Z-Score example
    z_result = afd.altman_z_score(
        working_capital=50e6,
        total_assets=200e6,
        retained_earnings=40e6,
        ebit=15e6,
        market_cap=120e6,
        total_liabilities=80e6,
        sales=250e6,
    )
    print(f"  Altman Z-Score: {z_result['z_score']:.4f}")
    print(f"  Zone: {z_result['zone']}")
    print(f"  Assessment: {z_result['bankruptcy_prob']}")

    print("\n[DONE]")
