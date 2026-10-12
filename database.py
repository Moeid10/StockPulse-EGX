import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "stockpulse.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # جدول المحافظ
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            username TEXT PRIMARY KEY,
            cash REAL NOT NULL DEFAULT 100000.0,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)
    
    # جدول الأسهم المملوكة (Holdings)
    c.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            UNIQUE(username, symbol),
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)
    
    # جدول سجل الصفقات
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            shares INTEGER NOT NULL,
            total_value REAL NOT NULL DEFAULT 0.0,
            reason TEXT DEFAULT '',
            date TEXT NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)
    
    # فحص تلقائي للأعمدة وتحديثها في حال كانت القاعدة قديمة
    c.execute("PRAGMA table_info(trades)")
    cols = [col[1] for col in c.fetchall()]
    if "total_value" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN total_value REAL NOT NULL DEFAULT 0.0")
    if "reason" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN reason TEXT DEFAULT ''")
    
    conn.commit()
    conn.close()

def register_user(username: str, password: str):
    init_db()
    username = username.strip()
    if not username or not password:
        return False, "اسم المستخدم وكلمة المرور مطلوبان."
    
    conn = get_db()
    c = conn.cursor()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pwd_hash = hash_password(password)
        c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)", 
                  (username, pwd_hash, now))
        c.execute("INSERT INTO portfolios (username, cash) VALUES (?, 100000.0)", (username,))
        conn.commit()
        return True, "تم إنشاء الحساب بنجاح ورصيدك 100,000 ج جاهز!"
    except sqlite3.IntegrityError:
        return False, "اسم المستخدم مسجل مسبقاً، يرجى اختيار اسم آخر."
    finally:
        conn.close()

def verify_user(username: str, password: str) -> bool:
    init_db()
    username = username.strip()
    conn = get_db()
    c = conn.cursor()
    pwd_hash = hash_password(password)
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row and row["password_hash"] == pwd_hash:
        return True
    return False

def get_user_portfolio(username: str):
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT cash FROM portfolios WHERE username = ?", (username,))
    p_row = c.fetchone()
    cash = float(p_row["cash"]) if p_row else 100000.0
    
    c.execute("SELECT symbol, shares, avg_price FROM holdings WHERE username = ? AND shares > 0", (username,))
    h_rows = c.fetchall()
    holdings = {r["symbol"]: {"shares": int(r["shares"]), "avg_price": float(r["avg_price"])} for r in h_rows}
    
    c.execute("SELECT * FROM trades WHERE username = ? ORDER BY id DESC", (username,))
    t_rows = c.fetchall()
    
    trades = []
    for t in t_rows:
        td = dict(t)
        # ضمان توافق القيم في حال عدم وجودها
        if "total_value" not in td or td["total_value"] is None:
            td["total_value"] = round(float(td.get("price", 0.0)) * int(td.get("shares", 0)), 2)
        if "reason" not in td or td["reason"] is None:
            td["reason"] = "تنفيذ استراتيجي آلي"
        trades.append(td)
    
    conn.close()
    return {
        "cash": cash,
        "holdings": holdings,
        "trade_history": trades
    }

def execute_user_trade(username: str, symbol: str, trade_type: str, price: float, shares: int, reason: str = ""):
    init_db()
    if shares <= 0 or price <= 0:
        return False, "الكمية والسعر يجب أن يكونا أكبر من الصفر."
    
    total_cost = round(price * shares, 2)
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("SELECT cash FROM portfolios WHERE username = ?", (username,))
        p_row = c.fetchone()
        current_cash = float(p_row["cash"]) if p_row else 100000.0
        
        c.execute("SELECT shares, avg_price FROM holdings WHERE username = ? AND symbol = ?", (username, symbol))
        h_row = c.fetchone()
        curr_shares = int(h_row["shares"]) if h_row else 0
        curr_avg = float(h_row["avg_price"]) if h_row else 0.0
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if trade_type.upper() == "BUY":
            if current_cash < total_cost:
                return False, f"السيولة النقدية غير كافية ({current_cash:,.2f} ج)."
            
            new_cash = current_cash - total_cost
            new_shares = curr_shares + shares
            new_avg = round(((curr_shares * curr_avg) + total_cost) / new_shares, 2)
            
            c.execute("UPDATE portfolios SET cash = ? WHERE username = ?", (new_cash, username))
            c.execute("""
                INSERT INTO holdings (username, symbol, shares, avg_price) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username, symbol) DO UPDATE SET shares = ?, avg_price = ?
            """, (username, symbol, new_shares, new_avg, new_shares, new_avg))
            
            c.execute("""
                INSERT INTO trades (username, symbol, type, price, shares, total_value, reason, date)
                VALUES (?, ?, 'BUY', ?, ?, ?, ?, ?)
            """, (username, symbol, price, shares, total_cost, reason, now))
            
            conn.commit()
            return True, f"تم شراء {shares} سهم من {symbol} بنجاح."
            
        elif trade_type.upper() == "SELL":
            if curr_shares < shares:
                return False, f"لا تملك كمية كافية للبيع (المتاح: {curr_shares} سهم)."
            
            new_cash = current_cash + total_cost
            new_shares = curr_shares - shares
            
            c.execute("UPDATE portfolios SET cash = ? WHERE username = ?", (new_cash, username))
            if new_shares == 0:
                c.execute("DELETE FROM holdings WHERE username = ? AND symbol = ?", (username, symbol))
            else:
                c.execute("UPDATE holdings SET shares = ? WHERE username = ? AND symbol = ?", (new_shares, username, symbol))
                
            c.execute("""
                INSERT INTO trades (username, symbol, type, price, shares, total_value, reason, date)
                VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?)
            """, (username, symbol, price, shares, total_cost, reason, now))
            
            conn.commit()
            return True, f"تم بيع {shares} سهم من {symbol} بنجاح."
            
        else:
            return False, "نوع العملية غير صالح."
            
    except Exception as e:
        conn.rollback()
        return False, f"خطأ في قاعدة البيانات: {str(e)}"
    finally:
        conn.close()

def panic_liquidate_user(username: str, market_prices: dict):
    init_db()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT symbol, shares FROM holdings WHERE username = ? AND shares > 0", (username,))
        holdings = c.fetchall()
        if not holdings:
            return False, "المحفظة خالية بالفعل من أي أسهم."
        
        recovered_cash = 0.0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for h in holdings:
            sym = h["symbol"]
            qty = int(h["shares"])
            cur_price = market_prices.get(sym, 10.0)
            val = round(cur_price * qty, 2)
            recovered_cash += val
            
            c.execute("""
                INSERT INTO trades (username, symbol, type, price, shares, total_value, reason, date)
                VALUES (?, ?, 'SELL', ?, ?, ?, '🚨 تسييل طارئ كامل (Panic Liquidation)', ?)
            """, (username, sym, cur_price, qty, val, now))
            
        c.execute("DELETE FROM holdings WHERE username = ?", (username,))
        c.execute("UPDATE portfolios SET cash = cash + ? WHERE username = ?", (recovered_cash, username))
        conn.commit()
        return True, f"تم تسييل جميع المراكز واسترجاع {recovered_cash:,.2f} ج كاش بنجاح!"
    except Exception as e:
        conn.rollback()
        return False, f"خطأ أثناء التسييل: {str(e)}"
    finally:
        conn.close()

def get_all_users_summary():
    init_db()
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT u.username, u.created_at, IFNULL(p.cash, 100000.0) as cash 
        FROM users u 
        LEFT JOIN portfolios p ON u.username = p.username
        ORDER BY u.created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

init_db()
