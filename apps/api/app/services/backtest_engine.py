import pandas as pd
import numpy as np
from datetime import timedelta, date
from typing import List, Dict, Any, Optional
# Removing DB imports to keep engine pure logic, will return dicts
# The service wrapper will save to DB

class BacktestEngine:
    def __init__(self):
        pass

    async def run_backtest(self, params: Dict[str, Any], top10_history: pd.DataFrame, 
                           feature_history: pd.DataFrame, price_history: Dict[str, pd.DataFrame],
                           index_history: pd.DataFrame) -> Dict[str, Any]:
        """
        Run backtest simulation.
        top10_history: DataFrame with multi-index (date, rank) -> symbol, final_score
            Should be indexed by DATE. If multi-index, we'll slice.
        feature_history: DataFrame with multi-index (date, symbol) -> ema50, atr14, etc.
        price_history: Dict[symbol] -> DataFrame[date] -> open, close, etc.
        index_history: DataFrame[date] -> ema50, close (for regime)
        """
        
        start_date = pd.to_datetime(params.get('start_date')).date()
        end_date = pd.to_datetime(params.get('end_date')).date()
        initial_capital = float(params.get('initial_capital', 100_000.0))
        fee_bps = float(params.get('fee_bps', 10.0))
        slippage_bps = float(params.get('slippage_bps', 8.0))
        
        # Helper to get price
        def get_price_row(sym, dt):
            if sym not in price_history: return None
            df = price_history[sym]
            if dt in df.index:
                return df.loc[dt]
            return None

        def get_feature_row(sym, dt):
            try:
                # features might serve 'date' as index level 0
                # We assume features are sorted and aligned
                return feature_history.loc[(pd.to_datetime(dt), sym)]
            except KeyError:
                return None

        # Build timeline from index history (business days)
        timeline = sorted([d.date() for d in index_history.index if start_date <= d.date() <= end_date])
        if not timeline:
            return {"error": "No timeline generated from index history within date range"}

        # State
        cash = initial_capital
        holdings = {} # symbol -> {qty, entry_price, entry_date, stop_price}
        equity_curve = []
        trades = []
        
        portfolio_value = initial_capital
        
        for i, today in enumerate(timeline):
            dt_ts = pd.to_datetime(today)
            is_monday = today.weekday() == 0
            
            # 1. Determine Target Universe (if Rebalance Day)
            target_symbols = []
            target_weight = 0.0
            rebalance_day = False
            
            if is_monday:
                rebalance_day = True
                # Look at previous valid day (Friday)
                prev_idx = i - 1
                if prev_idx >= 0:
                    prev_date = timeline[prev_idx]
                    prev_ts = pd.to_datetime(prev_date)
                    
                    # Check Regime on Prev Date
                    regime = "RISK_OFF"
                    if prev_ts in index_history.index:
                        idx_row = index_history.loc[prev_ts]
                        # Assuming index_history is already pre-computed or we classify here?
                        # Let's rely on 'scores' logic or simple Check
                        # RISK_ON if close > ema50 AND ema50 > ema50_lag10
                        # We might not have computed EMA explicitly here if passed raw
                        # For MVP assume basic risk on/off or check provided logic
                        # Let's check EMA50
                        if 'ema50' in idx_row and pd.notnull(idx_row['ema50']):
                             # We need lag10. Hard to get efficiently in loop without full series.
                             # Assume RISK_ON for now unless we import ScoringEngine. 
                             # Simpler: Assume RISK_ON = True for MVP or check simple close > ema50
                             if idx_row['close'] > idx_row['ema50']:
                                 regime = "RISK_ON"
                    
                    # Load Top 10
                    # top10_history usually (date, rank) multiindex
                    # Slice for prev_ts
                    try:
                        # top10_history index is (date, rank)
                        daily_top = top10_history.loc[prev_ts]
                        # Sort by rank just in case
                        daily_top = daily_top.sort_index()
                        
                        top_n = 10 if regime == "RISK_ON" else 7
                        top_list = daily_top.iloc[:top_n]
                        target_symbols = top_list['symbol'].tolist()
                        
                        # Weighting
                        # Risk ON: 100% invest / 10 = 10%
                        # Risk OFF: 70% invest / 7 = 10%
                        target_weight = 0.10
                        
                    except KeyError:
                        # No signals for yesterday
                        pass

            # 2. Check STOPS (based on Yesterday Close)
            stops_triggered = set() # symbols
            if i > 0:
                prev_date = timeline[i-1]
                prev_ts = pd.to_datetime(prev_date)
                
                for sym, h in holdings.items():
                    p_row = get_price_row(sym, prev_date)
                    f_row = get_feature_row(sym, prev_date)
                    
                    if p_row is None: continue
                    
                    close_price = p_row['close']
                    reason = None
                    
                    # Trend Stop: Close < EMA50
                    if f_row is not None and 'ema50' in f_row:
                        if close_price < f_row['ema50']:
                            reason = "TREND_STOP"
                            
                    # ATR Stop
                    if not reason and close_price < h['stop_price']:
                        reason = "ATR_STOP"
                        
                    # Time Stop (8 weeks = 56 days)
                    if not reason:
                        days_held = (today - h['entry_date']).days
                        if days_held >= 56:
                            reason = "TIME_STOP"
                            
                    if reason:
                        stops_triggered.add(sym)
                        # Log intent ?
                        
            # 3. EXECUTE TRADES at OPEN
            # Order: Sells first, then Buys
            
            # A. Sells
            # We sell if:
            # 1. Stop triggered (Force sell)
            # 2. Rebalance: not in target (Sell all)
            # 3. Rebalance: in target but weight adjustment? (MVP: Sell/Rebuy logic or simplified)
            #    Simpler: Sell if not in target. If in target, we ideally hold. 
            #    But if we want strictly equal weight, we might trim. 
            #    Let's stick to "Sell if not in target" for MVP to minimize turnover cost, 
            #    OR "Sell all and Rebuy" (costly).
            #    "Sell if not in target" + "Buy if new" is better.
            
            # List of things to sell
            to_sell = set()
            
            # Stops
            to_sell.update(stops_triggered)
            
            # Rebalance removals
            if rebalance_day:
                for sym in holdings.keys():
                    if sym not in target_symbols:
                        to_sell.add(sym)
            
            # Execute Sells
            for sym in list(to_sell):
                if sym not in holdings: continue
                
                h = holdings[sym]
                p_row = get_price_row(sym, today)
                if p_row is None: continue # Can't trade (halted/no data) -> skip
                
                open_price = p_row['open']
                if np.isnan(open_price): continue
                
                qty = h['qty']
                
                # Apply slippage
                exec_price = open_price * (1 - slippage_bps/10000.0)
                gross_proceeds = qty * exec_price
                fee = gross_proceeds * (fee_bps/10000.0)
                net_proceeds = gross_proceeds - fee
                
                cash += net_proceeds
                del holdings[sym]
                
                trades.append({
                    "run_id": params.get('run_id'),
                    "date": today,
                    "symbol": sym,
                    "action": "SELL",
                    "qty": qty,
                    "price": exec_price,
                    "fee": fee,
                    "slippage": open_price - exec_price,
                    "reason": "STOP" if sym in stops_triggered else "REBALANCE"
                })

            # B. Buys (Only on Rebalance Day)
            # Cash Stays rule: If we sold a stop mid-week, cash sits until next Monday.
            
            if rebalance_day and target_symbols:
                # Calculate target value per stock
                # Total Portfolio Value at this moment = Cash + Holdings Value
                # We want each target to be 10% of TOTAL Value? Or 10% of INITIAL?
                # Usually % of Current Equity.
                # Re-calc equity with updated cash
                current_equity = cash + sum(
                    holdings[s]['qty'] * get_price_row(s, today)['open'] 
                    for s in holdings if get_price_row(s, today) is not None
                )
                
                target_per_stock = current_equity * target_weight
                
                # Buy new targets
                for sym in target_symbols:
                    if sym in holdings:
                        continue # Already hold, skip re-weighting for MVP to save fees
                    
                    if sym in stops_triggered:
                        continue # Don't buy back immediately if just stopped? (Wash sale/logical)
                    
                    # Check price
                    p_row = get_price_row(sym, today)
                    f_row = get_feature_row(sym, today) # We need ATR for stop!
                    # Wait, stop is set at ENTRY. We need ATR from "Yesterday" (Signal day) or Today?
                    # Usually we use ATR from Signal Day (Friday/Yesterday).
                    prev_date = timeline[i-1] if i>0 else None
                    if not prev_date: continue
                    
                    f_prev = get_feature_row(sym, prev_date)
                    p_prev_close = get_price_row(sym, prev_date)
                    
                    if p_row is None or f_prev is None or p_prev_close is None: continue
                    
                    open_price = p_row['open']
                    if np.isnan(open_price): continue
                    
                    # Check Cash
                    cost_basis = open_price * (1 + slippage_bps/10000.0)
                    
                    # Max qty we can buy
                    # target_amount
                    if cash < (target_per_stock * 0.9): 
                        # If cash is significantly less than target, maybe we are fully invested?
                        # With 10% weights, we might have cash spread out.
                        # Using available cash is safer.
                        qty = cash / cost_basis
                        # But if we have 30% cash limit in Risk Off?
                        # target_weight logic handles the allocation ratio.
                        # If Risk Off, target_weight=10%, 7 stocks = 70%. 30% left.
                        # So simply: try to buy target amount, capped by cash.
                        amount_to_buy = min(target_per_stock, cash)
                    else:
                        amount_to_buy = target_per_stock

                    if amount_to_buy < 100: continue # Min trade size?
                    
                    qty = int(amount_to_buy / cost_basis)
                    if qty <= 0: continue
                    
                    # Execute Buy
                    gross_cost = qty * cost_basis
                    fee = gross_cost * (fee_bps/10000.0)
                    total_cost = gross_cost # cost_basis already includes slippage? 
                    # Logic: 
                    # Buy Price = Open * (1+slip)
                    # Gross = Qty * BuyPrice
                    # Fee = Gross * bps
                    # Cash -= (Gross + Fee)
                    
                    # Correct math:
                    # needed = qty * open * (1+slip) * (1+fee) ~ approx
                    
                    total_outflow = (qty * open_price * (1 + slippage_bps/10000.0)) + fee
                    
                    if total_outflow > cash:
                        # adj qty
                        qty = int(cash / (open_price * (1 + slippage_bps/10000.0) * (1 + fee_bps/10000.0)))
                        if qty <= 0: continue
                        total_outflow = (qty * open_price * (1 + slippage_bps/10000.0)) + fee

                    cash -= total_outflow
                    
                    # Set Stop
                    # ATR Stop: Entry - 2*ATR14(PrevDay)
                    atr14 = f_prev['atr14'] if 'atr14' in f_prev else (p_prev_close['close']*0.05) # fallback
                    stop_price = open_price - (2 * atr14)
                    
                    holdings[sym] = {
                        "qty": qty,
                        "entry_price": open_price, # execution price
                        "entry_date": today,
                        "stop_price": stop_price
                    }
                    
                    trades.append({
                        "run_id": params.get('run_id'),
                        "date": today,
                        "symbol": sym,
                        "action": "BUY",
                        "qty": qty,
                        "price": open_price * (1 + slippage_bps/10000.0),
                        "fee": fee,
                        "slippage": open_price * (slippage_bps/10000.0),
                        "reason": "REBALANCE"
                    })

            # 4. End of Day Reporting
            # Calculate Close Equity
            holding_value = 0.0
            for sym, h in holdings.items():
                p_row = get_price_row(sym, today)
                if p_row is None:
                    # Use last known? OR Entry?
                    # Use entry if no price (fallback)
                    price = h['entry_price']
                else:
                    price = p_row['close']
                holding_value += h['qty'] * price
            
            total_equity = cash + holding_value
            
            # Benchmark (XU100)
            bench_val = 0
            if today in index_history.index:
                # normalize to initial capital?
                # simple: just store close value, normalize later in UI
                bench_val = index_history.loc[today]['close']
                
            equity_curve.append({
                "date": today,
                "equity": total_equity,
                "benchmark_equity": bench_val,
                "cash": cash,
                "holdings_count": len(holdings)
            })

        # Final Metrics
        df_eq = pd.DataFrame(equity_curve)
        if df_eq.empty:
            return {"error": "No equity curve generated"}
            
        df_eq.set_index('date', inplace=True)
        
        # CAGR
        days = (end_date - start_date).days
        years = days / 365.25
        final_eq = df_eq.iloc[-1]['equity']
        cagr = (final_eq / initial_capital) ** (1/years) - 1 if years > 0 else 0
        
        # MaxDD
        roll_max = df_eq['equity'].cummax()
        drawdown = (df_eq['equity'] - roll_max) / roll_max
        max_dd = drawdown.min()
        
        # Sharpe (Daily returns)
        returns = df_eq['equity'].pct_change()
        sharpe = (returns.mean() / returns.std()) * (252**0.5) if returns.std() != 0 else 0
        
        return {
            "metrics": {
                "cagr": round(cagr * 100, 2),
                "max_dd": round(max_dd * 100, 2),
                "sharpe": round(sharpe, 2),
                "final_equity": round(final_eq, 2),
                "total_trades": len(trades)
            },
            "equity_curve": df_eq.reset_index().to_dict(orient='records'),
            "trades": trades
        }
