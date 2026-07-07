import yfinance as yf
import pandas as pd
from typing import Optional

_usdjpy_cache = None

def fetch_daily_data(symbol: str, periods: int = 100) -> Optional[pd.DataFrame]:
    """
    yfinanceを使用して日足データを取得します。
    (本番環境ではAlpaca APIの呼び出しを主とし、フォールバックとしてyfinanceを使用します)
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty:
            return None
        return df.tail(periods)
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def fetch_current_price(symbol: str) -> float:
    """現在の株価を取得します"""
    try:
        ticker = yf.Ticker(symbol)
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            return float(todays_data['Close'].iloc[-1])
        return 0.0
    except:
        return 0.0

def fetch_pre_market_price(symbol: str) -> dict:
    """プレマーケット（時間外）の現在価格と変動率を取得する"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        current_price = info.get("currentPrice")
        regular_close = info.get("previousClose")
        
        if current_price and regular_close:
            change_pct = ((current_price - regular_close) / regular_close) * 100
            return {
                "price": current_price,
                "change_pct": change_pct
            }
        return None
    except Exception as e:
        print(f"Error fetching pre-market price for {symbol}: {e}")
        return None

def fetch_usdjpy_rate() -> float:
    """USD/JPYのリアルタイム為替レートを取得する"""
    try:
        ticker = yf.Ticker("JPY=X")
        # fast info などの最新価格を取得
        current_price = ticker.fast_info.get("last_price")
        if not current_price:
            info = ticker.info
            current_price = info.get("regularMarketPrice", 150.0) # Fallback
        return float(current_price)
    except Exception as e:
        return 150.0

def fetch_market_overview() -> dict:
    """市場全体のサマリー（S&P500, VIX, 米10年債金利）を取得"""
    try:
        data = {}
        for sym in ["^GSPC", "^VIX", "^TNX"]:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            data[sym] = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
            
        return {
            "SP500": data.get("^GSPC", 0.0),
            "VIX": data.get("^VIX", 0.0),
            "US10Y": data.get("^TNX", 0.0)
        }
    except Exception as e:
        print(f"Market Overview取得エラー: {e}")
        return {"SP500": 0.0, "VIX": 0.0, "US10Y": 0.0}
