import schedule
import subprocess
import logging
import sys
import os
import time

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | [daemon] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_task(command_args: list):
    """
    指定されたコマンドを実行し、完了まで待機します。
    """
    cmd_str = " ".join(command_args)
    logging.info(f"▶️ タスク開始: {cmd_str}")
    try:
        # サブプロセスとして main_bot.py を呼び出す（分離して実行）
        result = subprocess.run(
            ["python", "main_bot.py"] + command_args[1:], 
            check=True, 
            capture_output=True, 
            text=True
        )
        logging.info(f"✅ タスク完了: {cmd_str}\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ タスク失敗: {cmd_str}\nエラー出力:\n{e.stderr}")

def schedule_jobs():
    logging.info("📅 スケジューラの初期化を開始します...")
    
    # 環境変数からペーパーモードかどうかを取得（デフォルトはTrueで安全に倒す）
    is_paper = os.getenv("PAPER_MODE", "True").lower() in ("true", "1", "yes")
    
    trade_cmd = ["main_bot.py", "--trade"]
    if is_paper:
        trade_cmd.append("--paper")
        logging.info("🚨 [安全装置] ペーパートレードモード (--paper) で起動します。実際の発注は行われません。")
    else:
        logging.warning("⚠️ [警告] ライブトレードモードで起動します。実際の資金が動きます！")

    summary_cmd = ["main_bot.py", "--summary"]
    if is_paper:
        summary_cmd.append("--paper")

    # 1. 毎朝 04:45 に「米国株の取引判定」を実行
    schedule.every().monday.at("04:45").do(run_task, trade_cmd)
    schedule.every().tuesday.at("04:45").do(run_task, trade_cmd)
    schedule.every().wednesday.at("04:45").do(run_task, trade_cmd)
    schedule.every().thursday.at("04:45").do(run_task, trade_cmd)
    schedule.every().friday.at("04:45").do(run_task, trade_cmd)
    
    # 2. 毎朝 06:00 に「米国市場終了後のサマリー通知」を実行
    schedule.every().monday.at("06:00").do(run_task, summary_cmd)
    schedule.every().tuesday.at("06:00").do(run_task, summary_cmd)
    schedule.every().wednesday.at("06:00").do(run_task, summary_cmd)
    schedule.every().thursday.at("06:00").do(run_task, summary_cmd)
    schedule.every().friday.at("06:00").do(run_task, summary_cmd)

    # 3. 毎昼 14:45 に「日本株の取引判定」を実行
    schedule.every().monday.at("14:45").do(run_task, trade_cmd)
    schedule.every().tuesday.at("14:45").do(run_task, trade_cmd)
    schedule.every().wednesday.at("14:45").do(run_task, trade_cmd)
    schedule.every().thursday.at("14:45").do(run_task, trade_cmd)
    schedule.every().friday.at("14:45").do(run_task, trade_cmd)

    # 4. 毎昼 15:30 に「日本市場終了後のサマリー通知」を実行
    schedule.every().monday.at("15:30").do(run_task, summary_cmd)
    schedule.every().tuesday.at("15:30").do(run_task, summary_cmd)
    schedule.every().wednesday.at("15:30").do(run_task, summary_cmd)
    schedule.every().thursday.at("15:30").do(run_task, summary_cmd)
    schedule.every().friday.at("15:30").do(run_task, summary_cmd)
    
    # 起動直後に正常動作確認のため、一度だけサマリーを実行
    logging.info("🔧 デーモン起動テスト: サマリーを生成します")
    run_task(summary_cmd)
    
    logging.info("🚀 スケジューラ起動完了。稼働を開始します。")

if __name__ == "__main__":
    schedule_jobs()
    
    while True:
        # スケジューラに登録されたタスクの時間になれば実行
        schedule.run_pending()
        # CPUリソースを消費しないように10秒スリープ
        time.sleep(10)
