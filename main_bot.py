import traceback
import argparse
import config
from database import log_signal, log_order, init_db
from data_engine import fetch_daily_data, fetch_pre_market_price, fetch_usdjpy_rate
from alpha_strategy import evaluate_signals, calculate_atr, calculate_dynamic_position_size
from execution import MoomooExecutor
from notifier import send_slack_notification
import messages
import datetime

def is_market_open_for_symbol(symbol: str) -> bool:
    """現在時刻から、対象市場（US/JP）がオープンしているか判定（大まかな時差フィルター）"""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(jst)
    
    is_jp = symbol.endswith('.T')
    if is_jp:
        return 8 <= now.hour <= 16
    else:
        return now.hour >= 21 or now.hour <= 7

def generate_markdown_report(symbols_data: dict, total_equity: float):
    report = [
        "# 🚀 AI Investment Quant Dashboard (Moomoo Edition)",
        "*(Automated Swing Trading System)*\n",
        f"## 📊 ポートフォリオ概算総資産: ¥{total_equity:,.0f}\n",
        "## 📈 本日のシグナルとアクション\n"
    ]
    
    buys = []
    sells = []
    holds = []
    
    for symbol, data in symbols_data.items():
        action = data['action']
        row = f"| **{symbol}** | {data['signal']} | {action} | {data['reason']} |"
        
        if "買" in action or "buy" in action.lower():
            buys.append(row)
        elif "決済" in action or "売" in action or "sell" in action.lower():
            sells.append(row)
        else:
            holds.append(row)
            
    # ヘッダー定義
    table_header = "| 銘柄 | シグナル | アクション | 詳細理由 |\n|---|---|---|---|"
    
    if buys:
        report.extend(["### 🟢 買いシグナル (Buy)", table_header] + buys + ["\n"])
    if sells:
        report.extend(["### 🔴 決済・売りシグナル (Sell)", table_header] + sells + ["\n"])
    if holds:
        report.extend(["### ⚖️ 様子見・見送り (Hold / Skip)", table_header] + holds + ["\n"])
        
    output_path = config.BASE_DIR / "daily_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

def run_trade_mode(executor: MoomooExecutor, equity: float):
    """【ジョブ1】市場オープン中のトレード実行モード"""
    symbols_data = {}
    slack_blocks = ["*🤖 自動トレード実行レポート*"]
    
    # 現在の全ポジションを取得
    positions = executor.get_positions()
    usdjpy_rate = fetch_usdjpy_rate()

    for symbol in config.TARGET_SYMBOLS:
        if not is_market_open_for_symbol(symbol):
            continue
            
        df = fetch_daily_data(symbol)
        if df is None:
            continue
            
        signal_type, reason, is_buy = evaluate_signals(df, config.VOLUME_SPIKE_MULTIPLIER)
        action_text = "なし"
        
        # プレマーケット暴落フィルター
        if is_buy:
            pre_market = fetch_pre_market_price(symbol)
            if pre_market and pre_market.get("change_pct", 0) <= config.PRE_MARKET_DROP_LIMIT:
                action_text = f"【発注ブロック】プレマーケット暴落({pre_market['change_pct']:.1f}%)"
                reason += f" (※暴落回避: {pre_market['change_pct']:.1f}%)"
                is_buy = False
        
        log_signal(symbol, signal_type, reason)
        pos = positions.get(symbol)
        
        if is_buy:
            if pos and pos['qty'] > 0:
                action_text = "既に保有中のため追加購入は見送り"
            else:
                atr = calculate_atr(df['High'], df['Low'], df['Close'])
                current_price = df['Close'].iloc[-1]
                is_us_stock = not symbol.endswith('.T')
                
                shares = calculate_dynamic_position_size(
                    equity=equity, 
                    current_price=current_price, 
                    atr=atr, 
                    is_us_stock=is_us_stock,
                    usdjpy_rate=usdjpy_rate,
                    risk_per_trade=config.MAX_PORTFOLIO_RISK_PCT
                )
                
                if shares <= 0:
                    req_funds = current_price * 100 if not is_us_stock else current_price
                    action_text = "【見送り】資金不足（リスク超過）"
                    
                    req_funds_jpy = req_funds * usdjpy_rate if is_us_stock else req_funds
                    curr_price_jpy = current_price * usdjpy_rate if is_us_stock else current_price
                    
                    msg = messages.INSUFFICIENT_FUNDS_TEMPLATE.format(
                        symbol=symbol,
                        min_shares=100 if not is_us_stock else 1,
                        required_funds=f"¥{req_funds_jpy:,.0f}",
                        current_price=f"¥{curr_price_jpy:,.0f}"
                    )
                    slack_blocks.append(msg)
                else:
                    # Moomoo経由で現物買い（成行）
                    executor.submit_order(symbol, shares, 'buy')
                    action_text = f"【自動発注】{shares}株を購入"
                    log_order(symbol, "buy", shares, current_price, "market", "submitted")
                    
                    curr_price_jpy = current_price * usdjpy_rate if is_us_stock else current_price
                    msg = messages.get_trade_execution_msg(symbol, messages.TERM_BUY, shares, curr_price_jpy)
                    slack_blocks.append(f"{msg}\n> 理由: {signal_type}")
                
        elif "利確" in signal_type or "下落" in signal_type:
            if pos and pos['qty'] > 0:
                executor.close_position(symbol)
                action_text = "【自動決済】保有株をすべて売却"
                log_order(symbol, "sell", pos['qty'], pos['current_price'], "market", "closed")
                
                is_us_stock = not symbol.endswith('.T')
                curr_price_jpy = pos['current_price'] * usdjpy_rate if is_us_stock else pos['current_price']
                msg = messages.get_trade_execution_msg(symbol, messages.TERM_SELL, pos['qty'], curr_price_jpy)
                slack_blocks.append(f"{msg}\n> 理由: {signal_type}")
                
        symbols_data[symbol] = {
            "signal": signal_type,
            "reason": reason,
            "action": action_text
        }
        
    generate_markdown_report(symbols_data, equity)
    
    if len(slack_blocks) > 1:
        send_slack_notification("\n\n".join(slack_blocks))

def run_summary_mode(executor: MoomooExecutor, equity: float):
    """【ジョブ2】市場クローズ後のサマリー報告モード"""
    usdjpy_rate = fetch_usdjpy_rate()
    positions = executor.get_positions()
    
    # ペーパートレードなどで全米株・日本株の含み損益を正確にJPYベースで合算する
    total_unrealized_jpy = 0.0
    if positions:
        for symbol, pos in positions.items():
            is_us_stock = not symbol.endswith('.T')
            rate = usdjpy_rate if is_us_stock else 1.0
            total_unrealized_jpy += pos['unrealized_pnl'] * rate

    # サマリーヘッダー
    slack_msg = [messages.get_daily_summary_header(equity, total_unrealized_jpy)]
    
    # 各銘柄の状況
    if positions:
        for symbol, pos in positions.items():
            is_us_stock = not symbol.endswith('.T')
            rate = usdjpy_rate if is_us_stock else 1.0
            
            entry_jpy = pos['entry_price'] * rate
            curr_jpy = pos['current_price'] * rate
            pnl_jpy = pos['unrealized_pnl'] * rate
            
            pos_msg = messages.get_position_detail_msg(
                symbol, pos['qty'], entry_jpy, curr_jpy, 
                pnl_jpy, pos['pnl_pct']
            )
            slack_msg.append(pos_msg)
    else:
        slack_msg.append("保有銘柄はありません。")
        
    slack_msg.append("\n※詳細はVPS上の `daily_report.md` または Moomooアプリを確認してください。")
    send_slack_notification("\n\n".join(slack_msg))

def main():
    parser = argparse.ArgumentParser(description="AI Investment Quant Bot (Moomoo Edition)")
    parser.add_argument('--trade', action='store_true', help="Run in trade execution mode")
    parser.add_argument('--summary', action='store_true', help="Run in daily summary mode")
    parser.add_argument('--paper', action='store_true', help="Run in Paper Trading mode (Simulate)")
    args = parser.parse_args()

    if not args.trade and not args.summary:
        print("Please specify --trade or --summary flag.")
        return

    try:
        init_db()  # ローカルDB初期化
        # MoomooExecutorの初期化 (引数でPaperかLiveかを切り替え)
        executor = MoomooExecutor(is_paper=args.paper)
        
        if args.paper:
            # ペーパートレード時はMoomooの残高を無視し、500万円ベースで計算
            print(f"📊 ペーパートレードモード: 仮想総資産を ¥{config.PAPER_TRADE_BASE_EQUITY:,.0f} として稼働します。")
            equity = config.PAPER_TRADE_BASE_EQUITY
        else:
            portfolio = executor.get_portfolio_status()
            equity = portfolio['equity']
            
            # Moomooの場合は資産がゼロの場合（口座未入金など）に備える
            if equity <= 0:
                print("Warning: Total equity is 0 or less. Using fallback of ¥1,000,000 for sizing.")
                equity = 1000000.0
            
        if args.trade:
            run_trade_mode(executor, equity)
            
        elif args.summary:
            run_summary_mode(executor, equity)
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR:\n{error_trace}")
        
        error_msg = messages.get_error_msg("Bot Execution Failed", str(e))
        send_slack_notification(error_msg)

if __name__ == "__main__":
    main()
