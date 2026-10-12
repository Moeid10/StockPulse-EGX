import json
import os
from datetime import datetime

PORTFOLIO_FILE = "portfolio.json"
INITIAL_CASH = 100000.0  # رأس المال المبدئي: 100 ألف جنيه
MAX_ALLOCATION_PER_TRADE = 0.20  # حد أقصى 20% من السيولة في العملية الواحدة

def init_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        data = {
            "cash": INITIAL_CASH,
            "holdings": {},  # {ticker: {"shares": n, "avg_price": x, "buy_date": "..."}}
            "trade_history": []
        }
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def execute_trade(symbol, action, price, reason="AI Decision"):
    init_portfolio()
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        port = json.load(f)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "BUY":
        # تخصيص 20% من الكاش المتاح للشراء
        allocated_cash = port["cash"] * MAX_ALLOCATION_PER_TRADE
        if allocated_cash < 1000 or port["cash"] < price:
            return False, "السيولة غير كافية لإتمام الصفقة"

        shares_to_buy = int(allocated_cash // price)
        if shares_to_buy <= 0:
            return False, "سعر السهم أعلى من الحصة المخصصة"

        total_cost = shares_to_buy * price
        port["cash"] -= total_cost

        if symbol in port["holdings"]:
            curr = port["holdings"][symbol]
            new_shares = curr["shares"] + shares_to_buy
            new_avg = ((curr["shares"] * curr["avg_price"]) + total_cost) / new_shares
            port["holdings"][symbol]["shares"] = new_shares
            port["holdings"][symbol]["avg_price"] = round(new_avg, 2)
        else:
            port["holdings"][symbol] = {
                "shares": shares_to_buy,
                "avg_price": round(price, 2),
                "buy_date": now_str
            }

        trade_record = {
            "date": now_str,
            "symbol": symbol,
            "type": "BUY",
            "shares": shares_to_buy,
            "price": round(price, 2),
            "total_value": round(total_cost, 2),
            "reason": reason
        }
        port["trade_history"].append(trade_record)

    elif action == "SELL":
        if symbol not in port["holdings"] or port["holdings"][symbol]["shares"] <= 0:
            return False, "لا توجد أسهم مملوكة لبيعها"

        shares_to_sell = port["holdings"][symbol]["shares"]
        avg_price = port["holdings"][symbol]["avg_price"]
        total_income = shares_to_sell * price
        pnl = total_income - (shares_to_sell * avg_price)
        pnl_pct = (pnl / (shares_to_sell * avg_price)) * 100

        port["cash"] += total_income
        del port["holdings"][symbol]

        trade_record = {
            "date": now_str,
            "symbol": symbol,
            "type": "SELL",
            "shares": shares_to_sell,
            "price": round(price, 2),
            "total_value": round(total_income, 2),
            "profit_loss": round(pnl, 2),
            "profit_pct": f"{pnl_pct:.2f}%",
            "reason": reason
        }
        port["trade_history"].append(trade_record)

    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(port, f, indent=4, ensure_ascii=False)

    return True, f"تم تنفيذ عملية {action} بنجاح"