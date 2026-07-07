import os
from pathlib import Path

# --- プロジェクトのベースディレクトリ ---
BASE_DIR = Path(__file__).resolve().parent

from dotenv import load_dotenv
load_dotenv()

# --- データベース設定 ---
DB_PATH = BASE_DIR / "trading_history.db"

# --- Moomoo (FutuOpenD) 設定 ---
FUTU_HOST = os.getenv("FUTU_HOST", "127.0.0.1")
FUTU_PORT = int(os.getenv("FUTU_PORT", 11111))

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# --- リスク管理・ポートフォリオ設定 ---
MAX_PORTFOLIO_RISK_PCT = 0.02  # 1回のトレードで許容するリスク (総資産の2%)
KILL_SWITCH_DRAWDOWN = -0.05   # ポートフォリオが5%減少したら全システム停止

# ペーパートレード時の基準となる仮想総資産（円）
PAPER_TRADE_BASE_EQUITY = 5000000.0

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
    "7203.T", # トヨタ自動車 (JP)
    "9983.T", # ファーストリテイリング (JP - 値がさ株の資金不足スキップテスト用)
    "BTC-USD" # ビットコイン
]
