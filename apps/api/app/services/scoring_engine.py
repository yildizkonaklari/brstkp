import pandas as pd
import json

class ScoringEngine:
    def detect_regime(self, df_index: pd.DataFrame) -> str:
        """
        Detect market regime based on XU100.
        RISK_ON if close > EMA50 AND EMA50 > EMA50[D-10]
        else RISK_OFF
        
        df_index: expected to have 'close', 'ema50' columns.
        Assumes the last row is the current day T.
        """
        if df_index.empty or len(df_index) < 11:
            return "RISK_OFF" # Default safety
            
        current = df_index.iloc[-1]
        ema50_lag10 = df_index['ema50'].iloc[-11]
        
        if (current['close'] > current['ema50']) and (current['ema50'] > ema50_lag10):
            return "RISK_ON"
        
        return "RISK_OFF"

    def calculate_scores(self, df_features: pd.DataFrame, regime: str) -> pd.DataFrame:
        """
        Calculate Potential, Risk, and Final scores.
        df_features: Normalized (0-100) feature dataframe with index=symbol.
        """
        if df_features.empty:
            return df_features
            
        df = df_features.copy()
        
        # Coefficients
        # Potential (0-100)
        # 0.25*RS6M + 0.15*RS3M + 0.15*Trend + 0.15*BO120 + 0.10*Vol + 0.10*UpRatio + 0.10*Quality
        df['potential_score'] = (
            0.25 * df.get('rs_6m', 0) +
            0.15 * df.get('rs_3m', 0) +
            0.15 * df.get('trend_score', 0) +
            0.15 * df.get('bo_120', 0) +
            0.10 * df.get('vol_surge', 0) +
            0.10 * df.get('up_ratio_20', 0) +
            0.10 * df.get('quality_trend', 0)
        )
        
        # Risk (0-100)
        # 0.60*ATR14pct + 0.40*DD60
        df['risk_score'] = (
            0.60 * df.get('atr14_pct', 0) +
            0.40 * df.get('dd60', 0)
        )
        
        # Lambda
        lam = 0.35 if regime == "RISK_ON" else 0.55
        
        # Final Score
        df['final_score'] = df['potential_score'] - (lam * df['risk_score'])
        
        # Generate explain_json
        def make_explain(row):
            return json.dumps({
                "regime": regime,
                "potential": round(row['potential_score'], 2),
                "risk": round(row['risk_score'], 2),
                "components": {
                    "rs_6m": round(row.get('rs_6m', 0), 1),
                    "rs_3m": round(row.get('rs_3m', 0), 1),
                    "trend": round(row.get('trend_score', 0), 1),
                    "bo_120": round(row.get('bo_120', 0), 1),
                    "vol_surge": round(row.get('vol_surge', 0), 1),
                    "risk_atr": round(row.get('atr14_pct', 0), 1),
                    "risk_dd": round(row.get('dd60', 0), 1)
                }
            })
            
        df['explain_json'] = df.apply(make_explain, axis=1)
        
        return df

    def select_top10(self, df_scores: pd.DataFrame, df_symbol_info: pd.DataFrame, min_adv: float = 10_000_000, regime: str = "RISK_ON") -> pd.DataFrame:
        """
        Select Top 10 stocks.
        df_scores: index=symbol, contains 'final_score', 'explain_json', and raw features like 'adv20_tl', 'trend_gate'
        df_symbol_info: index=symbol, contains 'sector', 'is_active'
        """
        if df_scores.empty:
            return pd.DataFrame()
            
        # Join with symbol info
        df = df_scores.join(df_symbol_info[['sector', 'is_active']], how='left')
        
        # Filters:
        # 1. Active
        df = df[df['is_active'] == True]
        
        # 2. ADV20 >= MinADV
        if 'adv20_tl' in df.columns:
             # Note: adv20_tl in df_scores might be normalized rank if we passed normalized df?
             # Wait, FeatureEngine returns raw values. Normalization happens afterwards.
             # If df_features was normalized IN PLACE, we lost raw ADV.
             # DESIGN FIX: FeatureEngine.normalize should return a NEW dataframe with normalized cols, 
             # OR we keep raw columns.
             # Assuming we have access to raw ADV. Let's assume input df_scores RETAINS raw columns 
             # because normalize_cross_sectional only normalized specific columns.
             # Checking FeatureEngine.normalize_cross_sectional...
             # It copies headers. It only normalizes 'columns_to_normalize'. 
             # 'adv20_tl' is NOT in 'columns_to_normalize' list there. So it is raw. Good.
             df = df[df['adv20_tl'] >= min_adv]
             
        # 3. TrendGate (Close > EMA50) - usually raw feature
        if 'trend_gate' in df.columns:
            df = df[df['trend_gate'] == True]
            
        # Sort by Final Score DESC
        df = df.sort_values('final_score', ascending=False)
        
        # Sector Cap: Max 2 per sector
        selected = []
        sector_counts = {}
        
        limit = 7 if regime == "RISK_OFF" else 10
        
        for symbol, row in df.iterrows():
            if len(selected) >= limit:
                break
                
            sector = row.get('sector', 'Unknown')
            if sector:
                count = sector_counts.get(sector, 0)
                if count >= 2:
                    continue
                sector_counts[sector] = count + 1
            
            selected.append({
                "rank": len(selected) + 1,
                "symbol": symbol,
                "final_score": row['final_score'],
                "universe_tag": "ALL"
            })
            
        return pd.DataFrame(selected)
