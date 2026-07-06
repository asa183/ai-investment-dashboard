import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date
import warnings
import requests
import json
from collections import Counter
warnings.filterwarnings('ignore')

def fetch_raw_business_insights():
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {
        "formatted": "false",
        "lang": "en-US",
        "region": "US",
        "scrIds": "day_gainers",
        "count": 15
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    }
    
    insights = []
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        quotes = data['finance']['result'][0]['quotes']
        
        count = 0
        for q in quotes:
            if count >= 5: break
            symbol = q['symbol']
            price = q.get('regularMarketPrice', 0)
            if price < 5.0: continue
            
            change_pct = q.get('regularMarketChangePercent', 0)
            
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                sector = info.get('sector', 'Unknown')
                industry = info.get('industry', 'Unknown')
                summary = info.get('longBusinessSummary', '')
                if not summary: continue
                
                news_title = ""
                news_summary = ""
                try:
                    news = ticker.news
                    if news and len(news) > 0:
                        content = news[0].get('content', {})
                        if content:
                            news_title = content.get('title', '')
                            news_summary = content.get('summary', '')
                except:
                    pass
                
                insights.append({
                    "symbol": symbol,
                    "change_pct": change_pct,
                    "sector": sector,
                    "industry": industry,
                    "business_summary": summary,
                    "news_title": news_title,
                    "news_summary": news_summary
                })
                count += 1
            except:
                continue
                
    except Exception as e:
        print(f"Error fetching insights: {e}")

    output_path = "/Users/asahi_saito/investment/ai-investment-dashboard-main/raw_insights.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print(f"生のインサイトデータを {output_path} に保存しました。")

def calculate_rsi(data, periods=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd, signal

def calculate_bollinger_bands(data, window=20, num_std=2):
    rolling_mean = data.rolling(window=window).mean()
    rolling_std = data.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, lower_band

def calculate_atr(high, low, close, window=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr

def evaluate_stock_quant(hist, is_vix_high):
    hist['SMA25'] = hist['Close'].rolling(window=25).mean()
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['RSI14'] = calculate_rsi(hist['Close'])
    macd, signal = calculate_macd(hist['Close'])
    hist['MACD'] = macd
    hist['MACD_Signal'] = signal
    upper, lower = calculate_bollinger_bands(hist['Close'])
    hist['BB_Upper'] = upper
    hist['BB_Lower'] = lower
    hist['ATR'] = calculate_atr(hist['High'], hist['Low'], hist['Close'])
    hist['Vol_SMA20'] = hist['Volume'].rolling(window=20).mean()
    
    hist['Vol_Surge'] = hist['Volume'] > (hist['Vol_SMA20'] * 1.2)
    vol_surge_recent = hist['Vol_Surge'].iloc[-3:].any()

    current_price = hist['Close'].iloc[-1]
    prev_price = hist['Close'].iloc[-2]
    sma25 = hist['SMA25'].iloc[-1]
    sma50 = hist['SMA50'].iloc[-1]
    rsi = hist['RSI14'].iloc[-1]
    macd_val = hist['MACD'].iloc[-1]
    signal_val = hist['MACD_Signal'].iloc[-1]
    prev_macd = hist['MACD'].iloc[-2]
    prev_signal = hist['MACD_Signal'].iloc[-2]
    bb_upper = hist['BB_Upper'].iloc[-1]
    bb_lower = hist['BB_Lower'].iloc[-1]
    atr = hist['ATR'].iloc[-1]
    
    change_pct = ((current_price - prev_price) / prev_price) * 100
    
    macd_cross_up = (prev_macd <= prev_signal) and (macd_val > signal_val)
    macd_cross_down = (prev_macd >= prev_signal) and (macd_val < signal_val)
    uptrend_50 = current_price > sma50
    
    rating = ""
    reasons = []
    
    if is_vix_high:
        rating = "⚠️ マクロ環境悪化(見送り推奨)"
        reasons.append("VIX急騰によるシグナル無効化")
    elif macd_cross_up and vol_surge_recent:
        if uptrend_50:
            rating = "⭐ 絶好の買い場 (Strong Buy)"
            reasons.extend(["大局上昇中のMACD買い", "直近3日の出来高急増を伴う"])
        elif hist['RSI14'].iloc[-5:].min() < 40:
            rating = "🚀 大底反発シグナル (Reversal Buy)"
            reasons.extend(["50日線割れからの反発", "直近3日の出来高急増を伴う"])
        else:
            rating = "💡 打診買いサイン (Buy Signal)"
            reasons.append("MACDクロス(出来高あり)")
    elif current_price > bb_upper and rsi > 70:
        rating = "🔥 短期過熱・利確推奨 (Take Profit)"
        reasons.extend(["BB上限突破", f"RSI高水準({rsi:.0f})"])
    elif current_price > sma25 and macd_val > signal_val:
        rating = "📈 トレンド継続 (Hold)"
        reasons.append("25日線＆MACDプラス圏維持")
    elif not uptrend_50 and macd_val < signal_val:
        rating = "📉 下落トレンド (No Touch)"
        reasons.append("50日線割れ＆MACD売り")
    elif current_price < bb_lower and rsi < 30:
        rating = "🎣 逆張りチャンス (Oversold)"
        reasons.append(f"BB下限割れ＆RSI極低({rsi:.0f})")
    elif macd_cross_up:
        rating = "💡 打診買いサイン (Buy Signal)"
        reasons.append("MACDクロス(出来高不足)")
    else:
        rating = "⚖️ もみ合い・様子見 (Wait)"
        reasons.append("明確なシグナルなし")
        
    stop_loss = current_price - (2 * atr)
    
    return current_price, change_pct, stop_loss, rating, " / ".join(reasons)

def get_market_data():
    tickers = {
        "USD/JPY (為替)": {"ticker": "JPY=X", "desc": "円安・円高"},
        "米10年国債利回り": {"ticker": "^TNX", "desc": "金利動向"},
        "VIX (恐怖指数)": {"ticker": "^VIX", "desc": "パニック度"},
        
        "TQQQ (NASDAQ3倍ブル)": {"ticker": "TQQQ", "desc": "超攻撃型ハイテクETF"},
        "SOXL (半導体3倍ブル)": {"ticker": "SOXL", "desc": "超攻撃型半導体ETF"},
        
        "NVIDIA (AI半導体)": {"ticker": "NVDA", "desc": "AIの絶対王者"},
        "Microsoft (AIソフト)": {"ticker": "MSFT", "desc": "AIソフト・クラウド"},
        "Palantir (AIデータ解析)": {"ticker": "PLTR", "desc": "実用化・業務効率化"},
        "Tesla (ロボ・自動運転)": {"ticker": "TSLA", "desc": "物理世界のAI革命"},
        
        "VHT (米ヘルスケアETF)": {"ticker": "VHT", "desc": "AI創薬・バイオ"},
        
        "S&P 500 (米国株全体)": {"ticker": "^GSPC", "desc": "米国市場の主軸"},
        "日経平均 (日本株)": {"ticker": "^N225", "desc": "日本の代表指数"},
        "ビットコイン (BTC)": {"ticker": "BTC-USD", "desc": "リスク先行指標"}
    }
    
    is_vix_high = False
    vix_val = 0
    try:
        vix_data = yf.Ticker("^VIX").history(period="1mo")
        vix_val = vix_data['Close'].iloc[-1]
        if vix_val >= 25:
            is_vix_high = True
    except:
        pass
        
    nq_change = 0
    try:
        nq_data = yf.Ticker("NQ=F").history(period="5d")
        if len(nq_data) >= 2:
            nq_current = nq_data['Close'].iloc[-1]
            nq_prev = nq_data['Close'].iloc[-2]
            nq_change = ((nq_current - nq_prev) / nq_prev) * 100
    except:
        pass
        
    groups = {
        "🎯 買いチャンス (Strong Buy / Buy)": [],
        "🔥 利確推奨 (Take Profit)": [],
        "📈 トレンド継続 (Hold)": [],
        "⚖️ 様子見・もみ合い (Wait)": [],
        "📉 下落トレンド・危険 (No Touch)": [],
        "🌍 マクロ指標・その他": [],
        "⚠️ エラー": []
    }
    
    strong_buys = 0
    take_profits = 0
    no_touches = 0
    btc_rating = ""
    btc_change = 0
    
    for name, info in tickers.items():
        ticker = info["ticker"]
        desc = info["desc"]
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="1y") 
            if not hist.empty and len(hist) > 60:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                change_5d_pct = 0
                if len(hist) >= 6:
                    price_5d_ago = hist['Close'].iloc[-6]
                    change_5d_pct = ((current_price - price_5d_ago) / price_5d_ago) * 100
                
                unit = "円" if "為替" in name or "日経" in name else "%" if "利回り" in name else "ドル" if "ビットコイン" in name else "pt" if "S&P" in name or "VIX" in name else "$"
                
                rating = ""
                reasons_str = ""
                stop_loss_str = "-"
                
                if ticker == "^VIX":
                    if current_price < 20: rating = "🟢安全圏"
                    elif current_price < 25: rating = "🟡警戒"
                    else: rating = "🔴危険(パニック)"
                    reasons_str = "市場の恐怖感"
                elif ticker == "^TNX":
                    rating = "⚪️米国金利"
                    reasons_str = "ハイテク株の逆風/追い風"
                elif ticker == "JPY=X":
                    rating = "⚪️為替相場"
                    reasons_str = "日本円の価値"
                else:
                    _, _, stop_loss, rating, reasons_str = evaluate_stock_quant(hist, is_vix_high)
                    stop_loss_str = f"撤退:{stop_loss:,.0f}" if stop_loss > 1000 else f"撤退:{stop_loss:,.2f}"
                    
                name_str = name.split(' (')[0]
                price_str = f"{current_price:,.2f}{unit}"
                
                if stop_loss_str != "-":
                    price_col = f"{price_str} ({stop_loss_str})"
                else:
                    price_col = price_str
                    
                change_str = f"[日:{change_pct:+.1f}% | 週:{change_5d_pct:+.1f}%]" if ticker != "^VIX" else ""
                
                rating_short = rating.split(' (')[0] if '(' in rating else rating
                item_str = f"- {name_str} : {price_col} {change_str} -> {rating_short} ({reasons_str})"
                
                preview_parts = []
                if ticker not in ["^VIX", "^TNX", "^GSPC", "^N225", "JPY=X", "BTC-USD"]:
                    try:
                        yf_info = data.info
                        pre_price = yf_info.get('preMarketPrice')
                        
                        if pre_price and pre_price > 0:
                            pre_change = ((pre_price - current_price) / current_price) * 100
                            if abs(pre_change) > 0.2:
                                if pre_change > 0.5 and nq_change > 0:
                                    preview_parts.append(f"🌙 今夜の予測: 時間外 {pre_price:,.2f}$ (+{pre_change:.1f}%) ＋ 先物順行(強気) ＝ 🚀 ギャップアップの強いスタート予想")
                                elif pre_change < -0.5 and nq_change < 0:
                                    preview_parts.append(f"🌙 今夜の予測: 時間外 {pre_price:,.2f}$ ({pre_change:.1f}%) ＋ 先物順行(弱気) ＝ 📉 ギャップダウン警戒")
                                elif pre_change > 0.5 and nq_change < 0:
                                    preview_parts.append(f"🌙 今夜の予測: 時間外 {pre_price:,.2f}$ (+{pre_change:.1f}%) ＋ 先物逆行(弱気) ＝ ⚠️ 寄り天（ダマシ）警戒")
                                else:
                                    preview_parts.append(f"🌙 今夜の予測: 時間外 {pre_price:,.2f}$ ({pre_change:+.1f}%)")
                        
                        calendar = data.calendar
                        if calendar and 'Earnings Date' in calendar and calendar['Earnings Date']:
                            earnings_date = calendar['Earnings Date'][0]
                            if isinstance(earnings_date, date):
                                days_to_earnings = (earnings_date - date.today()).days
                                if 0 <= days_to_earnings <= 7:
                                    preview_parts.append(f"⚠️ 決算発表まであと{days_to_earnings}日 (ギャンブル回避推奨)")
                    except Exception as e:
                        pass
                
                if preview_parts:
                    item_str += f"\n  - {' / '.join(preview_parts)}"

                if '⭐' in rating_short or '🚀' in rating_short:
                    strong_buys += 1
                if '🔥' in rating_short:
                    take_profits += 1
                if '📉' in rating_short:
                    no_touches += 1
                
                if ticker == "BTC-USD":
                    btc_rating = rating_short
                    btc_change = change_pct
                    
                if any(x in rating_short for x in ['⭐', '🚀', '💡', '🎣']):
                    groups["🎯 買いチャンス (Strong Buy / Buy)"].append(item_str)
                elif '🔥' in rating_short:
                    groups["🔥 利確推奨 (Take Profit)"].append(item_str)
                elif '📈' in rating_short:
                    groups["📈 トレンド継続 (Hold)"].append(item_str)
                elif '📉' in rating_short or '🔴' in rating_short:
                    groups["📉 下落トレンド・危険 (No Touch)"].append(item_str)
                elif '⚖️' in rating_short:
                    groups["⚖️ 様子見・もみ合い (Wait)"].append(item_str)
                else:
                    groups["🌍 マクロ指標・その他"].append(item_str)
            else:
                groups["⚠️ エラー"].append(f"- {name.split(' (')[0]} : ⚠️データ取得エラー")
        except Exception as e:
            groups["⚠️ エラー"].append(f"- {name.split(' (')[0]} : ⚠️エラー")

    summary = "### 🧠 クオンツ・複合指標アナリティクス（実戦チューニング版）\n"
    summary += "【判定ルール】直近3日間の出来高急増を検知し、大局トレンド逆張り時の「大底反発シグナル」にも対応した実戦仕様です。\n"
    summary += "【プレビュー機能】時間外取引と先物の相関、および決算日までのカウントダウンから「今夜の動き」をシミュレーション表示します。\n\n"
    
    if is_vix_high:
        summary += f"- 🚨 【警告】VIXが{vix_val:.1f}と危険水準を超えています。新規エントリーは見送りを推奨します。\n"
    else:
        summary += f"- 🟢 VIXは{vix_val:.1f}で安全圏です。シグナル通りのトレードが機能しやすい状態です。\n"

    summary += "\n### 📝 今日の相場サマリー\n"
    if strong_buys >= 2:
        summary += "- 📈 買いシグナル（⭐/🚀）が複数点灯しています！絶好のエントリーチャンス（または大底反発）が到来している可能性が高いです。撤退ラインを背にして強気に攻める場面です。\n"
    elif no_touches >= 3:
        summary += "- 📉 下落トレンド（危険）の銘柄が多く、相場全体が強い調整局面です。落ちるナイフには触れず、大底反発シグナル（🚀）が点灯するのを現金を持ったまま待ちましょう。\n"
    elif take_profits >= 2:
        summary += "- 🔥 短期的な過熱・利確推奨シグナルが目立ちます。利益確定を優先し、ここからの新規の高値掴みは控えるのが無難な空気に包まれています。\n"
    else:
        summary += "- ⚖️ 銘柄ごとに方向感が分かれている「もみ合い相場」です。強いシグナルが出ている銘柄だけを個別に狙い撃ちするか、無理をせずに様子見が推奨されます。\n"

    is_weekend = datetime.today().weekday() >= 5
    if is_weekend:
        summary += "\n### 🔮 週末の先行指標（月曜オープン予測）\n"
        if "下落" in btc_rating or "危険" in btc_rating or btc_change < -3:
            summary += "- ⚠️ **BTCが週末に下落しています（炭鉱のカナリア点灯）。** 機関投資家のリスクオフ（ヘッジ売り）が先行している可能性があり、月曜日の米国市場はギャップダウン（下落スタート）に警戒が必要です。\n"
        elif "買い" in btc_rating or "大底反発" in btc_rating or btc_change > 3:
            summary += "- 🚀 **BTCが週末に強い上昇を見せています。** リスクオンのムードが先行しており、月曜日の米国ハイテク株はギャップアップ（好スタート）となる確率が高まっています。\n"
        else:
            summary += "- ⚖️ **BTCは週末にかけて安定（もみ合い）しています。** 週末に世界的なネガティブショックは起きておらず、月曜日の米国市場は無風、あるいは安定したスタートが予想されます。\n"

    report = []
    report.append(f"# 📈 投資判断クリティカル・レポート（プレビュー予測機能搭載）")
    report.append(f"*(最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')})*\n")
    report.append(summary + "\n")
    report.append("### 📊 個別銘柄ステータス\n")
    
    for group_name, items in groups.items():
        if items:
            report.append(f"#### {group_name}")
            report.extend(items)
            report.append("")
            
    output_path = "/Users/asahi_saito/investment/ai-investment-dashboard-main/daily_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"定量レポートを {output_path} に出力しました。")
    
    # 生データの取得
    print("Fetching raw business insights...")
    fetch_raw_business_insights()

if __name__ == "__main__":
    get_market_data()
