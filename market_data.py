# market_data.py
import yfinance as yf
import pandas as pd
import pandas_ta as ta

def get_stock_metrics(ticker_symbol: str) -> dict:
    """
    جلب بيانات سهم في البورصة المصرية وحساب المؤشرات الفنية.
    مثال للرموز: 'MASR.CA', 'COMI.CA', 'ISPH.CA'
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="6mo")
        
        if df.empty or len(df) < 50:
            return {"error": "بيانات غير كافية"}

        # حساب المؤشرات الفنية
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_50'] = ta.sma(df['Close'], length=50)

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "symbol": ticker_symbol,
            "current_price": round(float(latest['Close']), 2),
            "prev_price": round(float(prev['Close']), 2),
            "rsi": round(float(latest['RSI']), 2),
            "sma_20": round(float(latest['SMA_20']), 2),
            "sma_50": round(float(latest['SMA_50']), 2),
            "volume": int(latest['Volume']),
            "trend": "Bullish" if latest['Close'] > latest['SMA_20'] else "Bearish"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(get_stock_metrics("MASR.CA"))