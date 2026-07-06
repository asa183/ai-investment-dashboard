import pandas as pd
import numpy as np

def calculate_rsi(data: pd.Series, periods=14) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data: pd.Series, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd, signal

def calculate_bollinger_bands(data: pd.Series, window=20, num_std=2):
    rolling_mean = data.rolling(window=window).mean()
    rolling_std = data.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, lower_band

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Average True Range (ATR) を計算し、最新の値を返す"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1])

def calculate_dynamic_position_size(total_equity: float, risk_pct: float, current_price: float, atr: float) -> int:
    """
    ATRベースの動的ロット計算 (リスク・パリティ)
    許容リスク額 = 総資産 * リスク許容度(%)
    1株あたりのリスク = ATR * 2 (余裕を持たせたストップロス幅)
    発注株数 = 許容リスク額 / 1株あたりのリスク
    """
    if atr == 0 or current_price == 0:
        return 0
    risk_amount = total_equity * risk_pct
    risk_per_share = atr * 2.0 
    
    # 割り当て株数を計算し、整数に切り捨て
    shares = int(risk_amount / risk_per_share)
    return shares

def evaluate_signals(df: pd.DataFrame, volume_multiplier: float = 1.5):
    """
    データフレームを評価し、シグナルを返す
    Returns: (signal_type, reason, is_buy)
    """
    if len(df) < 50:
        return "⚖️ もみ合い・様子見", "データ不足", False
        
    close = df['Close']
    volume = df['Volume']
    
    rsi = calculate_rsi(close)
    macd, macd_signal = calculate_macd(close)
    bb_upper, bb_lower = calculate_bollinger_bands(close)
    sma50 = close.rolling(window=50).mean()
    sma25 = close.rolling(window=25).mean()
    
    current_price = close.iloc[-1]
    current_volume = volume.iloc[-1]
    avg_volume = volume.rolling(window=20).mean().iloc[-1]
    
    vol_spike = current_volume > (avg_volume * volume_multiplier)
    
    # シグナル判定ロジック（旧スクリプトからの移植）
    if current_price < sma50.iloc[-1] and rsi.iloc[-1] < 40 and vol_spike and current_price > close.iloc[-2]:
        return "🚀 大底反発シグナル", "50日線割れからの反発 / 直近の出来高急増を伴う", True
    
    if macd.iloc[-1] > macd_signal.iloc[-1] and macd.iloc[-2] <= macd_signal.iloc[-2]:
        if vol_spike:
            return "⭐ MACDゴールデンクロス", "強い買いシグナル", True
        else:
            return "💡 打診買いサイン", "MACDクロス(出来高不足)", True
            
    if current_price > bb_upper.iloc[-1] or rsi.iloc[-1] > 75:
        return "🔥 短期過熱・利確推奨", f"BB上限突破 / RSI高水準({rsi.iloc[-1]:.0f})", False
        
    if current_price < sma50.iloc[-1] and macd.iloc[-1] < macd_signal.iloc[-1]:
        return "📉 下落トレンド", "50日線割れ＆MACD売り", False
        
    if current_price > sma25.iloc[-1] and macd.iloc[-1] > 0:
        return "📈 トレンド継続", "25日線＆MACDプラス圏維持", False
        
    return "⚖️ もみ合い・様子見", "明確なシグナルなし", False
