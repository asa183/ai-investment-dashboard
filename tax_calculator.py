import pandas as pd
import yfinance as yf
from execution import AlpacaExecutor
from datetime import datetime, timedelta
import config

def get_jpy_rates(start_date, end_date):
    """Yahoo Financeから指定期間のドル円為替レートを取得し、休日を前日のレートで埋める"""
    # 少し余裕を持たせて取得 (休日の前日データを確保するため)
    fetch_start = (pd.to_datetime(start_date) - timedelta(days=5)).strftime('%Y-%m-%d')
    fetch_end = (pd.to_datetime(end_date) + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Fetching USD/JPY rates from {fetch_start} to {fetch_end}...")
    df = yf.download('JPY=X', start=fetch_start, end=fetch_end, progress=False)
    
    if df.empty:
        raise ValueError("Failed to fetch USD/JPY rates from Yahoo Finance.")
        
    # インデックスをタイムゾーンなしのローカル日付に変換
    df.index = df.index.tz_localize(None).normalize()
    
    # 欠損日付（土日など）を全て埋めるため、日付のフルレンジを作成
    full_idx = pd.date_range(start=fetch_start, end=fetch_end)
    df_reindexed = df.reindex(full_idx)
    
    # 前日のレートで穴埋め（ffill）
    df_filled = df_reindexed.ffill()
    
    # 'Close'列のシリーズを返す
    return df_filled['Close']

def calculate_taxes():
    print("Initializing Alpaca Executor...")
    executor = AlpacaExecutor()
    
    print("Fetching trade activities (FILLs)...")
    activities = executor.api.get_activities(activity_types='FILL')
    
    if not activities:
        print("No trade activities found.")
        return
        
    # 古い順（時系列順）にソート
    activities.sort(key=lambda x: x.transaction_time)
    
    start_date = activities[0].transaction_time.date()
    end_date = activities[-1].transaction_time.date()
    
    jpy_rates = get_jpy_rates(start_date, end_date)
    
    # ポートフォリオの保有状況管理（移動平均法での単価計算）
    # positions = { 'AAPL': {'qty': 0, 'avg_cost_jpy': 0.0} }
    positions = {}
    
    report_rows = []
    
    total_realized_pnl_jpy = 0.0
    
    print("Calculating JPY tax basis and realized PnL...")
    for act in activities:
        date_obj = act.transaction_time.tz_convert('Asia/Tokyo').date()
        date_str = str(date_obj)
        
        # 該当日の為替レートを取得
        try:
            # yfinanceのCloseは単一のfloat、MultiIndexの場合は調整が必要
            rate_series = jpy_rates.loc[date_str]
            # yfinanceのバージョンによってはSeriesが返る場合がある
            rate = float(rate_series.iloc[0]) if isinstance(rate_series, pd.Series) else float(rate_series)
        except Exception as e:
            print(f"Warning: Could not find JPY rate for {date_str}. Using fallback 150.0")
            rate = 150.0
            
        symbol = act.symbol
        side = act.side
        qty = float(act.qty)
        price_usd = float(act.price)
        
        if symbol not in positions:
            positions[symbol] = {'qty': 0.0, 'avg_cost_jpy': 0.0}
            
        pos = positions[symbol]
        realized_pnl_jpy = 0.0
        
        if side == 'buy':
            # 円換算の購入額
            buy_amount_jpy = qty * price_usd * rate
            
            # 移動平均単価の更新
            new_qty = pos['qty'] + qty
            new_total_cost_jpy = (pos['qty'] * pos['avg_cost_jpy']) + buy_amount_jpy
            pos['avg_cost_jpy'] = new_total_cost_jpy / new_qty if new_qty > 0 else 0
            pos['qty'] = new_qty
            
            amount_jpy_str = f"-¥{int(buy_amount_jpy):,}"
            
        elif side == 'sell':
            # 円換算の売却額
            sell_amount_jpy = qty * price_usd * rate
            
            # 売却益（譲渡益）の計算 ＝ 売却額 − (取得単価 × 売却数)
            cost_basis_jpy = qty * pos['avg_cost_jpy']
            realized_pnl_jpy = sell_amount_jpy - cost_basis_jpy
            total_realized_pnl_jpy += realized_pnl_jpy
            
            # 保有数の更新（空売り非対応前提）
            pos['qty'] -= qty
            
            amount_jpy_str = f"+¥{int(sell_amount_jpy):,}"
            
        # レポート行の作成
        report_rows.append({
            '日付(JST)': date_str,
            '銘柄': symbol,
            '売買': '買' if side == 'buy' else '売',
            '数量': qty,
            '約定単価(USD)': price_usd,
            '為替レート(USD/JPY)': round(rate, 2),
            '受渡金額(JPY)': amount_jpy_str,
            '確定損益(JPY)': int(realized_pnl_jpy) if side == 'sell' else 0
        })

    # CSVエクスポート
    df_report = pd.DataFrame(report_rows)
    output_file = config.BASE_DIR / 'tax_report.csv'
    df_report.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"📊 確定申告用データ生成完了: {output_file}")
    print(f"💰 通算確定損益（円換算）: ¥{int(total_realized_pnl_jpy):,}")
    print("="*50 + "\n")
    print("※注意: 本スクリプトは移動平均法を用いて計算しています。実際の税務申告の際は、必ずご自身の税理士にご確認ください。")

if __name__ == "__main__":
    calculate_taxes()
