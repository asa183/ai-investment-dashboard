# execution.py
import config
from moomoo import OpenSecTradeContext, TrdMarket, TrdSide, OrderType, TrdEnv, RET_OK
from db_models import get_session, TradeHistory

class MoomooExecutor:
    """
    Moomoo証券 (Futu OpenAPI) を用いた取引実行クラス。
    後から改修しやすいよう、必要最小限の3つの関数のみを実装しています。
    """
    def __init__(self, is_paper=False):
        self.env = TrdEnv.SIMULATE if is_paper else TrdEnv.REAL
        # 取引コンテキストの初期化 (日米両市場向け)
        self.us_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=config.FUTU_HOST, port=config.FUTU_PORT)
        self.jp_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.JP, host=config.FUTU_HOST, port=config.FUTU_PORT)

    def _is_jp(self, symbol: str) -> bool:
        return symbol.endswith('.T')

    def _to_futu_symbol(self, symbol: str) -> str:
        if self._is_jp(symbol):
            return f"JP.{symbol.replace('.T', '')}"
        return f"US.{symbol}"

    def _from_futu_symbol(self, futu_symbol: str) -> str:
        if futu_symbol.startswith('JP.'):
            return f"{futu_symbol.replace('JP.', '')}.T"
        elif futu_symbol.startswith('US.'):
            return futu_symbol.replace('US.', '')
        return futu_symbol

    def get_positions(self) -> dict:
        """
        現在の保有ポジションを取得し、共通の辞書形式で返却します。
        Returns:
            { "AAPL": {"qty": 10, ...}, "7203.T": {"qty": 100, ...} }
        """
        positions = {}
        for ctx in [self.us_ctx, self.jp_ctx]:
            ret, data = ctx.position_list_query(trd_env=self.env)
            if ret == RET_OK and not data.empty:
                for _, row in data.iterrows():
                    symbol = self._from_futu_symbol(row['code'])
                    positions[symbol] = {
                        'qty': float(row['qty']),
                        'entry_price': float(row['cost_price']),
                        'current_price': float(row['nominal_price']),
                        'unrealized_pnl': float(row['pl_val']),
                        'pnl_pct': float(row['pl_ratio'])
                    }
        return positions

    def submit_order(self, symbol: str, qty: float, side: str):
        """
        現物（成行）注文を送信します。
        side: 'buy' または 'sell'
        """
        futu_symbol = self._to_futu_symbol(symbol)
        trd_side = TrdSide.BUY if side.lower() == 'buy' else TrdSide.SELL
        ctx = self.jp_ctx if self._is_jp(symbol) else self.us_ctx
        
        # ※実際の本番取引では ctx.unlock_trade("パスワードのMD5") が必要な場合があります。
        
        ret, data = ctx.place_order(
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
            
            # --- DBへ取引履歴を記録 ---
            with get_session() as db:
                trade = TradeHistory(
                    symbol=symbol,
                    side=side.lower(),
                    qty=qty,
                    price=0.0, # 成行のため0.0
                    is_paper=(self.env == TrdEnv.SIMULATE)
                )
                db.add(trade)
                db.commit()
                
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
        # 口座全体の資産はどちらのコンテキストから呼んでも同じ総合口座の情報を返すと想定
        ret, data = self.us_ctx.accinfo_query(trd_env=self.env)
        
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
        if hasattr(self, 'us_ctx'):
            self.us_ctx.close()
        if hasattr(self, 'jp_ctx'):
            self.jp_ctx.close()
