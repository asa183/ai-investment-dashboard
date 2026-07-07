# messages.py
# Slack通知用のメッセージテンプレートとシステム用語を一元管理します。
# 後から文言を変えたくなった場合は、このファイルだけを修正してください。

# --- 用語定義 ---
TERM_BUY = "🟢 新規買"
TERM_SELL = "🔴 決済売"
TERM_TRAILING_STOP = "🛡️ トレイリングストップ決済"
TERM_ERROR = "⚠️ エラー"

# --- メッセージテンプレート ---

def get_trade_execution_msg(symbol: str, side_term: str, qty: float, price: float) -> str:
    """約定時の通知メッセージ"""
    return f"{side_term}: {symbol}\n数量: {qty}株\n約定単価: ${price:.2f}"

def get_daily_summary_header(total_assets: float, total_unrealized_pnl: float) -> str:
    """朝のサマリー通知のヘッダー"""
    return (
        "📈 *本日のポートフォリオ サマリー*\n"
        "------------------------------------\n"
        f"💰 概算総資産: ${total_assets:,.2f}\n"
        f"📊 ポートフォリオ全体の含み損益: ${total_unrealized_pnl:,.2f}\n"
        "------------------------------------\n"
        "*保有銘柄の内訳:*"
    )

def get_position_detail_msg(symbol: str, qty: float, entry_price: float, current_price: float, unrealized_pnl: float, pnl_pct: float) -> str:
    """各保有銘柄の詳細メッセージ"""
    icon = "🟩" if unrealized_pnl >= 0 else "🟥"
    return (
        f"{icon} *{symbol}*\n"
        f"   保有数: {qty}株 | 取得単価: ${entry_price:.2f} | 現在値: ${current_price:.2f}\n"
        f"   含み損益: ${unrealized_pnl:,.2f} ({pnl_pct:.2f}%)"
    )

def get_trailing_stop_update_msg(symbol: str, old_stop: float, new_stop: float) -> str:
    """防衛線（トレイリングストップ）切り上げ時の通知"""
    return f"🛡️ 防衛線アップデート: {symbol}\nストップ価格を ${old_stop:.2f} から ${new_stop:.2f} に引き上げました。"

def get_error_msg(context: str, error_details: str) -> str:
    """エラー発生時の通知"""
    return f"{TERM_ERROR} [{context}]\n詳細: {error_details}"
