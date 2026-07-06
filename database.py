import sqlite3
import datetime
from pathlib import Path
import config

def get_db_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # シグナル履歴テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            reason TEXT
        )
    ''')
    
    # 注文履歴テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            notional REAL,
            order_type TEXT NOT NULL,
            status TEXT NOT NULL,
            alpaca_order_id TEXT
        )
    ''')
    
    # ポートフォリオ・スナップショットテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_equity REAL NOT NULL,
            cash REAL NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def log_signal(symbol: str, signal_type: str, reason: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO signals (timestamp, symbol, signal_type, reason) VALUES (?, ?, ?, ?)",
        (datetime.datetime.now(datetime.timezone.utc).isoformat(), symbol, signal_type, reason)
    )
    conn.commit()
    conn.close()

def log_order(symbol: str, side: str, qty: float, notional: float, order_type: str, status: str, alpaca_order_id: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (timestamp, symbol, side, qty, notional, order_type, status, alpaca_order_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.datetime.now(datetime.timezone.utc).isoformat(), symbol, side, qty, notional, order_type, status, alpaca_order_id)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # テスト用
    init_db()
    print("Database initialized.")
