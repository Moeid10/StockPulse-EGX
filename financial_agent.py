import os
import json
from groq import Groq

# تهيئة عميل Groq عبر المفتاح المحفوظ
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def analyze_market(ticker, metrics, holdings):
    current_price = metrics.get("current_price", 0.0)
    rsi = metrics.get("rsi", 50.0)
    sma_20 = metrics.get("sma_20", 0.0)
    trend = metrics.get("trend", "NEUTRAL")
    is_owned = ticker in holdings

    # إعداد سياق التحليل للذكاء الاصطناعي
    prompt = f"""
    أنت مدير استثمار وخبير تداول كمي بالبورصة المصرية (EGX).
    قم بتحليل الأصل التالي واتخاذ قرار استثماري حاسم:
    
    - رمز السهم: {ticker}
    - السعر الحالي: {current_price} جنيه
    - مؤشر القوة النسبية (RSI 14): {rsi}
    - المتوسط المتحرك البسيط (SMA 20): {sma_20} جنيه
    - الاتجاه العام: {trend}
    - هل السهم مملوك في المحفظة حالياً: {'نعم' if is_owned else 'لا'}
    
    المطلوب:
    أصدر قرارك على شكل كائن JSON صالح فقط بدون أي نصوص خارجية أو علامات Markdown:
    {{
        "decision": "BUY" أو "SELL" أو "HOLD",
        "reason": "اكتب مبرر القرار باللغة العربية حصراً وبشكل موجز ودقيق مالياً (مثال: تشبع بيعي عند RSI 30 وارتداد متوقع أعلى المتوسط المتحرك)"
    }}
    """

    try:
        # استشارة نموذج Llama-3.3-70B لصياغة القرار النهائي
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "أنت خبير مالي وتداول آلي. جميع تحليلاتك ومبرراتك يجب أن تكون باللغة العربية فقط وبصيغة JSON دقيقة."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        response_content = chat_completion.choices[0].message.content
        result = json.loads(response_content)
        return result

    except Exception as e:
        # مبررات عربية افتراضية في حال انقطاع الـ API
        fallback_reason = "تحليل فني آلي: "
        if rsi < 35:
            return {"decision": "BUY", "reason": "تشبع بيعي حاد لمؤشر القوة النسبية مع فرصة ارتداد صاعد"}
        elif rsi > 70 and is_owned:
            return {"decision": "SELL", "reason": "وصول السهم لمنطقة تشبع شرائي وجني أرباح"}
        else:
            return {"decision": "HOLD", "reason": "استقرار المؤشرات الفنية وانتظار إشارة دخول واضحة"}
