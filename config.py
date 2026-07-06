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
TRAILING_STOP_PERCENT = 0.05   # トレイリングストップ (最高値から5%下落で利確/損切り)

# --- AIシグナル判定の閾値 ---
VOLUME_SPIKE_MULTIPLIER = 1.5  # 出来高が過去平均の1.5倍以上で「急増」と判定

# --- 監視対象銘柄リスト ---
TARGET_SYMBOLS = [
    "MSFT",
    "PLTR",
    "TSLA",
    "TQQQ",
    "SOXL",
    "VHT",
    "BTC-USD"
]
