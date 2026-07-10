import config
from data_engine import fetch_daily_data_batch
from alpha_strategy import evaluate_signals
from main_bot import generate_markdown_report, is_market_open_for_symbol

def run_local_report():
    print("ローカル環境で市場データを取得し、レポートを生成しています...")
    # 現在開いている市場の銘柄、またはテスト用に全銘柄
    active_symbols = [sym for sym in config.TARGET_SYMBOLS if is_market_open_for_symbol(sym)]
    if not active_symbols:
        active_symbols = config.TARGET_SYMBOLS
        
    historical_data = fetch_daily_data_batch(active_symbols)
    symbols_data = {}
    
    for symbol in active_symbols:
        df = historical_data.get(symbol)
        if df is None:
            continue
            
        signal_type, reason, is_buy = evaluate_signals(df, config.VOLUME_SPIKE_MULTIPLIER, None)
        action_text = "様子見・保有継続"
        
        if is_buy:
            action_text = "【ローカル判定】買い対象"
        elif signal_type in [config.SignalName.SHORT_TERM_OVERHEAT, config.SignalName.TREND_BREAKDOWN, config.SignalName.ATR_STOP_LOSS]:
            action_text = "【ローカル判定】売り対象"
            
        symbols_data[symbol] = {
            "signal": signal_type,
            "reason": reason,
            "action": action_text
        }
        
    # MoomooAPIを使わずにレポートだけを生成（ポジションなし、初期資金1000万で仮置き）
    generate_markdown_report(symbols_data, config.PAPER_TRADE_BASE_EQUITY, {})
    print("レポートの生成が完了しました！")

if __name__ == "__main__":
    run_local_report()
