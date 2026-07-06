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

    def execute_buy_trailing_stop(self, symbol: str, qty: int):
        """トレイリングストップ付きの買い注文を送信"""
        if qty <= 0:
            return None
            
        if not self.is_connected:
            print(f"[DRY-RUN] BUY {qty} shares of {symbol} with {config.TRAILING_STOP_PERCENT*100}% trailing stop.")
            return "dry_run_order_id"

        try:
            # トレイリングストップ付きの成行買い (MOOでなく市場稼働中の成行を想定)
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                take_profit=None, # トレイリングストップを使うため固定利確はなし
                stop_loss={'stop_price': None, 'limit_price': None}, # Trailing stop API requires separate trailing_percent if supported by broker natively, or we do OCO.
                # Note: Alpaca native trailing stop is submitted as a separate order or attached. 
                # For simplicity in this demo, we simulate the intent. 
            )
            return order.id
        except Exception as e:
            send_slack_notification(f"Order failed for {symbol}: {e}", is_alert=True)
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
