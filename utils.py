import os
import sqlite3
import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH")

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成

    # アプリ起動時にSQLite接続しテーブルを作成
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ledger ("
        "session_id TEXT PRIMARY KEY, "
        "amount INTEGER, "
        "currency TEXT, "
        "status TEXT, "
        "created_at TEXT)"
    )
    # ADD: 初期化時に一度だけ走らせる。既存のDB接続を流用。
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions(
        id TEXT PRIMARY KEY,          -- sub_***
        customer_id TEXT,
        price_id TEXT,
        status TEXT,                  -- active/trialing/canceled 等
        current_period_end INTEGER,
        trial_end INTEGER,
        app_user_id TEXT,
        latest_invoice TEXT,
        created_at TEXT
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices(
        id TEXT PRIMARY KEY,          -- in_***
        subscription_id TEXT,         -- sub_***
        status TEXT,                  -- paid/open/void
        amount_due INTEGER,
        currency TEXT,
        created INTEGER
        )""")
    conn.commit()
    conn.close()


# 現在の日時を取得
def now():
    return datetime.datetime.now().isoformat()


# 台帳に追加
def record_ledger(session):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成
    
    session_id = session.get("id")
    amount_total = session.get("amount_total")
    currency = session.get("currency")
    payment_status = session.get("payment_status")
    created = now()
    
    try:
        cursor.execute(
            "INSERT INTO ledger (session_id, amount, currency, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, amount_total, currency, payment_status, created)
        )
        conn.commit()
        print(f" Ledger updated: Session {session_id} recorded.")
    except sqlite3.IntegrityError as e:
        print(f"⚠ Session {session_id} is already recorded in ledger.")
    conn.close()


# 定期課金情報を更新
def upsert_subscription(subscription):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成
    
    customer_id = subscription.get("customer")
    items = subscription.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    status = subscription.get("status")
    current_period_end = subscription.get("current_period_end") 
    trial_end = subscription.get("trial_end")
    app_user_id = subscription.get("metadata").get("app_user_id")
    latest_invoice = subscription.get("latest_invoice")
    created = now()
    
    try:
        cursor.execute("""
            INSERT INTO subscriptions(id, customer_id, price_id, status, current_period_end, trial_end, app_user_id, latest_invoice, created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
            price_id=excluded.price_id,
            status=excluded.status,
            current_period_end=excluded.current_period_end,
            trial_end=excluded.trial_end,
            app_user_id=COALESCE(NULLIF(excluded.app_user_id,''), app_user_id),
            latest_invoice=excluded.latest_invoice
        """, (
            subscription["id"],
            customer_id,
            price_id,
            status,
            current_period_end,
            trial_end,
            app_user_id,
            latest_invoice,
            created
            ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"⚠ Subscription {subscription['id']} is already recorded in subscriptions.")
    conn.close()

# 請求書を更新
def record_invoice(invoice):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成

    subscription_id = invoice.get("subscription")
    status = invoice.get("status")
    amount_due = invoice.get("amount_due")
    currency = invoice.get("currency")
    created = now()
    
    try:
        cursor.execute("""
            INSERT INTO invoices(id, subscription_id, status, amount_due, currency, created)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO NOTHING
        """, (
            invoice["id"],
            subscription_id,
            status,
            amount_due,
            currency,
            created
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"⚠ Invoice {invoice['id']} is already recorded in invoices.")
    conn.close()


# 台帳を取得
def get_ledger():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成

    cursor.execute("SELECT session_id, amount, currency, status, created_at FROM ledger")
    rows = cursor.fetchall()
    conn.close()
    return rows


# 定期課金情報を取得
def get_subscriptions():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
    cursor = conn.cursor() # カーソルオブジェクトを作成

    cursor.execute("SELECT id, customer_id, price_id, status, current_period_end, trial_end, app_user_id, latest_invoice, created_at FROM subscriptions")
    rows = cursor.fetchall()
    conn.close()
    return rows