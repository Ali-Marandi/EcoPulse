import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pytest


@pytest.fixture
def rng():
    """Deterministic random state."""
    return np.random.RandomState(42)


@pytest.fixture
def sample_returns(rng, n=200):
    """Synthetic daily returns (~1 year)."""
    return rng.normal(0.001, 0.02, n)


@pytest.fixture
def sample_4var_data(rng, n=200):
    """4-variable macro dataset as dict of arrays."""
    return {
        "gdp": 100 + np.cumsum(rng.normal(0.3, 1.0, n)),
        "inflation": 2.0 + np.cumsum(rng.normal(0.01, 0.1, n)),
        "unemployment": 5.0 + np.cumsum(rng.normal(-0.01, 0.2, n)),
        "investment": 50 + np.cumsum(rng.normal(0.1, 0.5, n)),
    }
