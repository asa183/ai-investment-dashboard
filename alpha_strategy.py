import pandas as pd
import numpy as np
from config import SignalName

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

def calculate_bb_width(upper_band: pd.Series, lower_band: pd.Series, sma: pd.Series) -> pd.Series:
    return (upper_band - lower_band) / sma

def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, periods: int = 14) -> pd.Series:
    """Calculate ADX (Average Directional Index)"""
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()
    
    plus_dm_true = np.where((plus_dm > minus_dm), plus_dm, 0)
    minus_dm_true = np.where((minus_dm > plus_dm), minus_dm, 0)
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=periods).mean()
    
    plus_di = 100 * (pd.Series(plus_dm_true, index=high.index).rolling(window=periods).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm_true, index=low.index).rolling(window=periods).mean() / atr)
    
    dx_den = plus_di + minus_di
    dx_val = np.where(dx_den == 0, 0, (abs(plus_di - minus_di) / dx_den) * 100)
    
    dx = pd.Series(dx_val, index=high.index)
    adx = dx.rolling(window=periods).mean()
    return adx

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Average True Range (ATR) を計算し、最新の値を返す"""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1])

def calculate_dynamic_position_size(
    equity: float, 
    current_price: float, 
    atr: float, 
    is_us_stock: bool = True,
    usdjpy_rate: float = 150.0,
    risk_per_trade: float = 0.02,
    available_cash: float = None
) -> int:
    """
    ATRベースの動的ポジションサイジング
    リスク金額 = 総資金 * risk_per_trade
    許容値幅 = ATR * 1.5
    """
    if current_price <= 0 or atr <= 0:
        return 0
        
    risk_amount = equity * risk_per_trade
    max_investment = equity * 0.20 # 総資金の20%を上限とする
    
    if available_cash is not None:
        max_investment = min(max_investment, available_cash)

    
    if is_us_stock:
        # 米国株の場合、価格とATRはUSD。equity(JPY)をUSDに変換して計算
        risk_amount_usd = risk_amount / usdjpy_rate
        max_investment_usd = max_investment / usdjpy_rate
        
        stop_loss_distance = atr * 1.5 
        shares = int(risk_amount_usd / stop_loss_distance)
        max_shares = int(max_investment_usd / current_price)
        
        return min(shares, max_shares)
    else:
        # 日本株の場合、価格とATRはJPY。
        stop_loss_distance = atr * 1.5 
        shares = int(risk_amount / stop_loss_distance)
        max_shares = int(max_investment / current_price)
        
        final_shares = min(shares, max_shares)
        # 日本株は単元株(100株)単位に切り捨てる
        return (final_shares // 100) * 100

def evaluate_signals(df: pd.DataFrame, volume_multiplier: float = 1.5, position_data: dict = None):
    """
    データフレームを評価し、シグナルを返す
    Returns: (signal_type, reason, is_buy)
    """
    if len(df) < 50:
        return SignalName.RANGE_BOUND, "データ不足", False
        
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    rsi = calculate_rsi(close)
    macd, macd_signal = calculate_macd(close)
    bb_upper, bb_lower = calculate_bollinger_bands(close)
    sma20 = close.rolling(window=20).mean()
    bb_width = calculate_bb_width(bb_upper, bb_lower, sma20)
    adx = calculate_adx(high, low, close)
    atr_val = calculate_atr(high, low, close)
    
    sma50 = close.rolling(window=50).mean()
    sma25 = close.rolling(window=25).mean()
    
    current_price = close.iloc[-1]
    current_volume = volume.iloc[-1]
    avg_volume = volume.rolling(window=20).mean().iloc[-1]
    
    vol_spike = current_volume > (avg_volume * volume_multiplier)
    
    # 1. 逃げ: ATR即時撤退（損切り）チェック
    import config as cfg
    if position_data and position_data.get('qty', 0) > 0:
        entry_price = position_data['entry_price']
        stop_loss_price = entry_price - (atr_val * cfg.ATR_TRAILING_MULTIPLIER)
        if current_price < stop_loss_price:
            return SignalName.ATR_STOP_LOSS, f"現在値が安全圏(¥{stop_loss_price:.1f})を下回りました", False

    # 2. 利確: 短期過熱チェック
    if current_price > bb_upper.iloc[-1] or rsi.iloc[-1] > 75:
        return SignalName.SHORT_TERM_OVERHEAT, f"BB上限突破 / RSI高水準({rsi.iloc[-1]:.0f})", False
        
    # 3. 逆張り: 大底反発
    if current_price < sma50.iloc[-1] and rsi.iloc[-1] < 40 and vol_spike and current_price > close.iloc[-2]:
        return SignalName.BOTTOM_REVERSAL, "50日線割れからの反発 / 直近の出来高急増", True

    # --- 環境認識 (Regime Detection) ---
    curr_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
    avg_bbw = bb_width.rolling(window=20).mean().iloc[-1] if not pd.isna(bb_width.iloc[-1]) else 0
    curr_bbw = bb_width.iloc[-1]
    
    is_squeeze = curr_bbw < avg_bbw
    is_ranging = curr_adx < 25 and is_squeeze

    # 4. 攻め: ボラティリティ・ブレイクアウト
    is_breaking_out = (current_price > bb_upper.iloc[-1]) and (current_volume > avg_volume * 2.0)
    if is_ranging and is_breaking_out:
        return SignalName.VOLATILITY_BREAKOUT, "エネルギー圧縮(スクイーズ)からの大陽線ブレイク", True

    # 5. 守り: レンジ相場でのダマシ回避（以降のトレンドシグナルをブロック）
    if is_ranging:
        return SignalName.RANGE_BOUND, f"レンジ相場検知 (ADX:{curr_adx:.1f}, BB幅収縮)", False

    # 6. 順張り: トレンドフォロー (MACD)
    if macd.iloc[-1] > macd_signal.iloc[-1] and macd.iloc[-2] <= macd_signal.iloc[-2]:
        if vol_spike:
            return SignalName.MACD_GOLDEN_CROSS, "強い買いシグナル", True
        else:
            return SignalName.MACD_TEST_BUY, "MACDクロス(出来高不足)", True
            
    if current_price < sma50.iloc[-1] and macd.iloc[-1] < macd_signal.iloc[-1]:
        return SignalName.TREND_BREAKDOWN, "50日線割れ＆MACD売り", False
        
    if current_price > sma25.iloc[-1] and macd.iloc[-1] > 0:
        # テスト運用向け：上昇トレンド中で、RSIが55以下（少し下がった状態）から反発した時に「押し目買い」
        if rsi.iloc[-1] < 60 and rsi.iloc[-1] > rsi.iloc[-2] and current_price > close.iloc[-2]:
            return "📈 押し目買いサイン", "上昇トレンド中の短期的な下落からの反発検知", True
        return SignalName.TREND_CONTINUATION, "25日線＆MACDプラス圏維持", False
        
    return SignalName.RANGE_BOUND, "明確なシグナルなし", False
