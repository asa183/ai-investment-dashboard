import requests
import config
from alpaca_trade_api.rest import REST, TimeFrame

def send_slack_notification(message: str, is_alert: bool = False):
    """Slackへ通知を送信する"""
    if config.SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL":
        print(f"[{'ALERT' if is_alert else 'INFO'}] Slack Webhook is not configured. Message: {message}")
        return
        
    alert_prefix = "🚨 *EMERGENCY ALERT* 🚨\n" if is_alert else ""
    payload = {"text": f"{alert_prefix}{message}"}
    try:
        requests.post(config.SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")

class AlpacaExecutor:
    def __init__(self):
        self.api = REST(
            key_id=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            base_url=config.ALPACA_BASE_URL
        )
        self.is_connected = False
        self._test_connection()

    def _test_connection(self):
        if config.ALPACA_API_KEY == "YOUR_ALPACA_API_KEY":
            print("Warning: Alpaca API keys are not set. Running in DRY-RUN mode.")
            return
        try:
            self.api.get_account()
            self.is_connected = True
        except Exception as e:
            print(f"Alpaca connection failed: {e}")

    def get_portfolio_status(self):
        """現在のポートフォリオ状態を取得"""
        if not self.is_connected:
            return {"equity": 10000.0, "cash": 10000.0} # Dry-run mock
        account = self.api.get_account()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash)
        }

    def check_kill_switch(self, current_equity: float, baseline_equity: float = 10000.0) -> bool:
        """ドローダウンを計算し、キルスイッチを発動するか判定"""
        drawdown = (current_equity - baseline_equity) / baseline_equity
        if drawdown <= config.KILL_SWITCH_DRAWDOWN:
            send_slack_notification(f"Kill Switch Activated! Drawdown is {drawdown*100:.1f}%", is_alert=True)
            return True
        return False

    def get_position(self, symbol: str):
        if not self.is_connected:
            return None
        try:
            return self.api.get_position(symbol)
        except:
            return None

    def execute_buy_trailing_stop(self, symbol: str, qty: int, limit_price: float):
        """指値注文を送信 (トレイリングストップは事後設定)"""
        if qty <= 0:
            return None
            
        if not self.is_connected:
            print(f"[DRY-RUN] BUY {qty} shares of {symbol} at LIMIT ${limit_price:.2f}.")
            return "dry_run_order_id"

        try:
            # 指値注文を送信 (約定後にAlpaca側でトレイリングストップを手動設定または後続ジョブで設定する想定)
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='limit',
                limit_price=round(limit_price, 2),
                time_in_force='gtc'
            )
            return order.id
        except Exception as e:
            alert_msg = (
                "🚨 *【システム警告】発注エラー* 🚨\n"
                f"銘柄 `{symbol}` の購入注文がAlpacaから拒否されました。\n"
                f"📝 *エラー詳細*: {e}\n"
                "💡 *よくある原因*: 資金不足（Insufficient buying power）、時間外で無効な注文設定、または暗号資産(BTC等)の非対応フォーマット。"
            )
            send_slack_notification(alert_msg)
            return None

    def execute_sell_all(self, symbol: str):
        """保有する全株を売却"""
        if not self.is_connected:
            print(f"[DRY-RUN] SELL ALL shares of {symbol}.")
            return "dry_run_sell_id"
            
        try:
            self.api.close_position(symbol)
            return "closed_all"
        except Exception as e:
            print(f"Failed to sell {symbol}: {e}")
            return None

    def attach_trailing_stop_if_needed(self, symbol: str, qty: int, trail_percent: float):
        """保有株に対して、まだトレイリングストップ注文がなければ発注する"""
        if not self.is_connected:
            print(f"[DRY-RUN] Attach Trailing Stop: {symbol} Qty: {qty} TrailPct: {trail_percent:.2f}%")
            return "dry_run_trail"

        try:
            # 現在のオープン注文を確認
            open_orders = self.api.list_orders(status='open', symbols=[symbol])
            has_trailing_stop = any(o.type == 'trailing_stop' for o in open_orders)
            
            if has_trailing_stop:
                print(f"[{symbol}] Trailing stop already exists. Skipping.")
                return None
                
            # トレイリングストップ売り注文を発注
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='trailing_stop',
                trail_percent=round(trail_percent, 2),
                time_in_force='gtc'
            )
            print(f"[{symbol}] Attached trailing stop: {trail_percent:.2f}%")
            return order.id
            
        except Exception as e:
            print(f"Failed to attach trailing stop for {symbol}: {e}")
            return None
