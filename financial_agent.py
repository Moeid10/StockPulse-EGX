import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from groq import Groq
from market_data import get_stock_metrics

GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

def run_ai_advisor(ticker="MASR.CA", company_name="مدينة مصر للإسكان"):
    print(f"\n1. جلب بيانات سهم {company_name}...")
    metrics = get_stock_metrics(ticker)
    
    if "error" in metrics:
        print("خطأ في البيانات:", metrics["error"])
        return

    print("2. البيانات الفنية:")
    print(f"   السعر: {metrics['current_price']} ج | RSI: {metrics['rsi']} | الاتجاه: {metrics['trend']}")
    
    print("\n3. تحليل المؤشرات بواسطة الذكاء الاصطناعي...")

    prompt = f"""
    أنت مستشار مالي خبير في البورصة المصرية (EGX).
    حلل البيانات الفنية لسهم {company_name} ({ticker}):
    - السعر الحالي: {metrics['current_price']} جنيه
    - السعر السابق: {metrics['prev_price']} جنيه
    - RSI: {metrics['rsi']}
    - SMA 20: {metrics['sma_20']}
    - SMA 50: {metrics['sma_50']}
    - الاتجاه: {metrics['trend']}

    قدم تحليلك باللغة العربية متضمناً:
    1. القرار الاستثماري: (شراء / بيع / احتفاظ).
    2. السعر المستهدف وسعر وقف الخسارة.
    3. درجة المخاطرة.
    4. تبرير فني مختصر في نقطتين.
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="qwen/qwen3.8-27b",
        temperature=0.2,
    )

    print("\n" + "="*50)
    print(f"قرار الأيچنت المالي لسهم {company_name}:")
    print("="*50)
    print(chat_completion.choices[0].message.content)
    print("="*50)

if __name__ == "__main__":
    run_ai_advisor("MASR.CA", "مدينة مصر للإسكان")