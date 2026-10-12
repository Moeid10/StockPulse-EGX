import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from market_data import get_stock_metrics
from egx_assets import EGX_ASSETS
from database import verify_user, register_user, get_user_portfolio, execute_user_trade, panic_liquidate_user

st.set_page_config(
    page_title="StockPulse EGX - AI Fund Manager",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
    <meta name="google" content="notranslate">
    <style>
    .notranslate { translate: no !important; }
    h1, h2, h3, h4, p, span, label {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        text-align: right;
        direction: rtl;
    }
    </style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

# شاشة تسجيل الدخول
if not st.session_state["authenticated"]:
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        st.title("🔐 تسجيل الدخول إلى المنصة")
        tab_login, tab_register = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        
        with tab_login:
            u_name = st.text_input("اسم المستخدم", key="login_user")
            u_pass = st.text_input("كلمة المرور", type="password", key="login_pass")
            if st.button("دخول", use_container_width=True):
                if verify_user(u_name, u_pass):
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
                    st.warning("يرجى ملء كافة الحقول.")
                elif reg_pass != reg_pass_conf:
                    st.error("كلمات المرور غير متطابقة.")
                else:
                    ok, msg = register_user(reg_user, reg_pass)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()

# ----------------- اللوحة الرئيسية -----------------
current_user = st.session_state["username"]

with st.sidebar:
    st.write(f"المستخدم: **{current_user}** 👤")
    if st.button("تسجيل الخروج"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()
    st.subheader("⚠️ مركز الطوارئ")
    if st.button("🚨 تسييل المحفظة بالكامل (Panic Sell)", type="primary", use_container_width=True):
        u_port = get_user_portfolio(current_user)
        market_prices = {}
        for sym in u_port["holdings"].keys():
            m = get_stock_metrics(sym)
            market_prices[sym] = m.get("current_price", 10.0)
        ok, msg = panic_liquidate_user(current_user, market_prices)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.warning(msg)

col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.title("📊 منصة إدارة الاستثمار الآلي للبورصة المصرية")
    st.caption(f"نظام الذكاء الاصطناعي المزدوج | المحفظة الاستثمارية لـ: {current_user}")
with col_t2:
    st.success("🟢 محرك التداول: قيد التشغيل")
    st.write(f"آخر فحص: {datetime.now().strftime('%H:%M:%S')}")

port = get_user_portfolio(current_user)
cash = port["cash"]
holdings = port["holdings"]
trade_history = port["trade_history"]

holdings_rows = []
invested_val = 0.0
allocation_labels = ["السيولة النقدية (Cash)"]
allocation_values = [cash]

for sym, info in holdings.items():
    shares = info["shares"]
    avg_price = info["avg_price"]
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

m1, m2, m3, m4 = st.columns(4)
m1.metric("القيمة الإجمالية للمحفظة", f"{total_portfolio_value:,.2f} ج")
m2.metric("السيولة النقدية المتاحة", f"{cash:,.2f} ج")
m3.metric("رأس المال في الأسهم", f"{invested_val:,.2f} ج")
m4.metric("العائد الإجمالي (P&L)", f"{total_pnl:,.2f} ج", delta=f"{total_pnl_pct:.2f}%")

st.divider()

with st.expander("⚡ تنفيذ صفقة يدوية فورية (Manual Trade Override)", expanded=False):
    t_c1, t_c2, t_c3, t_c4 = st.columns(4)
    with t_c1:
        asset_names = list(EGX_ASSETS.keys())
        selected_label = st.selectbox("اختر السهم أو الصندوق للتداول", asset_names)
        trade_ticker = EGX_ASSETS[selected_label]
    with t_c2:
        trade_type = st.selectbox("نوع العملية", ["BUY", "SELL"])
    with t_c3:
        trade_shares = st.number_input("الكمية (عدد الأسهم)", min_value=1, value=100, step=10)
    with t_c4:
        st.write("")
        st.write("")
        if st.button("🚀 تنفيذ الأمر فوراً", use_container_width=True):
            metrics = get_stock_metrics(trade_ticker)
            exec_price = metrics.get("current_price", 10.0)
            suc, message = execute_user_trade(current_user, trade_ticker, trade_type, exec_price, int(trade_shares), reason="أمر يدوي مباشر من لوحة التحكم")
            if suc:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

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

st.subheader("📌 الأسهم المملوكة حالياً")
if holdings_rows:
    df_holdings = pd.DataFrame(holdings_rows)
    st.table(df_holdings)
else:
    st.info("لا توجد أسهم مملوكة حالياً.")

st.divider()

st.subheader("📜 آخر صفقات ومبررات الذكاء الاصطناعي")
if trade_history:
    recent = trade_history[:6]
    table_data = []
    for t in recent:
        time_str = t.get("date", "").split()[-1] if " " in t.get("date", "") else t.get("date", "")
        p_val = float(t.get("price", 0.0))
        s_val = int(t.get("shares", 0))
        tot = float(t.get("total_value", p_val * s_val))
        action_tag = "🟢 شراء" if t.get("type") == "BUY" else "🔴 بيع"
        
        table_data.append({
            "التوقيت": time_str,
            "السهم": t.get("symbol", ""),
            "العملية": action_tag,
            "الكمية": s_val,
            "السعر": f"{p_val:.2f} ج",
            "الإجمالي": f"{tot:,.2f} ج",
            "مبرر الذكاء الاصطناعي": t.get("reason", "تنفيذ استراتيجي")
        })
        
    df_trades = pd.DataFrame(table_data)
    st.table(df_trades)
else:
    st.info("لم يتم تسجيل صفقات بعد.")
