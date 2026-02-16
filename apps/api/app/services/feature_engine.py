import pandas as pd
import numpy as np

class FeatureEngine:
    def compute_features(self, df_prices: pd.DataFrame, df_index: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features for a single symbol dataframe.
        df_prices: columns [open, high, low, close, volume, turnover_tl]
        df_index: columns [close] (XU100)
        
        Returns DataFrame with feature columns.
        """
        if df_prices.empty:
            return pd.DataFrame()
            
        df = df_prices.copy()
        
        # Ensure index alignment
        # We need to join with index data to calculate relative strength
        # But first let's calculate symbol-specific indicators
        
        # 1. EMAs
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # 2. Trend Metrics
        # TrendGate: close > EMA50
        df['trend_gate'] = df['close'] > df['ema50']
        
        # TrendScore components
        # Condition 1: close > EMA50
        c1 = (df['close'] > df['ema50']).astype(int)
        
        # Condition 2: EMA50 rising (EMA50[D] > EMA50[D-10])
        df['ema50_lag10'] = df['ema50'].shift(10)
        c2 = (df['ema50'] > df['ema50_lag10']).astype(int)
        
        df['trend_score'] = (0.6 * c1 + 0.4 * c2) * 100
        
        # QualityTrend
        df['quality_trend'] = np.where(df['ema50'] > df['ema200'], 100, 0)
        
        # 3. Relative Strength (RS)
        # Calculate returns
        df['ret_63'] = df['close'].pct_change(63)
        df['ret_126'] = df['close'].pct_change(126)
        
        # Index returns (align dates)
        idx_ret_63 = df_index['close'].pct_change(63)
        idx_ret_126 = df_index['close'].pct_change(126)
        
        # Map index returns to symbol dates
        df['idx_ret_63'] = df.index.map(idx_ret_63)
        df['idx_ret_126'] = df.index.map(idx_ret_126)
        
        df['rs_3m'] = df['ret_63'] - df['idx_ret_63']
        df['rs_6m'] = df['ret_126'] - df['idx_ret_126']
        
        # 4. Breakout Proximity (BO120)
        # HH120 = max(close[D-119..D]) -> Rolling max 120
        df['hh120'] = df['close'].rolling(window=120, min_periods=60).max()
        df['bo_120'] = df['close'] / df['hh120']
        
        # 5. Volume Surge
        # VOL20 = SMA(volume, 20)
        df['vol20'] = df['volume'].rolling(window=20, min_periods=10).mean()
        df['vol_surge'] = df['volume'] / df['vol20']
        
        # 6. Consistency (UpRatio20)
        # count(close[t] > close[t-1]) over last 20
        df['is_up'] = (df['close'] > df['close'].shift(1)).astype(float)
        df['up_ratio_20'] = df['is_up'].rolling(window=20, min_periods=10).sum() / 20.0
        
        # 7. ATR14%
        # TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = (df['high'] - df['prev_close']).abs()
        df['tr3'] = (df['low'] - df['prev_close']).abs()
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        df['atr14'] = df['tr'].ewm(span=14, adjust=False).mean()
        df['atr14_pct'] = df['atr14'] / df['close']
        
        # 8. Drawdown (DD60)
        # peak60 = max(close[D-59..D])
        df['peak60'] = df['close'].rolling(window=60, min_periods=30).max()
        df['dd60'] = 1 - (df['close'] / df['peak60'])
        
        # 9. ADV20
        if 'turnover_tl' not in df.columns:
            df['turnover_tl'] = df['close'] * df['volume']
        df['adv20_tl'] = df['turnover_tl'].rolling(window=20, min_periods=10).median()

        # Cleanup intermediate columns
        keep_cols = [
            'ema50', 'ema200', 'trend_gate', 'trend_score', 'quality_trend',
            'rs_3m', 'rs_6m', 'bo_120', 'vol_surge', 'up_ratio_20',
            'atr14_pct', 'dd60', 'adv20_tl', 'atr14'
        ]
        
        return df[keep_cols]

    def normalize_cross_sectional(self, df_features: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features across the daily universe (cross-sectional).
        df_features: MultiIndex (date, symbol) or index=symbol for a specific date.
        
        We assume df_features is for A SINGLE DATE if passing just symbols,
        OR we groupby level=0 if it's a full history.
        
        Here we assume a DataFrame with index=symbol for one specific day.
        """
        if df_features.empty:
            return df_features
            
        columns_to_normalize = [
            'rs_3m', 'rs_6m', 'trend_score', 'bo_120', 'vol_surge', 'up_ratio_20', 'quality_trend',
            'atr14_pct', 'dd60' # These are risk metrics, still normalize 0-100 rank
        ]
        
        normalized = df_features.copy()
        
        for col in columns_to_normalize:
            if col not in normalized.columns:
                continue
                
            # Winsorize 2%-98%
            lower = normalized[col].quantile(0.02)
            upper = normalized[col].quantile(0.98)
            normalized[col] = normalized[col].clip(lower, upper)
            
            # Percentile Rank (0-100)
            normalized[col] = normalized[col].rank(pct=True) * 100.0
            
            # For Risk metrics (ATR, DD), high value = high risk (bad).
            # The scoring formula uses them as 'Risk Score', so high rank = high risk.
            # Final = Potential - Risk.
            # So if ATR is high (volatile), rank is high (100). Final score reduces. Correct.
            
        return normalized
