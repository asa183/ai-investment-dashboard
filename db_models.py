import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

import config

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{config.DB_PATH}")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TradeHistory(Base):
    """実際の約定履歴を保存するテーブル"""
    __tablename__ = "trade_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # 'buy' or 'sell'
    qty = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_paper = Column(Boolean, default=False)

class SignalHistory(Base):
    """毎日のAIシグナル（買い・売り・様子見）の履歴"""
    __tablename__ = "signal_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal_type = Column(String)
    reason = Column(String)
    action_taken = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PortfolioHistory(Base):
    """毎日のポートフォリオ総資産の推移"""
    __tablename__ = "portfolio_history"
    
    id = Column(Integer, primary_key=True, index=True)
    total_equity = Column(Float)
    unrealized_pnl = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_paper = Column(Boolean, default=False)

# データベースの初期化（テーブルが存在しない場合は作成）
def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
