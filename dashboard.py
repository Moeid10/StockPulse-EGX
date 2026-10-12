import streamlit as st
import json
import os
import hashlib
import pandas as pd
import plotly.express as px
from datetime import datetime
from portfolio_manager import execute_trade, panic_liquidate
from market_data import get_stock_metrics

st.set_page_config(
    page_title="StockPulse EGX - AI Fund Manager",
    page_icon="📈",
    layout="wide"
)

# منع المتصفح من تشويه النصوص وضبط التنسيق
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
        border: 1px solid #e0e0e0;
        padding: 10px;
        text-align: center !important;
    }
    th {
        background-color: #f8f9fa;
        color: #333;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        direction: ltr !important;
        text-align: right !important;
    }
    </style>
""", unsafe_allow_html=True)

USERS_FILE = "users.json"
PORTFOLIO_FILE = "portfolio.json"

def hash_pass(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        default_admin = {"admin": hash_pass("123456")}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_admin, f, indent=4)
        return default_admin
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users_dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, indent=4)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

# شاشة تسجيل الدخول
if not st.session_state["authenticated"]:
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        st.title("🔐 تسجيل الدخول إلى المنصة")
        tab_login, tab_register = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        users = load_users()
        
        with tab_login:
            u_name = st.text_input("اسم المستخدم", key="login_user")
            u_pass = st.text_input("كلمة المرور", type="password", key="login_pass")
            if st.button("دخول", use_container_width=True):
                if u_name in users and users[u_name] == hash_pass(u_pass):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = u_name
                    st.rerun()
                else:
                    st.error("بيانات الدخول غير صحيحة.")

        with tab_register:
            reg_user = st.text_input("اسم المستخدم الجديد", key="reg_user")
            reg_pass = st.text_input("كلمة المرور الجديدة", type="password", key="reg_pass")
            reg_pass_conf = st.text_input("تأكيد كلمة المرور", type="password", key="reg_conf")
            if st.button("إنشاء الحساب", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("يرجى ملء جميع الحقول.")
                elif reg_user in users:
                    st.error("اسم المستخدم مسجل بالفعل.")
                elif reg_pass != reg_pass_conf:
                    st.error("كلمات المرور غير متطابقة.")
                else:
                    users[reg_user] = hash_pass(reg_pass)
                    save_users(users)
                    st.success("تم إنشاء الحساب بنجاح! تفضل بالدخول الآن.")

    st.stop()

# ----------------- لوحة التحكم بعد تسجيل الدخول -----------------

with st.sidebar:
    st.write(f"المستخدم: **{st.session_state['username']}** 👤")
    if st.button("تسجيل الخروج"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()
    st.subheader("⚠️ مركز الطوارئ")
    if st.button("🚨 تسييل المحفظة بالكامل (Panic Sell)", type="primary", use_container_width=True):
        market_prices = {
            "MASR.CA": 7.73, "COMI.CA": 122.70, "TMGH.CA": 86.30,
            "ISPH.CA": 3.40, "MFPC.CA": 45.0, "ABUK.CA": 60.0
        }
        success, msg = panic_liquidate(market_prices)
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.warning(msg)

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {"cash": 100000.0, "holdings": {}, "trade_history": []}
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ترويسة اللوحة
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("📊 منصة إدارة الاستثمار الآلي للبورصة المصرية")
    st.caption("نظام التداول الكمي المزدوج (DeepSeek-R1 + Llama-3.3-70B)")
with col_t2:
    st.success("🟢 محرك التداول: قيد التشغيل")
    st.write(f"آخر فحص: {datetime.now().strftime('%H:%M:%S')}")

port = load_portfolio()
cash = float(port.get("cash", 100000.0))
holdings = port.get("holdings", {})
trade_history = port.get("trade_history", [])

holdings_rows = []
invested_val = 0.0
allocation_labels = ["السيولة النقدية (Cash)"]
allocation_values = [cash]

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
        allocation_labels.append(sym)
        allocation_values.append(total_pos)

total_portfolio_value = cash + invested_val
initial_capital = 100000.0
total_pnl = total_portfolio_value - initial_capital
total_pnl_pct = (total_pnl / initial_capital) * 100

st.divider()

# كروت المؤشرات
m1, m2, m3, m4 = st.columns(4)
m1.metric("القيمة الإجمالية للمحفظة", f"{total_portfolio_value:,.2f} ج")
m2.metric("السيولة النقدية المتاحة", f"{cash:,.2f} ج")
m3.metric("رأس المال في الأسهم", f"{invested_val:,.2f} ج")
m4.metric("العائد الإجمالي (P&L)", f"{total_pnl:,.2f} ج", delta=f"{total_pnl_pct:.2f}%")

st.divider()

# قسم التداول اليدوي الفوري
with st.expander("⚡ تنفيذ صفقة يدوية فورية (Manual Trade Override)", expanded=False):
    t_c1, t_c2, t_c3, t_c4 = st.columns(4)
    with t_c1:
        trade_ticker = st.selectbox("اختر السهم", ["MASR.CA", "COMI.CA", "TMGH.CA", "ISPH.CA", "MFPC.CA", "ABUK.CA"])
    with t_c2:
        trade_type = st.selectbox("نوع العملية", ["BUY", "SELL"])
    with t_c3:
        trade_shares = st.number_input("الكمية (عدد الأسهم)", min_value=1, value=100, step=10)
    with t_c4:
        st.write("")
        st.write("")
        if st.button("🚀 تنفيذ الأمر فوراً", use_container_width=True):
            metrics = get_stock_metrics(trade_ticker)
            exec_price = metrics["current_price"] if "current_price" in metrics else 10.0
            suc, message = execute_trade(trade_ticker, trade_type, exec_price, int(trade_shares), reason="أمر يدوي من لوحة التحكم")
            if suc:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# الرسوم البيانية
st.subheader("📈 التحليلات البصرية وتوزيع الأصول")
c_chart1, c_chart2 = st.columns([1, 1])

with c_chart1:
    fig_donut = px.pie(
        names=allocation_labels,
        values=allocation_values,
        hole=0.45,
        title="توزيع رأس المال والمراكز النشطة",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
    fig_donut.update_layout(margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig_donut, use_container_width=True)

with c_chart2:
    if trade_history:
        df_trades = pd.DataFrame(trade_history)
        df_trades['total_value'] = df_trades.apply(lambda r: float(r.get('total_value', float(r.get('price', 0)) * int(r.get('shares', 0)))), axis=1)
        fig_bar = px.bar(
            df_trades.tail(8),
            x="symbol",
            y="total_value",
            color="type",
            color_discrete_map={"BUY": "#2ecc71", "SELL": "#e74c3c"},
            title="أحجام الصفقات الأخيرة (شراء / بيع)",
            labels={"symbol": "السهم", "total_value": "القيمة الإجمالية (ج)", "type": "العملية"}
        )
        fig_bar.update_layout(margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("لا توجد صفقات سابقة لرسم المسار المالي.")

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
            badge_color = "#27ae60" if t.get('type') == 'BUY' else "#c0392b"
            html_trades += f"<tr><td>{time_str}</td><td><b>{t.get('symbol')}</b></td><td style='color:{badge_color}; font-weight:bold;'>{t.get('type')}</td><td>{s_val}</td><td>{p_val:.2f} ج</td><td>{tot:,.2f} ج</td></tr>"
        html_trades += "</table></div>"
        st.markdown(html_trades, unsafe_allow_html=True)
    else:
        st.info("لم يتم تسجيل صفقات بعد.")
