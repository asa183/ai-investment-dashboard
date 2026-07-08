import yfinance as yf
import json

def fetch_top_gainers(limit=3):
    try:
        # Get predefined day gainers query
        query = yf.PREDEFINED_SCREENER_QUERIES['day_gainers']['query']
        
        # Execute screen
        result = yf.screener.screen(query)
        
        if 'quotes' not in result:
            print("Error: Invalid response from yfinance screener.")
            return

        quotes = result['quotes']
        
        # Sort by percent change just to be safe
        quotes = sorted(quotes, key=lambda x: x.get('regularMarketChangePercent', 0), reverse=True)
        
        print(f"--- Top {limit} Market Gainers (Live Data) ---")
        
        for i, quote in enumerate(quotes[:limit]):
            symbol = quote.get('symbol', 'N/A')
            name = quote.get('longName', quote.get('shortName', 'N/A'))
            change_pct = quote.get('regularMarketChangePercent', 0)
            
            # Fetch sector/industry info
            try:
                info = yf.Ticker(symbol).info
                sector = info.get('sector', 'Unknown Sector')
                industry = info.get('industry', 'Unknown Industry')
            except Exception:
                sector = 'Unknown Sector'
                industry = 'Unknown Industry'
                
            print(f"{i+1}. Symbol: {symbol}")
            print(f"   Name: {name}")
            print(f"   Change: +{change_pct:.2f}%")
            print(f"   Sector: {sector} / Industry: {industry}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error fetching market movers: {e}")

if __name__ == "__main__":
    fetch_top_gainers()
