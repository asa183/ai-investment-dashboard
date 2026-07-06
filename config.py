import os
from pathlib import Path

# --- プロジェクトのベースディレクトリ ---
BASE_DIR = Path(__file__).resolve().parent

# --- データベース設定 ---
DB_PATH = BASE_DIR / "trading_history.db"

# --- APIキー設定 (環境変数または直接入力) ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "PKBHSMNNEVDBZEQMZJRN27RZGD")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "CXVHjAdQW1s5aUUma6bow9Jq8FkBvwizeB21DHDyjej3")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # デモ口座用URL

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/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")

# --- リスク管理・ポートフォリオ設定 ---
MAX_PORTFOLIO_RISK_PCT = 0.02  # 1回のトレードで許容するリスク (総資産の2%)
KILL_SWITCH_DRAWDOWN = -0.05   # ポートフォリオが5%減少したら全システム停止

# --- 執行アルゴリズム設定 ---
ATR_TRAILING_MULTIPLIER = 2.0  # トレイリングストップ幅 (ATRの何倍の幅を持たせるか)
LIMIT_SLIPPAGE_BUFFER = 1.005  # 指値注文のバッファ (現在価格の+0.5%を上限とする)
PRE_MARKET_DROP_LIMIT = -3.0   # プレマーケットで前日比3%以上下落していたら発注をキャンセル

# --- AIシグナル判定の閾値 ---
VOLUME_SPIKE_MULTIPLIER = 1.5  # 出来高が過去平均の1.5倍以上で「急増」と判定

# --- 監視対象銘柄リスト ---
TARGET_SYMBOLS = [
    "MSFT",  # マイクロソフト
    "PLTR",  # パランティア
    "TSLA",  # テスラ
    "NVDA",  # エヌビディア (NEW!)
    "AAPL",  # アップル (NEW!)
    "TQQQ",  # ナスダック3倍ブル
    "SOXL",  # 半導体3倍ブル
    "VHT",   # ヘルスケアETF
    "BTC-USD" # ビットコイン
]
