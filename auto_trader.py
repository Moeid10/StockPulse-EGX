import os
import re
import json
from groq import Groq
from market_data import get_stock_metrics
from egx_assets import EGX_ASSETS
from database import (
    get_all_usernames,
    get_user_portfolio,
    execute_user_trade
)

def extract_json_payload(text: str) -> dict:
    """استخراج كائن JSON بأمان وتجاوز أي وسوم تفكير داخل رد DeepSeek"""
    # إزالة محتوى وسم التفكير إن وُجد
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    match = re.search(r'\{.*?\}', cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)

def query_deepseek_ai(symbol: str, metrics: dict) -> tuple:
    """استشارة نموذج DeepSeek-R1 عبر منصة Groq للتحليل المالي المتعمق"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("⚠️ تحذير: لم يتم العثور على GROQ_API_KEY، الاعتماد على القواعد الفنية البديلة.")
        rsi = metrics.get("rsi", 50.0)
        if rsi < 35:
            return "BUY", "إشارة شراء فنية: مؤشر RSI في مناطق تشبع بيعي قوية."
        return "HOLD", "مؤشرات فنية محايدة."

    try:
        client = Groq(api_key=api_key)
        prompt = f"""
        أنت محلل كمي وخبير استثمار معتمد في البورصة المصرية (EGX).
        قم بتحليل أرقام السهم التالية:
        السهم: {symbol}
        السعر الحالي: {metrics.get('current_price', 0.0)} ج.م
        مؤشر القوة النسبية (RSI 14): {metrics.get('rsi', 50.0)}
        المتوسط المتحرك (SMA 20): {metrics.get('sma_20', 0.0)}
        التغير اليومي: {metrics.get('change_pct', 0.0)}%

        المطلوب:
        اتخذ قرارك الاستثماري (BUY للشراء فقط إذا كانت نسبة المخاطرة للعائد ممتازة، أو HOLD للانتظار).
        أخرج إجابتك بصيغة JSON فقط دون أي شروحات إضافية خارج الـ JSON:
        {{"decision": "BUY", "reason": "مبرر مالي موجز بالعربية لا يتعدى 10 كلمات"}}
        """

        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        raw_content = response.choices[0].message.content
        data = extract_json_payload(raw_content)
        
        decision = data.get("decision", "HOLD").upper()
        reason = data.get("reason", "تحليل DeepSeek المالي الكمي")
        return decision, reason

    except Exception as e:
        print(f"⚠️ خطأ أثناء استشارة DeepSeek لسهم {symbol}: {e}")
        # خيار أمان احتياطي لتفادي توقف الدورة
        rsi = metrics.get("rsi", 50.0)
        if rsi < 35:
            return "BUY", "إشارة فنية احتياطية: تشبع بيعي"
        return "HOLD", "انتظار تأكيد المؤشرات"

def run_auto_trader():
    users = get_all_usernames()
    if not users:
        print("لا يوجد مستخدمون مسجلون لتنفيذ التداول.")
        return

    print(f"🚀 بدء تشغيل محرك DeepSeek-R1 لعدد {len(users)} مستخدمين مسجلين...")

    for username in users:
        print(f"\n==========================================")
        print(f"👤 فحص محفظة المستخدم: {username}")
        portfolio = get_user_portfolio(username)
        cash = portfolio.get("cash", 0.0)
        holdings = portfolio.get("holdings", {})

        print(f"💵 السيولة المتاحة: {cash:,.2f} ج | المراكز المفتوحة: {len(holdings)}")

        # ---------------- 1. إدارة المخاطر الآلية للأسهم المملوكة ----------------
        for sym, pos in list(holdings.items()):
            shares = pos.get("shares", 0)
            avg_price = pos.get("avg_price", 0.0)
            if shares <= 0:
                continue

            metrics = get_stock_metrics(sym)
            cur_price = metrics.get("current_price", avg_price)
            if cur_price <= 0:
                continue

            pnl_pct = ((cur_price - avg_price) / avg_price) * 100
            print(f"📊 سهم {sym}: الكمية={shares} | الشراء={avg_price:.2f} | الحالي={cur_price:.2f} | العائد={pnl_pct:+.2f}%")

            # جني الأرباح عند +6%
            if pnl_pct >= 6.0:
                reason = f"🎯 جني أرباح آلي (+{pnl_pct:.2f}%) عند وصول الهدف"
                execute_user_trade(username, sym, "SELL", cur_price, shares, reason=reason)
                print(f"✅ [{username}] تم بيع {shares} سهم من {sym} لجني الأرباح.")

            # وقف الخسارة عند -3%
            elif pnl_pct <= -3.0:
                reason = f"🛑 وقف خسارة إجباري ({pnl_pct:.2f}%) لحماية رأس المال"
                execute_user_trade(username, sym, "SELL", cur_price, shares, reason=reason)
                print(f"⚠️ [{username}] تم بيع {shares} سهم من {sym} لوقف الخسارة.")

        # ---------------- 2. فحص فرص الشراء عبر DeepSeek-R1 ----------------
        if cash >= 5000:
            bought_this_cycle = False
            for label, ticker in EGX_ASSETS.items():
                if bought_this_cycle:
                    break

                if ticker in holdings and holdings[ticker].get("shares", 0) > 0:
                    continue

                metrics = get_stock_metrics(ticker)
                cur_price = metrics.get("current_price", 0.0)
                if cur_price <= 0:
                    continue

                decision, reason = query_deepseek_ai(ticker, metrics)

                if decision == "BUY":
                    trade_budget = min(cash * 0.20, 20000.0)
                    shares_to_buy = int(trade_budget // cur_price)

                    if shares_to_buy > 0:
                        suc, msg = execute_user_trade(
                            username, ticker, "BUY", cur_price, shares_to_buy, reason=f"DeepSeek: {reason}"
                        )
                        if suc:
                            print(f"🟢 [{username}] شراء ناجح: {shares_to_buy} سهم من {ticker} بسعر {cur_price:.2f} ج.")
                            cash -= (shares_to_buy * cur_price)
                            bought_this_cycle = True
                        else:
                            print(f"❌ تعذر الشراء لـ [{username}]: {msg}")
        else:
            print(f"ℹ️ السيولة غير كافية لفتح مراكز جديدة للمستخدم {username}.")

    print("\n🏁 اكتملت دورة التداول الآلي بنجاح.")

if __name__ == "__main__":
    run_auto_trader()
