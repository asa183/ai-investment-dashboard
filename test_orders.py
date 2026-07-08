import time
from execution import MoomooExecutor

def run_test():
    print("🚀 [TEST] MoomooExecutor ペーパートレードモードで起動します...")
    executor = MoomooExecutor(is_paper=True)
    
    symbol = "AAPL"  # テスト銘柄
    qty = 1          # 1株
    
    print(f"\n🟢 [TEST] {symbol} の【買い注文】を送信します...")
    executor.submit_order(symbol, qty, 'buy')
    
    print("\n⏳ 注文の約定を待つため、3秒待機します...")
    time.sleep(3)
    
    print("\n📊 [TEST] 現在のポジションを取得します...")
    positions = executor.get_positions()
    for sym, pos in positions.items():
        print(f" - {sym}: {pos['qty']}株保有 (取得単価: ${pos['entry_price']})")
        
    print(f"\n🔴 [TEST] {symbol} の【全決済（売り注文）】を送信します...")
    executor.close_position(symbol)
    
    print("\n⏳ 決済の完了を待つため、3秒待機します...")
    time.sleep(3)
    
    print("\n📊 [TEST] 最終的なポジションを確認します...")
    positions_final = executor.get_positions()
    if not positions_final or symbol not in positions_final or positions_final[symbol]['qty'] == 0:
        print(f"✅ {symbol} のポジションは正常に 0 になりました！")
    else:
        print(f"⚠️ {symbol} がまだ残っています: {positions_final[symbol]['qty']}株")

if __name__ == "__main__":
    run_test()
