import time
from market_data import get_stock_metrics
from financial_agent import analyze_market
from egx_assets import EGX_ASSETS
from database import get_db, get_user_portfolio, execute_user_trade

STOP_LOSS_PCT = -0.03    # وقف خسارة عند هبوط 3%
TAKE_PROFIT_PCT = 0.06   # جني أرباح عند صعود 6%

def run_trading_cycle():
    print("\n" + "="*50)
    print("🚀 بدء دورة الفحص الشامل وإدارة المخاطر للبورصة المصرية...")
    print("="*50)

    # جلب جميع المستخدمين المسجلين في النظام
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [r["username"] for r in c.fetchall()]
    conn.close()

    # مسح السوق وتجميع الأسعار
    active_metrics = {}
    candidates = []

    for name, ticker in EGX_ASSETS.items():
        try:
            m = get_stock_metrics(ticker)
            if "error" in m:
                continue
            active_metrics[ticker] = m
            rsi = m.get("rsi", 50.0)
            trend = m.get("trend", "NEUTRAL")
            if rsi < 42 or (trend == "BULLISH" and rsi < 55):
                candidates.append((ticker, name, m))
        except Exception:
            continue

    print(f"📊 تم رصد {len(candidates)} سهم في نطاق إشارات شراء فنية محتملة.")

    # تطبيق استراتيجيات التداول وإدارة المخاطر على محفظة كل مستخدم بشكل معزول
    for username in users:
        port = get_user_portfolio(username)
        cash = port["cash"]
        holdings = port["holdings"]

        # 1. إدارة المخاطر التلقائية (Stop-Loss & Take-Profit) للأسهم الحالية
        for sym, h_info in list(holdings.items()):
            shares = h_info["shares"]
            avg_p = h_info["avg_price"]
            curr_p = active_metrics.get(sym, {}).get("current_price", avg_p)
            change = (curr_p - avg_p) / avg_p if avg_p > 0 else 0.0

            if change <= STOP_LOSS_PCT:
                execute_user_trade(username, sym, "SELL", curr_p, shares=shares, 
                                   reason=f"تفعيل وقف الخسارة التلقائي (خسارة {change*100:.1f}%)")
                print(f"🛑 [وقف خسارة - {username}] تم بيع {sym} لحماية رأس المال.")
            elif change >= TAKE_PROFIT_PCT:
                execute_user_trade(username, sym, "SELL", curr_p, shares=shares, 
                                   reason=f"تفعيل جني الأرباح التلقائي (ربح +{change*100:.1f}%)")
                print(f"🎯 [جني أرباح - {username}] تم بيع {sym} وتأمين الأرباح.")

        # 2. فحص أفضل الفرص بالذكاء الاصطناعي والشراء عند توفر السيولة
        if cash > 3000.0:
            for ticker, name, metrics in candidates[:3]:
                if ticker in holdings:
                    continue
                try:
                    decision_data = analyze_market(ticker, metrics, holdings)
                    if decision_data.get("decision") == "BUY":
                        price = metrics["current_price"]
                        allocated = min(max(cash * 0.15, 3000.0), 15000.0)
                        shares_to_buy = int(allocated // price)
                        if shares_to_buy > 0:
                            reason = decision_data.get("reason", "فرصة استثمارية واعدة")
                            execute_user_trade(username, ticker, "BUY", price, shares=shares_to_buy, reason=reason)
                            print(f"✅ [شراء - {username}] {ticker} | {reason}")
                            cash -= (shares_to_buy * price)
                except Exception as err:
                    print(f"خطأ في التحليل: {err}")
                time.sleep(1.5)

if __name__ == "__main__":
    run_trading_cycle()
