import json
import os
from datetime import datetime

PORTFOLIO_FILE = "portfolio.json"

def init_portfolio(initial_cash=100000.0):
    if not os.path.exists(PORTFOLIO_FILE):
        data = {
            "cash": initial_cash,
            "holdings": {},
            "trade_history": []
        }
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return data
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_portfolio():
    return init_portfolio()

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def execute_trade(symbol, action, price, shares=None, reason="Manual Execution"):
    port = load_portfolio()
    cash = float(port.get("cash", 0.0))
    holdings = port.get("holdings", {})
    history = port.get("trade_history", [])

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "BUY":
        # في الشراء إذا لم تحدد الكمية يدخل بـ 15% من الكاش أو 15,000 ج كحد أقصى
        if shares is None:
            allocated = min(cash * 0.20, 20000.0)
            if allocated < price:
                return False, "السيولة النقدية غير كافية لفتح المركز."
            shares = int(allocated // price)

        if shares <= 0:
            return False, "الكمية يجب أن تكون أكبر من صفر."

        total_cost = shares * price
        if total_cost > cash:
            return False, "الرصيد المتاح لا يكفي لتغطية إجمالي الصفقة."

        cash -= total_cost
        curr_shares = holdings.get(symbol, {}).get("shares", 0) if isinstance(holdings.get(symbol), dict) else holdings.get(symbol, 0)
        curr_avg = holdings.get(symbol, {}).get("avg_price", price) if isinstance(holdings.get(symbol), dict) else price
        
        new_shares = curr_shares + shares
        new_avg = ((curr_shares * curr_avg) + total_cost) / new_shares if new_shares > 0 else price

        holdings[symbol] = {
            "shares": new_shares,
            "avg_price": round(new_avg, 2)
        }

        history.append({
            "date": time_now,
            "symbol": symbol,
            "type": "BUY",
            "shares": shares,
            "price": round(price, 2),
            "total_value": round(total_cost, 2),
            "reason": reason
        })

    elif action == "SELL":
        if symbol not in holdings:
            return False, f"لا تملك أي أسهم في {symbol} لبيعها."

        curr_shares = holdings[symbol].get("shares", 0) if isinstance(holdings[symbol], dict) else holdings[symbol]
        
        if shares is None or shares > curr_shares:
            shares = curr_shares

        if shares <= 0:
            return False, "لا توجد أسهم متاحة للبيع."

        total_gain = shares * price
        cash += total_gain

        remaining = curr_shares - shares
        if remaining > 0:
            avg_p = holdings[symbol].get("avg_price", price) if isinstance(holdings[symbol], dict) else price
            holdings[symbol] = {"shares": remaining, "avg_price": avg_p}
        else:
            del holdings[symbol]

        history.append({
            "date": time_now,
            "symbol": symbol,
            "type": "SELL",
            "shares": shares,
            "price": round(price, 2),
            "total_value": round(total_gain, 2),
            "reason": reason
        })

    port["cash"] = round(cash, 2)
    port["holdings"] = holdings
    port["trade_history"] = history
    save_portfolio(port)
    return True, f"تم تنفيذ عملية {action} بنجاح ({shares} سهم)."

def panic_liquidate(market_prices_dict):
    """تسييل كافة الأسهم المملوكة فوراً بناءً على آخر أسعار مسجلة"""
    port = load_portfolio()
    holdings = list(port.get("holdings", {}).keys())
    if not holdings:
        return False, "المحفظة لا تحتوي على أي مراكز مفتوحة لتسييلها."

    for sym in holdings:
        price = market_prices_dict.get(sym, 1.0)
        execute_trade(sym, "SELL", price, reason="PANIC SELL: تسييل اضطراري شامل")
        
    return True, "تم تسييل كافة المراكز المفتوحة وتحويل المحفظة إلى كاش بالكامل."
