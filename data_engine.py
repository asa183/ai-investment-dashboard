import yfinance as yf
import pandas as pd
from typing import Optional

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
    """時間外取引のデータを取得します"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        pre_price = info.get('preMarketPrice', 0)
        reg_price = info.get('regularMarketPrice', 0)
        if pre_price and reg_price:
            pre_change = ((pre_price - reg_price) / reg_price) * 100
            return {"price": pre_price, "change_pct": pre_change}
        return {}
    except:
        return {}
