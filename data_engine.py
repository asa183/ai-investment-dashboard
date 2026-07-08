import time
import random
import yfinance as yf
import pandas as pd
from typing import Optional, Dict, List

_usdjpy_cache = None

def fetch_daily_data_batch(symbols: List[str], periods: int = 100) -> Dict[str, pd.DataFrame]:
    """
    指定された複数銘柄の過去データをバッチ取得し、辞書で返します。
    Bot検知を避けるため、JP/USでチャンクに分け、待機時間を設けます。
    """
    result = {}
    
    jp_symbols = [s for s in symbols if s.endswith('.T')]
    us_symbols = [s for s in symbols if not s.endswith('.T')]
    
    def process_chunks(target_symbols, is_jp):
        chunk_size = 5
        for i in range(0, len(target_symbols), chunk_size):
            chunk = target_symbols[i:i + chunk_size]
            print(f"Fetching chunk: {chunk}")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    df = yf.download(chunk, period="1y", group_by="ticker", threads=False, progress=False)
                    
                    if df.empty:
                        raise ValueError("Downloaded dataframe is empty (Possible IP Ban or Rate limit)")
                    
                    success_count = 0
                    if len(chunk) == 1:
                        df_clean = df.dropna(how='all')
                        if not df_clean.empty:
                            result[chunk[0]] = df_clean.tail(periods)
                            success_count += 1
                    else:
                        for sym in chunk:
                            if sym in df.columns.levels[0]:
                                sym_df = df[sym].dropna(how='all')
                                if not sym_df.empty:
                                    result[sym] = sym_df.tail(periods)
                                    success_count += 1
                            elif len(chunk) > 1 and len(df.columns.levels) == 1:
                                if sym in df.columns:
                                    sym_df = pd.DataFrame(df[sym]).dropna(how='all')
                                    if not sym_df.empty:
                                        result[sym] = sym_df.tail(periods)
                                        success_count += 1
                    
                    if success_count == 0:
                        raise ValueError("No valid data retrieved in this chunk")
                        
                    break 
                except Exception as e:
                    print(f"Error fetching {chunk} (Attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(5 * (attempt + 1))
            
            time.sleep(random.uniform(2.0, 4.0))

    if jp_symbols:
        process_chunks(jp_symbols, is_jp=True)
    if us_symbols:
        process_chunks(us_symbols, is_jp=False)
        
    return result

def fetch_daily_data(symbol: str, periods: int = 100) -> Optional[pd.DataFrame]:
    """(レガシー互換用)"""
    try:
        time.sleep(random.uniform(1.0, 2.0))
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
        time.sleep(random.uniform(1.0, 2.0))
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
            time.sleep(random.uniform(1.0, 2.0))
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
