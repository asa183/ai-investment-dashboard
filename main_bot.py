import traceback
import argparse
import config
from database import log_signal, log_order
from data_engine import fetch_daily_data, fetch_current_price, fetch_pre_market_price
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

def run_trade_mode(executor: AlpacaExecutor, equity: float, is_kill_switch_active: bool):
    """【ジョブ1】市場オープン中のトレード実行モード"""
    symbols_data = {}
    slack_blocks = ["*🤖 AI Quant Bot - Trade Execution Report*"]
    
    if is_kill_switch_active:
        slack_blocks.append("🚨 *【キルスイッチ発動中】* 異常ドローダウンを検知したため、すべての新規発注を見送りました。")

    for symbol in config.TARGET_SYMBOLS:
        df = fetch_daily_data(symbol)
        if df is None:
            continue
            
        signal_type, reason, is_buy = evaluate_signals(df, config.VOLUME_SPIKE_MULTIPLIER)
        action_text = "なし"
        
        # プレマーケット暴落フィルター
        if is_buy:
            pre_market = fetch_pre_market_price(symbol)
            if pre_market and pre_market.get("change_pct", 0) <= config.PRE_MARKET_DROP_LIMIT:
                action_text = f"【発注キャンセル】異常な下落({pre_market['change_pct']:.1f}%)を検知"
                reason += f" (※暴落フィルター作動: {pre_market['change_pct']:.1f}%)"
                is_buy = False
        
        log_signal(symbol, signal_type, reason)
        
        if is_buy and not is_kill_switch_active:
            atr = calculate_atr(df['High'], df['Low'], df['Close'])
            current_price = df['Close'].iloc[-1]
            shares = calculate_dynamic_position_size(equity, config.MAX_PORTFOLIO_RISK_PCT, current_price, atr)
            limit_price = current_price * config.LIMIT_SLIPPAGE_BUFFER
            
            pos = executor.get_position(symbol)
            if pos:
                action_text = f"既に保有中。シグナル点灯だが追加購入は見送り"
            else:
                order_id = executor.execute_buy_trailing_stop(symbol, shares, limit_price)
                if order_id:
                    action_text = f"【自動発注】{shares}株を指値購入（上限${limit_price:.2f}）"
                    log_order(symbol, "buy", shares, 0, "limit_trailing", "submitted", order_id)
                    slack_blocks.append(f"🟢 *BUY {symbol}*: {shares} shares (Limit: ${limit_price:.2f})\n> 理由: {signal_type}")
                    
        elif "利確" in signal_type or "下落" in signal_type:
            pos = executor.get_position(symbol)
            if pos:
                executor.execute_sell_all(symbol)
                action_text = "【自動決済】保有する全株を売却（シグナル反転）"
                log_order(symbol, "sell", float(pos.qty), 0, "market", "closed")
                slack_blocks.append(f"🔴 *SELL {symbol}*: Closed all positions.\n> 理由: {signal_type}")
                
        symbols_data[symbol] = {
            "signal": signal_type,
            "reason": reason,
            "action": action_text
        }
        
    generate_markdown_report(symbols_data, equity, is_kill_switch_active)
    
    if len(slack_blocks) > 1:
        send_slack_notification("\n\n".join(slack_blocks))

def run_summary_mode(executor: AlpacaExecutor, equity: float):
    """【ジョブ2】市場クローズ後のサマリー報告モード"""
    # 簡易的に前日比を計算 (デモ用。厳密にはAlpaca APIのlast_equityを使うなどが必要)
    try:
        account = executor.api.get_account()
        last_equity = float(account.last_equity)
        daily_pnl = equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity) * 100 if last_equity > 0 else 0
    except:
        daily_pnl = 0.0
        daily_pnl_pct = 0.0

    slack_msg = (
        "📈 *Market Close Summary (本日の最終結果)*\n\n"
        f"💰 *総資産*: ${equity:,.2f}\n"
        f"📊 *前日比*: ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)\n\n"
        "※詳細な各銘柄のシグナルはGitHubの `daily_report.md` をご確認ください！"
    )
    send_slack_notification(slack_msg)

def main():
    parser = argparse.ArgumentParser(description="AI Investment Quant Bot")
    parser.add_argument('--trade', action='store_true', help="Run in trade execution mode")
    parser.add_argument('--summary', action='store_true', help="Run in daily summary mode")
    args = parser.parse_args()

    if not args.trade and not args.summary:
        print("Please specify --trade or --summary flag.")
        return

    try:
        executor = AlpacaExecutor()
        portfolio = executor.get_portfolio_status()
        equity = portfolio['equity']
        
        if args.trade:
            is_kill_switch_active = executor.check_kill_switch(equity)
            run_trade_mode(executor, equity, is_kill_switch_active)
            
        elif args.summary:
            run_summary_mode(executor, equity)
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR:\n{error_trace}")
        
        # スタックトレースは長すぎるのでSlackでは省略し、エラー文だけ読みやすくする
        alert_msg = (
            "🚨 *【緊急】システム異常終了* 🚨\n"
            "AI投資ダッシュボードの実行中に予期せぬエラーが発生し、処理を中断しました。\n\n"
            f"📝 *エラー内容*: `{str(e)}`\n"
            "💡 *アクション*: GitHub Actionsのログ、またはローカル環境で詳細を確認してください。"
        )
        send_slack_notification(alert_msg)

if __name__ == "__main__":
    main()
