import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from market_data import get_stock_metrics
from egx_assets import EGX_ASSETS
from database import verify_user, register_user, get_user_portfolio, execute_user_trade, panic_liquidate_user

st.set_page_config(
    page_title="StockPulse EGX | البورصة المصرية",
    page_icon="📈",
    layout="wide"
)

# تنسيق مريح ونظيف للعين وبدون كسر لأيقونات النظام
st.markdown("""
<meta name="google" content="notranslate">
<style>
    .notranslate { translate: no !important; }
    
    /* ضبط اتجاه النصوص والقراءة العربية */
    h1, h2, h3, h4, p, label {
        direction: rtl;
        text-align: right;
    }
    
    /* تحسين مظهر الكروت التفاعلية */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #64748b !important;
        direction: rtl;
        text-align: right;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    /* تحسين الجداول لتكون واضحة بدون قص */
    .stTable table {
        width: 100% !important;
        border-collapse: collapse !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid #e2e8f0 !important;
    }
    .stTable th {
        background-color: #f8fafc !important;
        color: #475569 !important;
        font-weight: 600 !important;
        padding: 12px !important;
        text-align: right !important;
    }
    .stTable td {
        padding: 12px !important;
        color: #1e293b !important;
        border-bottom: 1px solid #f1f5f9 !important;
        text-align: right !important;
    }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

# شاشة تسجيل الدخول
if not st.session_state["authenticated"]:
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        st.markdown("<h2 style='text-align: center;'>📈 StockPulse EGX</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>منصة التداول الآلي وإدارة المحافظ للبورصة المصرية</p>", unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        
        with tab_login:
            u_name = st.text_input("اسم المستخدم", key="login_user")
            u_pass = st.text_input("كلمة المرور", type="password", key="login_pass")
            if st.button("دخول", use_container_width=True, type="primary"):
                if verify_user(u_name, u_pass):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = u_name
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")

        with tab_register:
            reg_user = st.text_input("اسم مستخدم جديد", key="reg_user")
            reg_pass = st.text_input("كلمة المرور", type="password", key="reg_pass")
            reg_pass_conf = st.text_input("تأكيد كلمة المرور", type="password", key="reg_conf")
            if st.button("إنشاء حساب", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("يرجى ملء جميع الحقول.")
                elif reg_pass != reg_pass_conf:
                    st.error("كلمتا المرور غير متطابقتين.")
                else:
                    ok, msg = register_user(reg_user, reg_pass)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()

# ----------------- الشاشة الرئيسية -----------------
current_user = st.session_state["username"]

with st.sidebar:
    st.markdown(f"**المستخدم:** `{current_user}` 👤")
    if st.button("تسجيل الخروج", use_container_width=True):
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

# ترويسة الصفحة
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("📊 لوحة إدارة الاستثمار والتداول الآلي")
    st.caption("تحليل فني ذكي (DeepSeek + Llama) • إدارة مخاطر آلية")
with col_h2:
    st.success("🟢 محرك التداول متصل")
    st.caption(f"توقيت التحديث: {datetime.now().strftime('%H:%M:%S')}")

# جلب بيانات المحفظة
port = get_user_portfolio(current_user)
cash = float(port.get("cash", 100000.0))
holdings = port.get("holdings", {})
trade_history = port.get("trade_history", [])

holdings_rows = []
invested_val = 0.0
allocation_labels = ["السيولة النقدية (Cash)"]
allocation_values = [cash]

for sym, info in holdings.items():
    shares = int(info.get("shares", 0))
    avg_price = float(info.get("avg_price", 0.0))
    total_pos = shares * avg_price
    invested_val += total_pos
    if shares > 0:
        holdings_rows.append({
            "السهم": sym,
            "الكمية": f"{shares:,}",
            "سعر الشراء": f"{avg_price:.2f} ج",
            "القيمة السوقية": f"{total_pos:,.2f} ج"
        })
        allocation_labels.append(sym)
        allocation_values.append(total_pos)

total_portfolio_value = cash + invested_val
initial_capital = 100000.0
total_pnl = total_portfolio_value - initial_capital
total_pnl_pct = (total_pnl / initial_capital) * 100

st.divider()

# كروت المؤشرات الأساسية (متجاوبة مع الموبايل والكمبيوتر)
m1, m2, m3, m4 = st.columns(4)
m1.metric("إجمالي قيمة المحفظة", f"{total_portfolio_value:,.2f} ج")
m2.metric("السيولة المتاحة", f"{cash:,.2f} ج")
m3.metric("رأس المال في الأسهم", f"{invested_val:,.2f} ج")
m4.metric("صافي العائد (P&L)", f"{total_pnl:,.2f} ج", delta=f"{total_pnl_pct:.2f}%")

st.divider()

# التداول اليدوي
with st.expander("⚡ تنفيذ صفقة يدوية فورية (Manual Trade)", expanded=False):
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1])
    with t1:
        asset_names = list(EGX_ASSETS.keys())
        selected_label = st.selectbox("الأصل المالي", asset_names)
        trade_ticker = EGX_ASSETS[selected_label]
    with t2:
        trade_type = st.selectbox("نوع الأمر", ["BUY", "SELL"])
    with t3:
        trade_shares = st.number_input("عدد الأسهم", min_value=1, value=100, step=10)
    with t4:
        st.write("")
        st.write("")
        if st.button("تنفيذ الصفقة", use_container_width=True, type="primary"):
            metrics = get_stock_metrics(trade_ticker)
            exec_price = metrics.get("current_price", 10.0)
            suc, message = execute_user_trade(current_user, trade_ticker, trade_type, exec_price, int(trade_shares), reason="أمر يدوي من لوحة التحكم")
            if suc:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# الرسوم البيانية بألوان نظيفة ومريحة
c1, c2 = st.columns(2)

with c1:
    fig_donut = px.pie(
        names=allocation_labels,
        values=allocation_values,
        hole=0.45,
        title="توزيع السيولة والأسهم",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
    fig_donut.update_layout(margin=dict(t=40, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig_donut, use_container_width=True)

with c2:
    if trade_history:
        df_trades = pd.DataFrame(trade_history)
        fig_bar = px.bar(
            df_trades.tail(7),
            x="symbol",
            y="total_value",
            color="type",
            color_discrete_map={"BUY": "#10b981", "SELL": "#ef4444"},
            title="أحجام الصفقات الأخيرة",
            labels={"symbol": "السهم", "total_value": "القيمة (ج)", "type": "العملية"}
        )
        fig_bar.update_layout(margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("لا توجد صفقات منفذة بعد.")

st.divider()

# جداول البيانات
st.subheader("📌 الأسهم المملوكة حالياً")
if holdings_rows:
    st.table(pd.DataFrame(holdings_rows))
else:
    st.info("لا توجد أسهم في المحفظة حالياً.")

st.divider()

st.subheader("📜 آخر الصفقات ومبررات الذكاء الاصطناعي")
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
            "النوع": action_tag,
            "الكمية": f"{s_val:,}",
            "السعر": f"{p_val:.2f} ج",
            "الإجمالي": f"{tot:,.2f} ج",
            "مبرر القرار": t.get("reason", "تنفيذ استراتيجي آلي")
        })
    st.table(pd.DataFrame(table_data))
else:
    st.info("لم يتم تسجيل أي صفقات بعد.")
