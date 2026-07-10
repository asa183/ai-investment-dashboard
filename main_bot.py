import traceback
import argparse
import config
from data_engine import fetch_daily_data_batch, fetch_daily_data, fetch_pre_market_price, fetch_usdjpy_rate
from alpha_strategy import evaluate_signals, calculate_atr, calculate_dynamic_position_size
from execution import MoomooExecutor
from notifier import send_slack_notification
import messages
import datetime
from db_models import init_db, get_session, SignalHistory, PortfolioHistory

def is_market_open_for_symbol(symbol: str) -> bool:
    """現在時刻から、対象市場（US/JP）がオープンしているか判定（大まかな時差フィルター）"""
    jst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(jst)
    
    is_jp = symbol.endswith('.T')
    if is_jp:
        return 8 <= now.hour <= 16
    else:
        return now.hour >= 21 or now.hour <= 7

def generate_markdown_report(symbols_data: dict, total_equity: float, positions: dict = None):
    from data_engine import fetch_market_overview, fetch_usdjpy_rate
    overview = fetch_market_overview()
    rate = fetch_usdjpy_rate()
    positions = positions or {}
    
    total_unrealized_jpy = 0.0
    for symbol, pos in positions.items():
        is_us = not symbol.endswith('.T')
        fx = rate if is_us else 1.0
        total_unrealized_jpy += pos['unrealized_pnl'] * fx
    
    report = [
        "# 🚀 AI Investment Quant Dashboard (Moomoo Edition)",
        "*(Automated Swing Trading System)*\n",
        "## 📊 ポートフォリオ状況",
        f"- **概算総資産**: ¥{total_equity:,.0f}",
        f"- **全体含み損益**: ¥{total_unrealized_jpy:,.0f}\n",
        "## 🌍 Market Overview",
        f"- **S&P 500**: {overview['SP500']:,.2f}",
        f"- **VIX (恐怖指数)**: {overview['VIX']:.2f}",
        f"- **米国10年債金利**: {overview['US10Y']:.3f}%",
        f"- **USD/JPY**: ¥{rate:.2f}\n",
        "## 💼 現在の保有ポジション\n"
    ]
    
    if positions:
        report.append("| 銘柄 | 保有数 | 取得単価 | 現在値 | 含み損益 | 損益率 |")
        report.append("|---|---|---|---|---|---|")
        for symbol, pos in positions.items():
            is_us = not symbol.endswith('.T')
            fx = rate if is_us else 1.0
            entry_jpy = pos['entry_price'] * fx
            curr_jpy = pos['current_price'] * fx
            pnl_jpy = pos['unrealized_pnl'] * fx
            icon = "🟩" if pnl_jpy >= 0 else "🟥"
            name = config.SYMBOL_NAMES.get(symbol, symbol)
            report.append(f"| {icon} **{name} ({symbol})** | {pos['qty']}株 | ¥{entry_jpy:,.0f} | ¥{curr_jpy:,.0f} | ¥{pnl_jpy:,.0f} | {pos['pnl_pct']:.2f}% |")
    else:
        report.append("現在保有している銘柄はありません。")
        
    report.append("\n## 📈 本日のシグナルとアクション\n")
    
    buys = []
    sells = []
    holds = []
    
    for symbol, data in symbols_data.items():
        action = data['action']
        name = config.SYMBOL_NAMES.get(symbol, symbol)
        row = f"| **{name} ({symbol})** | {data['signal']} | {action} | {data['reason']} |"
        
        if "買" in action or "buy" in action.lower():
            buys.append(row)
        elif "決済" in action or "売" in action or "sell" in action.lower():
            sells.append(row)
        else:
            holds.append(row)
            
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

    # オープン中の市場の銘柄だけを抽出
    active_symbols = [sym for sym in config.TARGET_SYMBOLS if is_market_open_for_symbol(sym)]
    
    if active_symbols:
        print(f"📊 {len(active_symbols)}銘柄の過去データをバッチ取得します...")
        historical_data = fetch_daily_data_batch(active_symbols)
    else:
        historical_data = {}

    # キルスイッチ判定
    status = executor.get_portfolio_status()
    unrealized_pl = status.get('unrealized_pl', 0.0)
    current_equity = status.get('equity', equity)
    drawdown = unrealized_pl / current_equity if current_equity > 0 else 0.0
    kill_switch_active = False
    
    if drawdown <= config.KILL_SWITCH_DRAWDOWN:
        kill_switch_active = True
        slack_blocks.append(f"🚨 **【キルスイッチ作動】**\nポートフォリオの含み損({drawdown*100:.2f}%)が許容値({config.KILL_SWITCH_DRAWDOWN*100:.0f}%)を超過しました。\nシステムの安全のため、本日の新規買い注文は全てブロックされます。")

    for symbol in active_symbols:
        df = historical_data.get(symbol)
        if df is None:
            continue
            
        pos = positions.get(symbol)
        signal_type, reason, is_buy = evaluate_signals(df, config.VOLUME_SPIKE_MULTIPLIER, pos)
        action_text = "なし"
        
        # キルスイッチブロック
        if is_buy and kill_switch_active:
            action_text = "【発注ブロック】キルスイッチ作動中"
            reason += " (※安全のため購入見送り)"
            is_buy = False

        # プレマーケット暴落フィルター
        if is_buy:
            pre_market = fetch_pre_market_price(symbol)
            if pre_market and pre_market.get("change_pct", 0) <= config.PRE_MARKET_DROP_LIMIT:
                action_text = f"【発注ブロック】プレマーケット暴落({pre_market['change_pct']:.1f}%)"
                reason += f" (※暴落回避: {pre_market['change_pct']:.1f}%)"
                is_buy = False
        
        if is_buy:
            if pos and pos['qty'] > 0:
                action_text = "既に保有中のため追加購入は見送り"
            else:
                atr = calculate_atr(df['High'], df['Low'], df['Close'])
                current_price = df['Close'].iloc[-1]
                is_us_stock = not symbol.endswith('.T')
                cash_power = executor.get_available_power(is_us_stock)
                
                # ペーパートレードの場合は現金残高の制約を無視
                if executor.is_paper:
                    cash_power = equity
                
                shares = calculate_dynamic_position_size(
                    equity=equity, 
                    current_price=current_price, 
                    atr=atr, 
                    is_us_stock=is_us_stock,
                    usdjpy_rate=usdjpy_rate,
                    risk_per_trade=config.MAX_PORTFOLIO_RISK_PCT,
                    available_cash=cash_power
                )
                
                if shares <= 0:
                    req_funds = current_price * 100 if not is_us_stock else current_price
                    action_text = "【見送り】資金不足（リスク超過）"
                    
                    req_funds_jpy = req_funds * usdjpy_rate if is_us_stock else req_funds
                    curr_price_jpy = current_price * usdjpy_rate if is_us_stock else current_price
                    
                    msg = messages.INSUFFICIENT_FUNDS_TEMPLATE.format(
                        symbol=symbol,
                        name=config.SYMBOL_NAMES.get(symbol, symbol),
                        min_shares=100 if not is_us_stock else 1,
                        required_funds=f"¥{req_funds_jpy:,.0f}",
                        current_price=f"¥{curr_price_jpy:,.0f}"
                    )
                    slack_blocks.append(msg)
                else:
                    # Moomoo経由で現物買い（成行）
                    executor.submit_order(symbol, shares, 'buy')
                    action_text = f"【自動発注】{shares}株を購入"
                    
                    curr_price_jpy = current_price * usdjpy_rate if is_us_stock else current_price
                    msg = messages.get_trade_execution_msg(symbol, messages.TERM_BUY, shares, curr_price_jpy)
                    slack_blocks.append(f"{msg}\n> 理由: {signal_type}")
                
        elif signal_type in [config.SignalName.SHORT_TERM_OVERHEAT, config.SignalName.TREND_BREAKDOWN, config.SignalName.ATR_STOP_LOSS]:
            if pos and pos['qty'] > 0:
                executor.close_position(symbol)
                action_text = "【自動決済】保有株をすべて売却"
                
                is_us_stock = not symbol.endswith('.T')
                curr_price_jpy = pos['current_price'] * usdjpy_rate if is_us_stock else pos['current_price']
                msg = messages.get_trade_execution_msg(symbol, messages.TERM_SELL, pos['qty'], curr_price_jpy)
                slack_blocks.append(f"{msg}\n> 理由: {signal_type}")
                
        symbols_data[symbol] = {
            "signal": signal_type,
            "reason": reason,
            "action": action_text
        }

        # --- データベースへの記録 (Signal) ---
        formatted_name = f"{config.SYMBOL_NAMES.get(symbol, symbol)} ({symbol})"
        with get_session() as db:
            sig = SignalHistory(
                symbol=formatted_name,
                signal_type=signal_type,
                reason=reason,
                action_taken=action_text
            )
            db.add(sig)
            db.commit()
        
    generate_markdown_report(symbols_data, equity, positions)
    
    if len(slack_blocks) > 1:
        send_slack_notification("\n\n".join(slack_blocks))

def run_summary_mode(executor: MoomooExecutor, equity: float):
    """【ジョブ2】市場クローズ後のサマリー報告モード"""
    usdjpy_rate = fetch_usdjpy_rate()
    positions = executor.get_positions()
    
    status = executor.get_portfolio_status()
    equity = status.get('equity', 0.0)
    unrealized_pl = status.get('unrealized_pl', 0.0)
    
    # --- データベースへの記録 (Portfolio) ---
    with get_session() as db:
        port = PortfolioHistory(
            total_equity=equity,
            unrealized_pnl=unrealized_pl,
            is_paper=executor.is_paper
        )
        db.add(port)
        db.commit()
    
    # サマリーヘッダー
    slack_msg = [messages.get_daily_summary_header(equity, unrealized_pl)]
    
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--trade", action="store_true", help="取引判定モードで実行")
    parser.add_argument("--summary", action="store_true", help="サマリーモードで実行")
    parser.add_argument("--paper", action="store_true", help="ペーパートレードモード（実際の発注は行わない）")
    args = parser.parse_args()

    # DBの初期化
    init_db()

    if not args.trade and not args.summary:
        print("Please specify --trade or --summary flag.")
        return

    try:
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
