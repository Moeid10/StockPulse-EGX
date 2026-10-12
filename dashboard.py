import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from market_data import get_stock_metrics
from egx_assets import EGX_ASSETS
from database import (
    verify_user, 
    register_user, 
    get_user_portfolio, 
    execute_user_trade, 
    panic_liquidate_user,
    get_all_users_summary
)

st.set_page_config(
    page_title="StockPulse | Thndr Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ثيم وتنسيق مستوحى من Thndr & Telda (Dark Emerald Minimalist)
st.markdown("""
<meta name="google" content="notranslate">
<style>
    .stApp {
        background-color: #0c0d12 !important;
        color: #f1f5f9 !important;
    }

    .thndr-card {
        background: #141721;
        border: 1px solid #1f2433;
        border-radius: 18px;
        padding: 20px 24px;
        margin-bottom: 20px;
        direction: rtl;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .thndr-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }

    .thndr-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
    }

    .thndr-tag {
        background: rgba(0, 230, 118, 0.12);
        color: #00E676;
        border: 1px solid rgba(0, 230, 118, 0.25);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
    }

    .metrics-wrapper {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
        direction: rtl;
    }

    .m-card {
        background: #141721;
        border: 1px solid #1e2330;
        border-radius: 16px;
        padding: 16px 18px;
        transition: border-color 0.2s ease;
    }
    .m-card:hover {
        border-color: #00E676;
    }

    .m-label {
        color: #8b949e;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 6px;
    }

    .m-value {
        font-size: 1.45rem;
        font-weight: 800;
        color: #ffffff;
        direction: ltr;
        text-align: right;
    }

    .m-sub-up {
        color: #00E676;
        font-size: 0.82rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .m-sub-down {
        color: #ff5252;
        font-size: 0.82rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .stTable table {
        background: #141721 !important;
        border-radius: 14px !important;
        border: 1px solid #1e2330 !important;
        overflow: hidden !important;
        direction: rtl !important;
        width: 100% !important;
    }
    .stTable th {
        background: #181d2a !important;
        color: #8b949e !important;
        font-weight: 700 !important;
        padding: 12px 14px !important;
        border-bottom: 1px solid #23293a !important;
        text-align: right !important;
    }
    .stTable td {
        color: #f1f5f9 !important;
        padding: 14px !important;
        border-bottom: 1px solid #1a1f2c !important;
        text-align: right !important;
    }

    div[data-testid="stExpander"] {
        background: #141721 !important;
        border: 1px solid #1e2330 !important;
        border-radius: 16px !important;
    }

    button[kind="primary"] {
        background: #00E676 !important;
        color: #0c0d12 !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background: #00c853 !important;
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

# ----------------- تسجيل الدخول -----------------
if not st.session_state["authenticated"]:
    _, col_auth, _ = st.columns([1, 2, 1])
    with col_auth:
        st.markdown("""
            <div style="text-align: center; margin: 40px 0 25px 0; direction: rtl;">
                <h1 style="color: #00E676; font-size: 2.1rem; font-weight: 800; margin: 0;">⚡ StockPulse</h1>
                <p style="color: #8b949e; font-size: 0.95rem; margin-top: 6px;">محفظتك الاستثمارية الذكية للبورصة المصرية</p>
            </div>
        """, unsafe_allow_html=True)
        
        tab_log, tab_reg = st.tabs(["تسجيل الدخول", "فتح حساب جديد"])
        
        with tab_log:
            st.write("")
            u_name = st.text_input("اسم المستخدم", key="log_user")
            u_pass = st.text_input("كلمة المرور", type="password", key="log_pass")
            if st.button("دخول إلى المحفظة", use_container_width=True, type="primary"):
                if verify_user(u_name, u_pass):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = u_name
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")

        with tab_reg:
            st.write("")
            reg_user = st.text_input("اسم مستخدم جديد", key="r_user")
            reg_pass = st.text_input("كلمة المرور", type="password", key="r_pass")
            reg_conf = st.text_input("تأكيد كلمة المرور", type="password", key="r_conf")
            if st.button("تفعيل المحفظة بـ 100,000 ج", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("يرجى ملء جميع الحقول.")
                elif reg_pass != reg_conf:
                    st.error("كلمات المرور غير متطابقة.")
                else:
                    ok, msg = register_user(reg_user, reg_pass)
                    if ok:
                        st.success("تم تفعيل حسابك بنجاح! يمكنك الآن تسجيل الدخول.")
                    else:
                        st.error(msg)
    st.stop()

# ----------------- الشاشة الرئيسية -----------------
current_user = st.session_state["username"]

with st.sidebar:
    st.markdown(f"**المستخدم الحالي:** `{current_user}` 👤")
    if st.button("تسجيل الخروج", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()
    
    with st.expander("👑 بيانات ومحافظ المسجلين"):
        all_users = get_all_users_summary()
        if all_users:
            df_users = pd.DataFrame(all_users)
            df_users.rename(columns={
                "username": "المستخدم",
                "created_at": "تاريخ التسجيل",
                "cash": "السيولة (ج)"
            }, inplace=True)
            st.dataframe(df_users, hide_index=True)
        else:
            st.caption("لا يوجد مستخدمون مسجلون.")

    st.divider()
    st.markdown("<p style='color: #ff5252; font-weight: 700; font-size: 0.85rem;'>⚠️ إدارة المخاطر</p>", unsafe_allow_html=True)
    if st.button("🚨 تسييل المحفظة (Panic Sell)", type="primary", use_container_width=True):
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

# جلب بيانات المحفظة وحساب القيم
port = get_user_portfolio(current_user)
cash = float(port.get("cash", 100000.0))
holdings = port.get("holdings", {})
trade_history = port.get("trade_history", [])

holdings_rows = []
invested_val = 0.0
allocation_labels = ["كاش غير مستثمر"]
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

pnl_class = "m-sub-up" if total_pnl >= 0 else "m-sub-down"
pnl_sign = "+" if total_pnl >= 0 else ""

# 1. الترويسة الرئيسية
now_str = datetime.now().strftime("%I:%M %p")
st.markdown(f"""
    <div class="thndr-card">
        <div class="thndr-header">
            <div>
                <h2 class="thndr-title">⚡ StockPulse • محفظة {current_user}</h2>
                <div style="color: #8b949e; font-size: 0.85rem; margin-top: 4px;">تداول آلي كمي مدعوم بالذكاء الاصطناعي وإدارة المخاطر</div>
            </div>
            <div class="thndr-tag">● السوق نشط • {now_str}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 2. كروت المؤشرات المالية
st.markdown(f"""
    <div class="metrics-wrapper">
        <div class="m-card">
            <div class="m-label">إجمالي قيمة الحساب</div>
            <div class="m-value">{total_portfolio_value:,.2f} <span style="font-size: 0.85rem; color:#8b949e;">ج</span></div>
        </div>
        <div class="m-card">
            <div class="m-label">السيولة المتاحة (كاش)</div>
            <div class="m-value">{cash:,.2f} <span style="font-size: 0.85rem; color:#8b949e;">ج</span></div>
        </div>
        <div class="m-card">
            <div class="m-label">المستثمر في الأسهم</div>
            <div class="m-value">{invested_val:,.2f} <span style="font-size: 0.85rem; color:#8b949e;">ج</span></div>
        </div>
        <div class="m-card">
            <div class="m-label">إجمالي الأرباح / الخسائر</div>
            <div class="m-value">{pnl_sign}{total_pnl:,.2f} <span style="font-size: 0.85rem; color:#8b949e;">ج</span></div>
            <div class="{pnl_class}">{pnl_sign}{total_pnl_pct:.2f}% منذ البداية</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 3. تنفيذ صفقة يدوية فورية
with st.expander("⚡ تنفيذ صفقة يدوية فورية (Manual Trade)", expanded=False):
    t1, t2, t3, t4 = st.columns([2, 1, 1, 1.2])
    with t1:
        asset_names = list(EGX_ASSETS.keys())
        selected_label = st.selectbox("اختر السهم / الأصل", asset_names)
        trade_ticker = EGX_ASSETS[selected_label]
    with t2:
        trade_type = st.selectbox("نوع العملية", ["BUY", "SELL"])
    with t3:
        trade_shares = st.number_input("الكمية", min_value=1, value=100, step=10)
    with t4:
        st.write("")
        st.write("")
        if st.button("🚀 تأكيد العملية", use_container_width=True, type="primary"):
            metrics = get_stock_metrics(trade_ticker)
            exec_price = metrics.get("current_price", 10.0)
            suc, message = execute_user_trade(
                current_user,
                trade_ticker,
                trade_type,
                exec_price,
                int(trade_shares),
                reason="تنفيذ يدوي مباشر من لوحة التحكم"
            )
            if suc:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# 4. الرسوم البيانية
c1, c2 = st.columns(2)

with c1:
    fig_donut = px.pie(
        names=allocation_labels,
        values=allocation_values,
        hole=0.6,
        title="توزيع الأصول والمراكز",
        color_discrete_sequence=['#00E676', '#1E88E5', '#FFB300', '#D81B60', '#8E24AA']
    )
    fig_donut.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#0c0d12', width=2)))
    fig_donut.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8b949e'),
        margin=dict(t=40, b=10, l=10, r=10),
        showlegend=False
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with c2:
    if trade_history:
        cleaned_trades = []
        for t in trade_history[-7:]:
            p_val = float(t.get("price", 0.0))
            s_val = int(t.get("shares", 0))
            tot = float(t.get("total_value", p_val * s_val))
            cleaned_trades.append({
                "symbol": str(t.get("symbol", "")),
                "total_value": tot,
                "type": str(t.get("type", "BUY"))
            })
            
        df_trades = pd.DataFrame(cleaned_trades)
        if not df_trades.empty and "total_value" in df_trades.columns:
            fig_bar = px.bar(
                df_trades,
                x="symbol",
                y="total_value",
                color="type",
                color_discrete_map={"BUY": "#00E676", "SELL": "#ff5252"},
                title="أحدث الصفقات المنفذة",
                labels={"symbol": "السهم", "total_value": "القيمة (ج)", "type": "العملية"}
            )
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#8b949e'),
                margin=dict(t=40, b=10, l=10, r=10),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("بيانات الصفقات غير مكتملة للرسم البياني.")
    else:
        st.info("لا توجد صفقات لعرض المسار البياني.")

st.divider()

# 5. الجداول
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
            "الوقت": time_str,
            "السهم": t.get("symbol", ""),
            "العملية": action_tag,
            "الكمية": f"{s_val:,}",
            "السعر": f"{p_val:.2f} ج",
            "الإجمالي": f"{tot:,.2f} ج",
            "مبرر الذكاء الاصطناعي": t.get("reason", "تنفيذ استراتيجي آلي")
        })
    st.table(pd.DataFrame(table_data))
else:
    st.info("لم يتم تسجيل أي صفقات بعد.")
