import sys
import json
from groq import Groq
from market_data import get_stock_metrics
from portfolio_manager import execute_trade, PORTFOLIO_FILE

sys.stdout.reconfigure(encoding='utf-8')

GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

def run_pipeline(ticker="MASR.CA", company_name="مدينة مصر للإسكان"):
    print("=" * 60)
    print(f"🚀 بدء تشغيل StockPulse EGX لسهم: {company_name} ({ticker})")
    print("=" * 60)

    # 1. سحب البيانات والمؤشرات
    metrics = get_stock_metrics(ticker)
    if "error" in metrics:
        print("❌ فشل في جلب البيانات:", metrics["error"])
        return

    price = metrics["current_price"]
    print(f"📈 السعر الحالي: {price} ج | RSI: {metrics['rsi']} | الاتجاه: {metrics['trend']}")

    # 2. استدعاء الأيچنت المالي
    print("\n🤖 جاري استشارة الأيچنت المالي واتخاذ القرار...")
    prompt = f"""
    أنت مدير استثمار ذكي في البورصة المصرية (EGX).
    سهم: {company_name} ({ticker})
    السعر: {price} جنيه
    مؤشر RSI: {metrics['rsi']}
    الاتجاه: {metrics['trend']}

    المطلوب منك:
    أول كلمة في إجابتك يجب أن تكون أحد هذه القرارات فقط بدون مقدمات: (BUY أو SELL أو HOLD).
    ثم في سطر جديد اكتب تبريراً فنياً موجزاً وسعر الهدف ووقف الخسارة.
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="qwen/qwen3.8-27b",
        temperature=0.1,
    )

    response_text = chat_completion.choices[0].message.content.strip()
    print("\n📝 تقرير الأيچنت المالي:")
    print("-" * 40)
    print(response_text)
    print("-" * 40)

    # 3. استخراج القرار وتنفيذه في المحفظة
    action = "HOLD"
    if "BUY" in response_text[:20].upper() or "شراء" in response_text[:20]:
        action = "BUY"
    elif "SELL" in response_text[:20].upper() or "بيع" in response_text[:20]:
        action = "SELL"

    print(f"\n⚙️ تنفيذ القرار المالي: [{action}] في المحفظة الافتراضية...")
    execute_trade(symbol=ticker, action=action, price=price)

    # عرض ملخص المحفظة بعد التنفيذ
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        port = json.load(f)
    print("\n💼 حالة المحفظة الحالية:")
    print(f"   - السيولة النقدية: {port['cash']} ج")
    print(f"   - الأسهم المملوكة: {port['holdings']}")
    print("=" * 60)

if __name__ == "__main__":
    run_pipeline("MASR.CA", "مدينة مصر للإسكان")