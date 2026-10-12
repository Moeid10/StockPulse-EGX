import sqlite3
import hashlib
from datetime import datetime

DB_FILE = "stockpulse.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)
    # جدول محافظ المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            username TEXT PRIMARY KEY,
            cash REAL NOT NULL DEFAULT 100000.0,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    # جدول المراكز المفتوحة (الأسهم المملوكة)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            UNIQUE(username, symbol),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    # جدول سجل الصفقات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            shares INTEGER NOT NULL,
            price REAL NOT NULL,
            total_value REAL NOT NULL,
            reason TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    conn.commit()

    # إنشاء مستخدم أدمن افتراضي لو غير موجود
    default_admin = "admin"
    default_pass = hashlib.sha256("123456".encode("utf-8")).hexdigest()
    cursor.execute("SELECT username FROM users WHERE username = ?", (default_admin,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (default_admin, default_pass, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        cursor.execute("INSERT INTO portfolios VALUES (?, ?)", (default_admin, 100000.0))
        conn.commit()
    conn.close()

init_db()

def verify_user(username, password):
    h = hashlib.sha256(password.encode("utf-8")).hexdigest()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row and row["password_hash"] == h

def register_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False, "اسم المستخدم مسجل بالفعل."
    
    h = hashlib.sha256(password.encode("utf-8")).hexdigest()
    c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, h, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("INSERT INTO portfolios VALUES (?, ?)", (username, 100000.0))
    conn.commit()
    conn.close()
    return True, "تم إنشاء الحساب بنجاح!"

def get_user_portfolio(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT cash FROM portfolios WHERE username = ?", (username,))
    p_row = c.fetchone()
    cash = p_row["cash"] if p_row else 100000.0

    c.execute("SELECT symbol, shares, avg_price FROM holdings WHERE username = ?", (username,))
    holdings_rows = c.fetchall()
    holdings = {row["symbol"]: {"shares": row["shares"], "avg_price": row["avg_price"]} for row in holdings_rows}

    c.execute("SELECT date, symbol, trade_type as type, shares, price, total_value, reason FROM trades WHERE username = ? ORDER BY id DESC", (username,))
    trades = [dict(row) for row in c.fetchall()]
    conn.close()

    return {"cash": cash, "holdings": holdings, "trade_history": trades}

def execute_user_trade(username, symbol, trade_type, price, shares=None, reason="تنفيذ آلي"):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT cash FROM portfolios WHERE username = ?", (username,))
    cash = c.fetchone()["cash"]

    c.execute("SELECT shares, avg_price FROM holdings WHERE username = ? AND symbol = ?", (username, symbol))
    h_row = c.fetchone()
    owned_shares = h_row["shares"] if h_row else 0
    owned_avg = h_row["avg_price"] if h_row else 0.0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if trade_type.upper() == "BUY":
        if not shares or shares <= 0:
            conn.close()
            return False, "الكمية المطلوبة غير صحيحة."
        total_cost = shares * price
        if cash < total_cost:
            conn.close()
            return False, f"السيولة غير كافية. المطلوب: {total_cost:,.2f} ج | المتاح: {cash:,.2f} ج"

        new_cash = cash - total_cost
        new_shares = owned_shares + shares
        new_avg = ((owned_shares * owned_avg) + total_cost) / new_shares

        c.execute("UPDATE portfolios SET cash = ? WHERE username = ?", (new_cash, username))
        c.execute("""
            INSERT INTO holdings (username, symbol, shares, avg_price) VALUES (?, ?, ?, ?)
            ON CONFLICT(username, symbol) DO UPDATE SET shares = ?, avg_price = ?
        """, (username, symbol, new_shares, new_avg, new_shares, new_avg))
        
        c.execute("INSERT INTO trades (username, date, symbol, trade_type, shares, price, total_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, now_str, symbol, "BUY", shares, price, total_cost, reason))
        conn.commit()
        conn.close()
        return True, f"تم شراء {shares} سهم من {symbol} بسعر {price:.2f} ج"

    elif trade_type.upper() == "SELL":
        sell_shares = shares if (shares and shares > 0) else owned_shares
        if owned_shares <= 0 or sell_shares > owned_shares:
            conn.close()
            return False, f"لا توجد كمية كافية للبيع. تملك: {owned_shares}"

        total_gain = sell_shares * price
        new_cash = cash + total_gain
        remaining_shares = owned_shares - sell_shares

        c.execute("UPDATE portfolios SET cash = ? WHERE username = ?", (new_cash, username))
        if remaining_shares > 0:
            c.execute("UPDATE holdings SET shares = ? WHERE username = ? AND symbol = ?", (remaining_shares, username, symbol))
        else:
            c.execute("DELETE FROM holdings WHERE username = ? AND symbol = ?", (username, symbol))

        c.execute("INSERT INTO trades (username, date, symbol, trade_type, shares, price, total_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (username, now_str, symbol, "SELL", sell_shares, price, total_gain, reason))
        conn.commit()
        conn.close()
        return True, f"تم بيع {sell_shares} سهم من {symbol} بسعر {price:.2f} ج"

    conn.close()
    return False, "نوع العملية غير معروف."

def panic_liquidate_user(username, market_prices):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT symbol, shares FROM holdings WHERE username = ?", (username,))
    holdings = c.fetchall()
    if not holdings:
        conn.close()
        return False, "المحفظة لا تحتوي على أي مراكز لتسييلها."

    for h in holdings:
        sym = h["symbol"]
        shares = h["shares"]
        price = market_prices.get(sym, 10.0)
        execute_user_trade(username, sym, "SELL", price, shares=shares, reason="🚨 تسييل طوارئ شامل للمحفظة")
    conn.close()
    return True, "تم تسييل كافة المراكز وتحويلها إلى سيولة نقدية."
