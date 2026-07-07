# execution.py
import config
from moomoo import OpenSecTradeContext, TrdMarket, TrdSide, OrderType, TrdEnv, RET_OK

class MoomooExecutor:
    """
    Moomoo証券 (Futu OpenAPI) を用いた取引実行クラス。
    後から改修しやすいよう、必要最小限の3つの関数のみを実装しています。
    """
    def __init__(self, is_paper=False):
        self.env = TrdEnv.SIMULATE if is_paper else TrdEnv.REAL
        # 取引コンテキストの初期化 (US市場向け)
        self.trd_ctx = OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US, 
            host=config.FUTU_HOST, 
            port=config.FUTU_PORT
        )

    def get_positions(self) -> dict:
        """
        現在の保有ポジションを取得し、共通の辞書形式で返却します。
        Returns:
            { "AAPL": {"qty": 10, "entry_price": 150.0, "current_price": 155.0, "unrealized_pnl": 50.0, "pnl_pct": 3.33} }
        """
        ret, data = self.trd_ctx.position_list_query(trd_env=self.env)
        positions = {}
        
        if ret == RET_OK:
            for _, row in data.iterrows():
                # "US.AAPL" などのコードから "AAPL" だけを抽出
                symbol = row['code'].split('.')[-1]
                positions[symbol] = {
                    'qty': float(row['qty']),
                    'entry_price': float(row['cost_price']),
                    'current_price': float(row['nominal_price']),
                    'unrealized_pnl': float(row['pl_val']),
                    'pnl_pct': float(row['pl_ratio'])
                }
        else:
            print(f"⚠️ ポジション取得エラー: {data}")
            
        return positions

    def submit_order(self, symbol: str, qty: float, side: str):
        """
        現物（成行）注文を送信します。
        side: 'buy' または 'sell'
        """
        futu_symbol = f"US.{symbol}"
        trd_side = TrdSide.BUY if side.lower() == 'buy' else TrdSide.SELL
        
        # ※実際の本番取引では self.trd_ctx.unlock_trade("パスワードのMD5") が必要な場合があります。
        
        ret, data = self.trd_ctx.place_order(
            price=0.0,  # 成行の場合は0
            qty=qty,
            code=futu_symbol,
            trd_side=trd_side,
            order_type=OrderType.MARKET,
            adjust_limit=0,
            trd_env=self.env
        )
        
        if ret == RET_OK:
            print(f"✅ 注文完了: {side.upper()} {qty} shares of {symbol}")
            return data
        else:
            print(f"⚠️ 注文エラー: {data}")
            return None

    def close_position(self, symbol: str):
        """
        指定した銘柄の保有ポジションをすべて成行で決済します。
        """
        positions = self.get_positions()
        if symbol in positions:
            qty = positions[symbol]['qty']
            if qty > 0:
                print(f"🧹 全決済を実行します: {symbol} ({qty}株)")
                return self.submit_order(symbol, qty, 'sell')
        return None

    def get_portfolio_status(self) -> dict:
        """口座全体の資産状況を取得します"""
        ret, data = self.trd_ctx.accinfo_query(trd_env=self.env)
        
        def safe_float(val):
            if val == 'N/A' or val is None:
                return 0.0
            try:
                return float(val)
            except ValueError:
                return 0.0

        if ret == RET_OK and not data.empty:
            row = data.iloc[0]
            return {
                "equity": safe_float(row.get('total_assets', 0.0)),
                "unrealized_pl": safe_float(row.get('unrealized_pl', 0.0))
            }
        return {"equity": 0.0, "unrealized_pl": 0.0}

    def __del__(self):
        """終了処理: APIゲートウェイとの接続を安全に閉じます"""
        if hasattr(self, 'trd_ctx'):
            self.trd_ctx.close()
