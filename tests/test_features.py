"""Tests for feature engineering helpers."""
import numpy as np
import pandas as pd

from src.features import _days_between


def test_days_between_basic():
    """Positive difference when 'later' is after 'earlier'."""
    earlier = pd.Series(pd.to_datetime(["2020-01-01"]))
    later = pd.Series(pd.to_datetime(["2020-01-11"]))
    assert _days_between(later, earlier).iloc[0] == 10.0


def test_days_between_preserves_nat():
    """NaT input should produce NaN output, not zero."""
    earlier = pd.Series(pd.to_datetime(["2020-01-01", None]))
    later = pd.Series(pd.to_datetime(["2020-01-11", "2020-01-15"]))
    result = _days_between(later, earlier)
    assert result.iloc[0] == 10.0
    assert pd.isna(result.iloc[1])


def test_rfm_scores_in_range():
    """RFM quintile scores must be 1..5."""
    rfm = pd.DataFrame({
        "recency_days": np.arange(100),
        "frequency": np.random.randint(1, 5, 100),
        "monetary": np.random.rand(100) * 1000,
    })
    rfm["r_score"] = pd.qcut(rfm["recency_days"], 5,
                             labels=[5, 4, 3, 2, 1]).astype(int)
    assert rfm["r_score"].between(1, 5).all()