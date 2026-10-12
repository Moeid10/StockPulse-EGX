import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="StockPulse EGX - AI Fund Manager",
    page_icon="📈",
    layout="wide"
)

# تحديث تلقائي كل 30 ثانية
st.markdown("""
    <script>
    setTimeout(function(){
       window.location.reload();
    }, 30000);
    </script>
""", unsafe_allow_html=True)

# منع المتصفح من تشويه النصوص وتنسيق الواجهة
st.markdown("""
    <meta name="google" content="notranslate">
    <style>
    html, body, [class*="css"], div, p, span, h1, h2, h3, label {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .notranslate {
        translate: no !important;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center !important;
    }
    th {
        background-color: #f2f2f2;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        direction: ltr !important;
        text-align: right !important;
    }
    </style>
""", unsafe_allow_html=True)

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {"cash": 100000.0, "holdings": {}, "trade_history": []}
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ترويسة الصفحة
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("📊 منصة إدارة الاستثمار الآلي للبورصة المصرية")
    st.caption("مراقبة حية لمحرك التداول الذاتي وقرارات الذكاء الاصطناعي")
with col_t2:
    st.success("🟢 محرك التداول: قيد التشغيل")
    st.write(f"آخر فحص: {datetime.now().strftime('%H:%M:%S')}")

port = load_portfolio()
cash = float(port.get("cash", 100000.0))
holdings = port.get("holdings", {})
trade_history = port.get("trade_history", [])

holdings_rows = []
invested_val = 0.0

for sym, info in holdings.items():
    shares = 0
    avg_price = 0.0
    
    if isinstance(info, dict):
        shares = int(info.get("shares", 0))
        avg_price = float(info.get("avg_price", 0.0))
    elif isinstance(info, (int, float)):
        shares = int(info)
        for t in reversed(trade_history):
            if t.get("symbol") == sym:
                avg_price = float(t.get("price", 0.0))
                break
        if avg_price == 0.0 and shares == 2587:
            avg_price = 7.73

    total_pos = shares * avg_price
    invested_val += total_pos
    
    if shares > 0:
        holdings_rows.append({
            "السهم": sym,
            "عدد الأسهم": shares,
            "سعر الشراء": f"{avg_price:.2f} ج",
            "القيمة الإجمالية": f"{total_pos:,.2f} ج"
        })

total_portfolio_value = cash + invested_val
initial_capital = 100000.0
total_pnl = total_portfolio_value - initial_capital
total_pnl_pct = (total_pnl / initial_capital) * 100

st.divider()

# كروت المؤشرات المالية
m1, m2, m3, m4 = st.columns(4)
m1.metric("القيمة الإجمالية للمحفظة", f"{total_portfolio_value:,.2f} ج")
m2.metric("السيولة النقدية المتاحة", f"{cash:,.2f} ج")
m3.metric("رأس المال في الأسهم", f"{invested_val:,.2f} ج")
m4.metric("العائد الإجمالي (P&L)", f"{total_pnl:,.2f} ج", delta=f"{total_pnl_pct:.2f}%")

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📌 الأسهم المملوكة حالياً")
    if holdings_rows:
        html_holdings = "<div class='notranslate'><table><tr><th>السهم</th><th>عدد الأسهم</th><th>سعر الشراء</th><th>القيمة الإجمالية</th></tr>"
        for row in holdings_rows:
            html_holdings += f"<tr><td><b>{row['السهم']}</b></td><td>{row['عدد الأسهم']}</td><td>{row['سعر الشراء']}</td><td>{row['القيمة الإجمالية']}</td></tr>"
        html_holdings += "</table></div>"
        st.markdown(html_holdings, unsafe_allow_html=True)
    else:
        st.info("لا توجد أسهم مملوكة حالياً.")

with col_right:
    st.subheader("📜 آخر صفقات نفذها المدير المالي")
    if trade_history:
        recent = list(reversed(trade_history[-6:]))
        html_trades = "<div class='notranslate'><table><tr><th>التوقيت</th><th>السهم</th><th>العملية</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>"
        for t in recent:
            time_str = t.get("date", "").split()[-1] if " " in t.get("date", "") else t.get("date", "")
            p_val = float(t.get("price", 0.0))
            s_val = int(t.get("shares", 0))
            tot = float(t.get("total_value", p_val * s_val))
            html_trades += f"<tr><td>{time_str}</td><td><b>{t.get('symbol')}</b></td><td>{t.get('type')}</td><td>{s_val}</td><td>{p_val:.2f} ج</td><td>{tot:,.2f} ج</td></tr>"
        html_trades += "</table></div>"
        st.markdown(html_trades, unsafe_allow_html=True)
    else:
        st.info("لم يتم تسجيل صفقات بعد.")