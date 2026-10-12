import time
from market_data import get_stock_metrics
from financial_agent import analyze_market
from portfolio_manager import execute_trade, load_portfolio
from egx_assets import EGX_ASSETS

def run_trading_cycle():
    print("\n" + "="*50)
    print("🚀 بدء دورة فحص السوق ومسح أسهم وصناديق البورصة المصرية...")
    print("="*50)

    portfolio = load_portfolio()
    cash = portfolio.get("cash", 0.0)
    holdings = portfolio.get("holdings", {})

    print(f"💰 السيولة النقدية المتاحة: {cash:,.2f} ج | المراكز المفتوحة: {len(holdings)}")

    # 1. مسح السوق وتجميع الإشارات الفنية الأولية
    candidates = []
    
    for name, ticker in EGX_ASSETS.items():
        try:
            metrics = get_stock_metrics(ticker)
            if "error" in metrics:
                continue

            rsi = metrics.get("rsi", 50.0)
            trend = metrics.get("trend", "NEUTRAL")
            price = metrics.get("current_price", 0.0)

            # ترشيح الأسهم في مناطق شراء محتملة (تشبع بيعي أو اتجاه صاعد)
            # أو الأسهم المملوكة حالياً لفحص إمكانية جني الأرباح / وقف الخسارة
            is_owned = ticker in holdings
            is_oversold = rsi < 42
            is_overbought = rsi > 68
            
            if is_owned or is_oversold or (trend == "BULLISH" and rsi < 55):
                candidates.append({
                    "name": name,
                    "ticker": ticker,
                    "metrics": metrics,
                    "is_owned": is_owned
                })
        except Exception as e:
            print(f"تخطي {ticker} بسبب خطأ في البيانات: {e}")
            continue

    print(f"🔍 تم ترشيح {len(candidates)} أصل/سهم لإخضاعها لتحليل الذكاء الاصطناعي المزدوج.")

    # 2. فحص المرشحين عبر DeepSeek-R1 و Llama-3.3-70B
    for item in candidates[:6]:  # فحص أبرز 6 فرص في كل دورة لتفادي الـ Rate Limits
        ticker = item["ticker"]
        name = item["name"]
        metrics = item["metrics"]
        price = metrics["current_price"]

        print(f"\n🧠 جاري استشارة الذكاء الاصطناعي لسهم: {name} ({ticker}) - السعر: {price:.2f} ج...")

        try:
            decision_data = analyze_market(ticker, metrics, holdings)
            decision = decision_data.get("decision", "HOLD")
            reason = decision_data.get("reason", "لا توجد أسباب كافية للتنفيذ")

            print(f"📋 القرار النهائي: [{decision}] | المبرر: {reason}")

            # 3. تنفيذ الأوامر وفق إدارة المخاطر
            if decision == "BUY" and cash > 2000.0:
                # تخصيص سيولة منضبطة (بين 5,000 إلى 15,000 ج لكل مركز)
                allocated = min(max(cash * 0.15, 3000.0), 15000.0)
                shares = int(allocated // price)
                if shares > 0:
                    success, msg = execute_trade(ticker, "BUY", price, shares=shares, reason=reason)
                    print(f"✅ {msg}" if success else f"⚠️ فشل الشراء: {msg}")

            elif decision == "SELL" and item["is_owned"]:
                success, msg = execute_trade(ticker, "SELL", price, reason=reason)
                print(f"🔻 {msg}" if success else f"⚠️ فشل البيع: {msg}")

        except Exception as err:
            print(f"❌ خطأ أثناء تحليل {ticker}: {err}")

        # انتظار ثانيتين بين كل استدعاء لتجنب حظر مفتاح الـ API
        time.sleep(2)

    print("\n🏁 اكتملت دورة الفحص بنجاح.")

def start_bot(interval_seconds=120):
    """تشغيل المحرك في حلقة تكرارية مستمرة"""
    while True:
        try:
            run_trading_cycle()
        except Exception as e:
            print(f"حدث خطأ غير متوقع في محرك التداول: {e}")
        print(f"\n⏳ استراحة لمدة {interval_seconds} ثانية حتى الدورة القادمة...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    start_bot(interval_seconds=180)
