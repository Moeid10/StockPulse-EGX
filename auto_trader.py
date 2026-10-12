import time
import json
import re
from datetime import datetime
from market_data import get_stock_metrics
from portfolio_manager import execute_trade, PORTFOLIO_FILE, init_portfolio
from groq import Groq

# إعداد مفتاح Groq
GROQ_API_KEY = "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"
client = Groq(api_key=GROQ_API_KEY)

# قائمة الأسهم المراقبة
WATCHLIST = {
    "Madinet Masr": "MASR.CA",
    "CIB": "COMI.CA",
    "Talaat Moustafa": "TMGH.CA",
    "Ibnsina Pharma": "ISPH.CA",
    "MOPCO": "MFPC.CA",
    "Abu Qir": "ABUK.CA"
}

def get_portfolio():
    init_portfolio()
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_reasoning_output(text):
    # إزالة وسوم التفكير الخاصة بـ DeepSeek إذا وجدت
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return cleaned

def query_model(model_name, prompt):
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_name,
            temperature=0.1,
        )
        res = completion.choices[0].message.content.strip()
        res = clean_reasoning_output(res)
        
        first_word = res.split()[0].upper().replace(",", "").replace(".", "").replace("*", "")
        action = "HOLD"
        if "BUY" in first_word:
            action = "BUY"
        elif "SELL" in first_word:
            action = "SELL"
        return action, res
    except Exception as e:
        return "HOLD", f"Model Error ({model_name}): {e}"

def consult_ai(name, ticker, metrics):
    prompt = f"""
    You are an elite quantitative hedge fund analyst evaluating EGX stock: {name} ({ticker}).
    Technical Indicators:
    - Current Price: {metrics['current_price']} EGP
    - RSI (14): {metrics['rsi']}
    - SMA 20: {metrics['sma_20']}
    - Trend: {metrics['trend']}

    Instruction:
    Your output MUST start with exactly one word: BUY, SELL, or HOLD.
    Followed by exactly ONE brief, factual sentence justifying the decision based on RSI and trend.
    """

    # استشارة أقوى نموذجين على المنصة
    action_deepseek, reason_deepseek = query_model("deepseek-r1-distill-llama-70b", prompt)
    action_llama, reason_llama = query_model("llama-3.3-70b-versatile", prompt)

    print(f"   ├─ [DeepSeek-R1-70B]: {action_deepseek} | {reason_deepseek}")
    print(f"   └─ [Llama-3.3-70B]  : {action_llama} | {reason_llama}")

    # قاعدة اتخاذ القرار: إجماع كامل للدخول، وتحذير فردي للخروج
    if action_deepseek == "BUY" and action_llama == "BUY":
        final_action = "BUY"
        final_reason = f"Dual AI Consensus BUY: {reason_deepseek}"
    elif action_deepseek == "SELL" or action_llama == "SELL":
        final_action = "SELL"
        final_reason = f"Dual AI Risk SELL: {reason_deepseek if action_deepseek == 'SELL' else reason_llama}"
    else:
        final_action = "HOLD"
        final_reason = f"Consensus not reached (DeepSeek: {action_deepseek}, Llama: {action_llama})"

    return final_action, final_reason

def run_trading_cycle():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==========================================")
    print(f"[*] Dual-AI Trading Engine Running: {now_str}")
    print(f"==========================================")
    
    portfolio = get_portfolio()
    cash = float(portfolio.get("cash", 0))
    holdings = portfolio.get("holdings", {})

    print(f"[PORTFOLIO] Cash: {cash:,.2f} EGP | Active Positions: {len(holdings)}")

    # 1. مراقبة المراكز المفتوحة وشروط الأمان
    for ticker in list(holdings.keys()):
        metrics = get_stock_metrics(ticker)
        if "error" in metrics:
            continue
            
        current_price = metrics["current_price"]
        pos_data = holdings[ticker]
        entry_price = pos_data.get("avg_price", current_price) if isinstance(pos_data, dict) else current_price

        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0
        print(f"\n[MONITORING] {ticker} | Entry: {entry_price} | Current: {current_price} | PnL: {pnl_pct:.2f}%")

        if pnl_pct <= -3.0:
            print(f"[!] TRIGGER: Stop-Loss reached (-3%) for {ticker}")
            execute_trade(ticker, "SELL", current_price, reason="Stop-Loss Triggered (-3%)")
        elif pnl_pct >= 6.0:
            print(f"[+] TRIGGER: Take-Profit reached (+6%) for {ticker}")
            execute_trade(ticker, "SELL", current_price, reason="Take-Profit Triggered (+6%)")
        else:
            action, reason = consult_ai(ticker, ticker, metrics)
            print(f"Final Decision: {action}")
            if action == "SELL":
                print(f"[!] TRIGGER: AI Consensus Exit for {ticker}")
                execute_trade(ticker, "SELL", current_price, reason=reason)

    # 2. فحص واقتناص فرص جديدة
    if cash > 10000:
        for name, ticker in WATCHLIST.items():
            if ticker in holdings:
                continue

            metrics = get_stock_metrics(ticker)
            if "error" in metrics:
                continue

            print(f"\n[SCANNING] {name} ({ticker}) | Price: {metrics['current_price']} EGP")
            action, reason = consult_ai(name, ticker, metrics)
            print(f"Final Decision: {action}")

            if action == "BUY":
                print(f"[+] EXECUTING ENTRY: {ticker}")
                execute_trade(symbol=ticker, action="BUY", price=metrics["current_price"], reason=reason)
                portfolio = get_portfolio()
                cash = float(portfolio.get("cash", 0))
                if cash < 10000:
                    print("[!] Minimum cash reserve reached.")
                    break
    else:
        print("[i] Capital fully deployed or below threshold.")

    print(f"\n[*] Cycle complete. Next scan in 60s...")

if __name__ == "__main__":
    print(">>> StockPulse Dual-AI Engine (DeepSeek-R1-70B + Llama-3.3-70B) is Online...")
    print(">>> Press Ctrl + C to stop at any time.")
    
    CHECK_INTERVAL_SECONDS = 60 

    while True:
        try:
            run_trading_cycle()
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[!] Engine Stopped.")
            break
        except Exception as e:
            print(f"\n[!] Unexpected Error: {e}")
            time.sleep(10)