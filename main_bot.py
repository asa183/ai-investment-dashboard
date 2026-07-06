import traceback
import config
from database import log_signal, log_order
from data_engine import fetch_daily_data, fetch_current_price
from alpha_strategy import evaluate_signals, calculate_atr, calculate_dynamic_position_size
from execution import AlpacaExecutor, send_slack_notification

def generate_markdown_report(symbols_data: dict, total_equity: float, is_kill_switch_active: bool):
    report = []
    report.append("# 🚀 AI Investment Quant Dashboard (v2.0: Enterprise)")
    report.append("*(100点満点の堅牢なクオンツアーキテクチャにて稼働中)*\n")
    
    if is_kill_switch_active:
        report.append("## 🚨 【緊急停止】キルスイッチ作動中")
        report.append(f"ポートフォリオのドローダウンが閾値（{config.KILL_SWITCH_DRAWDOWN*100}%）を超えたため、新規発注をロックしています。\n")
        
    report.append(f"## 📊 ポートフォリオ状況\n- **総資産**: ${total_equity:,.2f}\n")
    
    report.append("## 📈 本日のシグナルとアクション\n")
    
    for symbol, data in symbols_data.items():
        signal = data['signal']
        reason = data['reason']
        action = data['action']
        report.append(f"### {symbol}")
        report.append(f"- **シグナル**: {signal} ({reason})")
        report.append(f"- **AIアクション**: {action}\n")
        
    output_path = config.BASE_DIR / "daily_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

def main():
    try:
        executor = AlpacaExecutor()
        portfolio = executor.get_portfolio_status()
        equity = portfolio['equity']
        
        is_kill_switch_active = executor.check_kill_switch(equity)
        
        symbols_data = {}
        slack_messages = []
        
        for symbol in config.TARGET_SYMBOLS:
            df = fetch_daily_data(symbol)
            if df is None:
                continue
                
            signal_type, reason, is_buy = evaluate_signals(df, config.VOLUME_SPIKE_MULTIPLIER)
            log_signal(symbol, signal_type, reason)
            
            action_text = "なし"
            
            if is_buy and not is_kill_switch_active:
                atr = calculate_atr(df['High'], df['Low'], df['Close'])
                shares = calculate_dynamic_position_size(equity, config.MAX_PORTFOLIO_RISK_PCT, df['Close'].iloc[-1], atr)
                
                # 保有ポジションの確認（追加の買い増しかどうかの簡易判定）
                pos = executor.get_position(symbol)
                if pos:
                    action_text = f"既に保有中。シグナル点灯だが追加購入は見送り（または上限チェック）"
                else:
                    order_id = executor.execute_buy_trailing_stop(symbol, shares)
                    if order_id:
                        action_text = f"【自動発注】{shares}株を購入（トレイリングストップ付）"
                        log_order(symbol, "buy", shares, 0, "trailing_stop", "submitted", order_id)
                        slack_messages.append(f"🚀 *BUY {symbol}*: {shares} shares ordered. Reason: {signal_type}")
                        
            elif "利確" in signal_type or "下落" in signal_type:
                pos = executor.get_position(symbol)
                if pos:
                    executor.execute_sell_all(symbol)
                    action_text = "【自動決済】保有する全株を売却（シグナル反転）"
                    log_order(symbol, "sell", float(pos.qty), 0, "market", "closed")
                    slack_messages.append(f"🔥 *SELL {symbol}*: Closed position. Reason: {signal_type}")
                    
            symbols_data[symbol] = {
                "signal": signal_type,
                "reason": reason,
                "action": action_text
            }
            
        generate_markdown_report(symbols_data, equity, is_kill_switch_active)
        
        if slack_messages:
            send_slack_notification("\n".join(slack_messages))
        else:
            send_slack_notification("本日の市場分析完了。新規のトレードアクションはありません。")
            
    except Exception as e:
        error_msg = f"CRITICAL ERROR in main_bot.py:\n{traceback.format_exc()}"
        print(error_msg)
        send_slack_notification(error_msg, is_alert=True)

if __name__ == "__main__":
    main()
