import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from market_data import get_stock_metrics
from egx_assets import EGX_ASSETS
from database import verify_user, register_user, get_user_portfolio, execute_user_trade, panic_liquidate_user

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="StockPulse EGX | AI Hedge Fund",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. تصميم CSS عصري ومتجاوب بالكامل للموبايل (Responsive FinTech UI)
st.markdown("""
<meta name="google" content="notranslate">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .notranslate { translate: no !important; }
    
    /* خلفية وتنسيق عام */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(18, 20, 29) 0%, rgb(11, 12, 16) 90.2%);
        color: #e0e6ed;
    }
    
    /* ترويسة رئيسية مصممة بنمط بطاقة زجاجية */
    .header-card {
        background: rgba(26, 31, 46, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(10px);
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
        direction: rtl;
    }
    
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(120deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .header-sub {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-top: 4px;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #10b981;
        padding: 6px 14px;
        border-radius: 30px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    /* كروت المؤشرات المالية (Metric Cards) */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 14px;
        margin-bottom: 24px;
        direction: rtl;
    }
    
    .metric-box {
        background: rgba(22, 27, 40, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 16px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-box:hover {
        transform: translateY(-2px);
        border-color: rgba(79, 172, 254, 0.4);
    }
    
    .metric-title {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    
    .metric-val {
        font-size: 1.45rem;
        font-weight: 800;
        color: #f8fafc;
        direction: ltr;
        text-align: right;
    }
    
    .metric-pill-green {
        color: #10b981;
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 4px;
    }
    
    .metric-pill-red {
        color: #ef4444;
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 4px;
    }

    /* تحسين شكل الجداول والبطاقات */
    .stTable, table {
        border-collapse: separate !important;
        border-spacing: 0 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        background: rgba(18, 22, 33, 0.8) !important;
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
    }
    
    th {
        background: #1e2538 !important;
        color: #94a3b8 !important;
        font-weight: 700 !important;
        padding: 12px 14px !important;
        font-size: 0.88rem !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    td {
        padding: 12px 14px !important;
        font-size: 0.88rem !important;
        color: #e2e8f0 !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
    }
    
    /* ضبط مدخلات وأزرار الموبايل */
    button {
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    
    div[data-testid="stExpander"] {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        background: rgba(20, 25, 38, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. إدارة جلسات المستخدمين
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

# 4. شاشة تسجيل الدخول بتصميم مدمج
if not st.session_state["authenticated"]:
    _, col_auth, _ = st.columns([1, 2.2, 1])
    with col_auth:
        st.markdown("""
            <div style="text-align: center; margin: 30px 0 20px 0; direction: rtl;">
                <h1 style="font-size: 2rem; font-weight: 800; color: #4facfe; margin-bottom: 5px;">⚡ منصة StockPulse EGX</h1>
                <p style="color: #94a3b8; font-size: 0.95rem;">منظومة التداول الكمي والذكاء الاصطناعي للبورصة المصرية</p>
            </div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔑 تسجيل الدخول", "✨ إنشاء حساب جديد"])
        
        with tab_login:
            st.write("")
            u_name = st.text_input("اسم المستخدم", key="login_user")
            u_pass = st.text_input("كلمة المرور", type="password", key="login_pass")
            if st.button("دخول إلى المنصة 🚀", use_container_width=True):
                if verify_user(u_name, u_pass):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = u_name
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")

        with tab_register:
            st.write("")
            reg_user = st.text_input("اسم المستخدم الجديد", key="reg_user")
            reg_pass = st.text_input("كلمة المرور الجديدة", type="password", key="reg_pass")
            reg_pass_conf = st.text_input("تأكيد كلمة المرور", type="password", key="reg_conf")
            if st.button("تفعيل المحفظة الاستثمارية 💼", use_container_width=True):
                if not reg_user or not reg_pass:
                    st.warning("يرجى ملء جميع الحقول المطلوبة.")
                elif reg_pass != reg_pass_conf:
                    st.error("كلمات المرور غير متطابقة.")
                else:
                    ok, msg = register_user(reg_user, reg_pass)
                    if ok:
                        st.success(f"{msg} رصيدك الافتراضي 100,000 ج جاهز. تفضل بالدخول الآن.")
                    else:
                        st.error(msg)
    st.stop()

# ----------------- اللوحة الرئيسية للمستخدم -----------------
current_user = st.session_state["username"]

# القائمة الجانبية
with st.sidebar:
    st.markdown(f"""
        <div style="padding: 10px 0; direction: rtl;">
            <p style="margin: 0; color: #94a3b8; font-size: 0.85rem;">المحفظة النشطة:</p>
            <h3 style="margin: 0; color: #4facfe; font-weight: 800;">{current_user}</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("تسجيل الخروج 🚪", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()
    st.markdown("<p style='color: #ef4444; font-weight: 700; font-size: 0.9rem;'>⚠️ بروتوكول الطوارئ</p>", unsafe_allow_html=True)
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

# جلب بيانات المحفظة وحساب القيم
port = get_user_portfolio(current_user)
cash = float(port.get("cash", 100000.0))
holdings = port.get("holdings", {})
trade_history = port.get("trade_history", [])

holdings_rows = []
invested_val = 0.0
allocation_labels = ["السيولة النقدية"]
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
            "متوسط الشراء": f"{avg_price:.2f} ج",
            "القيمة السوقية": f"{total_pos:,.2f} ج"
        })
        allocation_labels.append(sym)
        allocation_values.append(total_pos)

total_portfolio_value = cash + invested_val
initial_capital = 100000.0
total_pnl = total_portfolio_value - initial_capital
total_pnl_pct = (total_pnl / initial_capital) * 100

pnl_color_class = "metric-pill-green" if total_pnl >= 0 else "metric-pill-red"
pnl_sign = "+" if total_pnl >= 0 else ""

# 5. الترويسة الرئيسية المحترفة
now_str = datetime.now().strftime("%I:%M %p")
st.markdown(f"""
    <div class="header-card">
        <div>
            <h1 class="header-title">⚡ لوحة الإدارة الكمية | StockPulse EGX</h1>
            <div class="header-sub">تحليل مزدوج (DeepSeek-R1 + Llama-3.3) • إدارة مخاطر آلية</div>
        </div>
        <div class="status-badge">
            <span style="font-size: 1.1rem;">●</span> متصل بالسحابة • {now_str}
        </div>
    </div>
""", unsafe_allow_html=True)

# 6. بطاقات المؤشرات المالية المتجاوبة للموبايل
st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-title">💼 صافي قيمة المحفظة (NAV)</div>
            <div class="metric-val">{total_portfolio_value:,.2f} <span style="font-size: 0.9rem; color:#94a3b8;">ج</span></div>
        </div>
        <div class="metric-box">
            <div class="metric-title">💵 السيولة المتاحة (Cash)</div>
            <div class="metric-val">{cash:,.2f} <span style="font-size: 0.9rem; color:#94a3b8;">ج</span></div>
        </div>
        <div class="metric-box">
            <div class="metric-title">📊 رأس المال المستثمر</div>
            <div class="metric-val">{invested_val:,.2f} <span style="font-size: 0.9rem; color:#94a3b8;">ج</span></div>
        </div>
        <div class="metric-box">
            <div class="metric-title">📈 العائد المحقق (P&L)</div>
            <div class="metric-val">{pnl_sign}{total_pnl:,.2f} <span style="font-size: 0.9rem; color:#94a3b8;">ج</span></div>
            <div class="{pnl_color_class}">{pnl_sign}{total_pnl_pct:.2f}% منذ التأسيس</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 7. التداول اليدوي الفوري
with st.expander("⚡ تنفيذ صفقة يدوية فورية (Manual Trade)", expanded=False):
    t_c1, t_c2, t_c3, t_c4 = st.columns([2, 1, 1, 1.2])
    with t_c1:
        asset_names = list(EGX_ASSETS.keys())
        selected_label = st.selectbox("اختر الأصل المالي", asset_names)
        trade_ticker = EGX_ASSETS[selected_label]
    with t_c2:
        trade_type = st.selectbox("نوع العملية", ["BUY", "SELL"])
    with t_c3:
        trade_shares = st.number_input("الكمية", min_value=1, value=100, step=10)
    with t_c4:
        st.write("")
        st.write("")
        if st.button("🚀 تنفيذ فوري", use_container_width=True):
            metrics = get_stock_metrics(trade_ticker)
            exec_price = metrics.get("current_price", 10.0)
            suc, message = execute_user_trade(current_user, trade_ticker, trade_type, exec_price, int(trade_shares), reason="أمر يدوي مباشر من لوحة التحكم")
            if suc:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# 8. الرسوم البيانية التفاعلية بنمط Dark Theme
c_chart1, c_chart2 = st.columns([1, 1])

with c_chart1:
    fig_donut = px.pie(
        names=allocation_labels,
        values=allocation_values,
        hole=0.55,
        title="توزيع الأوزان النسبية والمراكز",
        color_discrete_sequence=['#4facfe', '#00f2fe', '#38ef7d', '#f12711', '#f5af19', '#7f00ff']
    )
    fig_donut.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#0b0c10', width=2)))
    fig_donut.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8', family='Cairo'),
        margin=dict(t=40, b=10, l=10, r=10),
        showlegend=False
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with c_chart2:
    if trade_history:
        df_trades = pd.DataFrame(trade_history)
        fig_bar = px.bar(
            df_trades.tail(7),
            x="symbol",
            y="total_value",
            color="type",
            color_discrete_map={"BUY": "#10b981", "SELL": "#ef4444"},
            title="أحجام أحدث الصفقات المنفذة",
            labels={"symbol": "السهم", "total_value": "القيمة (ج)", "type": "النوع"}
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8', family='Cairo'),
            margin=dict(t=40, b=10, l=10, r=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("لا توجد صفقات منفذة حالياً لعرض المسار المالي.")

# 9. جداول البيانات المتجاوبة
st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-top: 15px;'>📌 المراكز المفتوحة والأسهم المملوكة</h3>", unsafe_allow_html=True)
if holdings_rows:
    df_holdings = pd.DataFrame(holdings_rows)
    st.table(df_holdings)
else:
    st.info("لا توجد أسهم مملوكة حالياً في المحفظة.")

st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-top: 25px;'>📜 سجل العمليات ومبررات الذكاء الاصطناعي</h3>", unsafe_allow_html=True)
if trade_history:
    recent = trade_history[:6]
    table_data = []
    for t in recent:
        time_str = t.get("date", "").split()[-1] if " " in t.get("date", "") else t.get("date", "")
        p_val = float(t.get("price", 0.0))
        s_val = int(t.get("shares", 0))
        tot = float(t.get("total_value", p_val * s_val))
        action_badge = "🟢 شراء" if t.get("type") == "BUY" else "🔴 بيع"
        
        table_data.append({
            "الوقت": time_str,
            "السهم": t.get("symbol", ""),
            "العملية": action_badge,
            "الكمية": f"{s_val:,}",
            "السعر": f"{p_val:.2f} ج",
            "الإجمالي": f"{tot:,.2f} ج",
            "مبرر الذكاء الاصطناعي": t.get("reason", "تنفيذ استراتيجي آلي")
        })
        
    df_trades_table = pd.DataFrame(table_data)
    st.table(df_trades_table)
else:
    st.info("لم يتم تسجيل أي عمليات بعد.")
