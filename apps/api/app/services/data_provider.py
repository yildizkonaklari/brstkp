from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
import os
from datetime import date
from pydantic import BaseModel

class SymbolInfo(BaseModel):
    symbol: str
    name: str = ""
    sector: str = ""
    is_active: bool = True
    list_start_date: Optional[date] = None

class DataProvider(ABC):
    @abstractmethod
    def get_symbols(self) -> List[SymbolInfo]:
        """Return list of active symbols."""
        pass

    @abstractmethod
    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Return daily OHLCV dataframe.
        Columns: [open, high, low, close, volume, turnover_tl, adj_close]
        Index: date (pd.DatetimeIndex)
        """
        pass

    @abstractmethod
    def get_index_daily(self, index_name: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Return daily index dataframe.
        Columns: [close] -> can add others like return_1d
        Index: date
        """
        pass

class CSVDataProvider(DataProvider):
    def __init__(self, csv_dir: str):
        self.csv_dir = csv_dir

    def get_symbols(self) -> List[SymbolInfo]:
        path = os.path.join(self.csv_dir, "symbols.csv")
        if not os.path.exists(path):
            return []
        
        df = pd.read_csv(path)
        symbols = []
        for _, row in df.iterrows():
            symbols.append(SymbolInfo(
                symbol=str(row['symbol']),
                name=str(row.get('name', '')),
                sector=str(row.get('sector', '')),
                is_active=bool(row.get('is_active', True)),
                list_start_date=pd.to_datetime(row['list_start_date']).date() if 'list_start_date' in row and pd.notnull(row['list_start_date']) else None
            ))
        return symbols

    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        # Assuming format: prices_{symbol}.csv or just one big file? 
        # For simplicity in MVP seed: prices_sample.csv containing multiple symbols
        path = os.path.join(self.csv_dir, "prices_sample.csv")
        if not os.path.exists(path):
            return pd.DataFrame()

        df = pd.read_csv(path, parse_dates=['date'])
        
        # Filter by symbol
        df = df[df['symbol'] == symbol].copy()
        
        # Filter by date
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return pd.DataFrame()

        df.set_index('date', inplace=True)
        # Ensure columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing column {col} in CSV")
        
        if 'adj_close' not in df.columns:
            df['adj_close'] = df['close']
            
        if 'turnover_tl' not in df.columns:
            df['turnover_tl'] = df['close'] * df['volume']

        return df[['open', 'high', 'low', 'close', 'volume', 'turnover_tl', 'adj_close']].sort_index()

    def get_index_daily(self, index_name: str, start_date: date, end_date: date) -> pd.DataFrame:
        path = os.path.join(self.csv_dir, f"{index_name.lower()}_sample.csv")
        if not os.path.exists(path):
             # Fallback to prices_sample if it contains index? No, keep separate for clarity
            return pd.DataFrame()
            
        df = pd.read_csv(path, parse_dates=['date'])
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        df = df.loc[mask]
        
        if df.empty:
            return pd.DataFrame()
            
        df.set_index('date', inplace=True)
        return df[['close']].sort_index()

class YahooFinanceProvider(DataProvider):
    def __init__(self):
        import yfinance as yf
        self.yf = yf
        
    def get_symbols(self) -> List[SymbolInfo]:
        # Yahoo doesn't provide a "list of all symbols" easily. 
        # We must rely on an external list or the seed CSV to know WHAT to fetch.
        # For this implementation, we return empty info and expect the caller 
        # to provide the symbol list from another source (like database or seed csv).
        return []

    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        # BIST symbols on Yahoo end with .IS
        ticker = f"{symbol}.IS" if not symbol.endswith(".IS") else symbol
        
        df = self.yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        
        if df.empty:
            return pd.DataFrame()
            
        # Yahoo columns: Open, High, Low, Close, Volume
        # Rename to lowercase
        df.reset_index(inplace=True)
        df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Determine active date range
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        df = df.loc[mask].copy()

        if df.empty:
            return pd.DataFrame()

        df.set_index('date', inplace=True)
        
        # Handle 'Adj Close' if present, but auto_adjust=True usually gives adjusted in Close
        # Let's simulate turnover_tl approx as close * volume
        df['turnover_tl'] = df['close'] * df['volume']
        df['adj_close'] = df['close']
        
        return df[['open', 'high', 'low', 'close', 'volume', 'turnover_tl', 'adj_close']].sort_index()

    def get_index_daily(self, index_name: str, start_date: date, end_date: date) -> pd.DataFrame:
        # XU100 is XU100.IS on Yahoo
        if index_name == "XU100":
            ticker = "XU100.IS"
        else:
            ticker = f"{index_name}.IS"
            
        df = self.yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        
        if df.empty:
            return pd.DataFrame()
            
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'date', 'Close': 'close'}, inplace=True)
        
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        df = df.loc[mask].copy()
        
        if df.empty:
            return pd.DataFrame()

        df.set_index('date', inplace=True)
        return df[['close']].sort_index()

