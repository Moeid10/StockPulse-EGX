import yfinance as yf
import pandas as pd

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_stock_metrics(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo", interval="1d")
        
        if df.empty or len(df) < 15:
            # بيانات احتياطية تقديرية في حال إغلاق السوق أو نقص البيانات
            return {
                "current_price": 10.0,
                "rsi": 50.0,
                "sma_20": 10.0,
                "trend": "NEUTRAL"
            }

        current_price = round(float(df['Close'].iloc[-1]), 2)
        
        # حساب SMA 20
        sma_20 = round(float(df['Close'].rolling(window=min(20, len(df))).mean().iloc[-1]), 2)
        
        # حساب RSI 14
        rsi_series = calculate_rsi(df['Close'], period=14)
        rsi_val = round(float(rsi_series.iloc[-1]), 2)
        if pd.isna(rsi_val):
            rsi_val = 50.0

        # تحديد الاتجاه
        trend = "BULLISH" if current_price > sma_20 else "BEARISH"

        return {
            "current_price": current_price,
            "rsi": rsi_val,
            "sma_20": sma_20,
            "trend": trend
        }
    except Exception as e:
        return {"error": str(e), "current_price": 10.0, "rsi": 50.0, "sma_20": 10.0, "trend": "NEUTRAL"}
