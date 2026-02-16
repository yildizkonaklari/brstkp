import pytest
import pandas as pd
import numpy as np
from app.services.feature_engine import FeatureEngine

@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    df = pd.DataFrame({
        'close': np.linspace(10, 110, 100), # Linear uptrend
        'open': np.linspace(10, 110, 100),
        'high': np.linspace(11, 111, 100),
        'low': np.linspace(9, 109, 100),
        'volume': [1000] * 100
    }, index=dates)
    
    index_df = pd.DataFrame({
        'close': np.linspace(100, 110, 100) # Slower uptrend
    }, index=dates)
    
    return df, index_df

def test_ema_calculation(sample_data):
    df, index_df = sample_data
    fe = FeatureEngine()
    
    res = fe.compute_features(df, index_df)
    
    assert 'ema50' in res.columns
    assert 'ema200' in res.columns # Might be NaN at start
    
    # Check last value
    # Linear trend 10..110 over 100 days. EMA should lag close.
    assert res.iloc[-1]['ema50'] < res.iloc[-1]['close']
    assert res.iloc[-1]['ema50'] > 0

def test_rs_metric(sample_data):
    df, index_df = sample_data
    fe = FeatureEngine()
    
    # Stock doubles (10->110 = 10x), Index 10% (100->110)
    # RS should be positive
    res = fe.compute_features(df, index_df)
    
    assert 'rs_3m' in res.columns
    # Check valid values at end
    assert not np.isnan(res.iloc[-1]['rs_3m'])
    assert res.iloc[-1]['rs_3m'] > 0

def test_insufficient_data():
    dates = pd.date_range(start='2023-01-01', periods=10, freq='B')
    df = pd.DataFrame({'close': [10]*10, 'volume': [100]*10}, index=dates)
    index = pd.DataFrame({'close': [100]*10}, index=dates)
    
    fe = FeatureEngine()
    res = fe.compute_features(df, index)
    
    # Should handle gracefully, maybe return empty or NaNs
    if not res.empty:
        # Check that long term features are NaN
        assert np.isnan(res.iloc[-1].get('ema50', np.nan))
