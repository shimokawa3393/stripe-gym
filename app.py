import os
import datetime
import sqlite3
import stripe
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify, request

load_dotenv()

app = Flask(__name__)

# デバッグモードを有効化
app.config["DEBUG"] = True


# 環境変数からStripeの公開鍵・秘密鍵を取得
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") # テスト秘密鍵をセット
PUBLIC_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY") # テスト公開鍵（必要ならフロントで使用）
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") # ウェブフックシークレットキー

BASE_URL = os.getenv("BASE_URL")

DB_PATH = os.getenv("DB_PATH")


# アプリ起動時にSQLite接続しテーブルを作成
conn = sqlite3.connect(DB_PATH, check_same_thread=False) # データベース接続
cursor = conn.cursor() # カーソルオブジェクトを作成
cursor.execute(
    "CREATE TABLE IF NOT EXISTS ledger ("
    "session_id TEXT PRIMARY KEY, "
    "amount INTEGER, "
    "currency TEXT, "
    "status TEXT, "
    "created TEXT)"
)
conn.commit()


# ホームページ
@app.route("/")
def index():
    # シンプルなホーム。実際はテンプレートを使ってボタンを配置可能
    return """
        <h1>デモショップ</h1>
        <p><a href="/checkout">テスト商品を購入</a></p>
        <p><a href="/ledger">台帳を表示</a></p>
    """

# 支払いページ
@app.route("/checkout")
def checkout():
    # ドメインURLを組み立て（Dockerの場合ホスト名に注意。ローカルテスト用にlocalhost使用）
    try:
        # StripeのCheckout Sessionを作成
        checkout_session = stripe.checkout.Session.create(
            success_url = f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",    # 支払い成功後に戻るURL
            cancel_url  = f"{BASE_URL}/cancel",     # 支払いキャンセル時に戻るURL
            payment_method_types = ["card"],       # 使用する支払方法
            mode = "payment",                      # 単発の支払いモード
            line_items = [                         # 商品ラインアイテムの指定
                {
                    'price_data': {
                        'currency': 'jpy',
                        'product_data': {'name': 'テスト商品'},
                        'unit_amount': 50,  # 単価50円（通貨の最小単位：50円）
                    },
                    'quantity': 1,
                }
            ]
        )
    except Exception as e:
        return f"Error creating checkout session: {e}", 500

    # Stripeの決済ページURLへリダイレクト
    return redirect(checkout_session.url, code=303)


# 支払い成功後のページ
@app.route("/success")
def success():
    s_id = request.args.get("session_id")
    if not s_id:
        return "session_id missing", 400
    
    session = stripe.checkout.Session.retrieve(s_id, expand=["payment_intent"])
    
    return f"""
        <h1>支払いが完了しました！ありがとうございます。</h1>
        <p>セッションID: {s_id}</p>
        <p>支払い金額: {session.amount_total} {session.currency}</p>
        <p>支払いステータス: {session.payment_status}</p>
        <p>支払い日時: {session.created}</p>
        <button><a href="/">ホームに戻る</a></button>
    """


# 支払いキャンセル後のページ
@app.route("/cancel")
def cancel():
    return """
        <h1>支払いがキャンセルされました。</h1>
        <button><a href="/">ホームに戻る</a></button>
    """


# ウェブフックエンドポイント
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    # Webhookイベントを受け取るエンドポイント
    payload = request.data # 生のリクエストボディ
    sig_header = request.headers.get("Stripe-Signature", "") # 署名ヘッダーの取得
    event = None # イベントオブジェクトの初期化
    
    try:
        # 署名の検証とイベントオブジェクトの取得
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        # 署名検証エラー（偽装やシークレット不一致）
        print("⚠ Webhook signature verification failed.")
        return jsonify({'error': 'invalid signature'}), 400
    except Exception as e:
        # その他エラー（ペイロード不正など）
        print(f"⚠ Webhook error: {e}")
        return jsonify({'error': 'webhook error'}), 400

    # イベントタイプによって処理を分岐
    if event["type"] == "checkout.session.completed":
        print(f"Received event type: {event['type']}")
        return "", 200
        
    session = event["data"]["object"] 
    session_id = session.get("id")
    amount_total = session.get("amount_total") # 合計金額 (支払額)
    currency = session.get("currency")
    payment_status = session.get("payment_status", "") # "paid" 等
        
    # 台帳に追加
    try:
        cursor.execute(
            "INSERT INTO ledger (session_id, amount, currency, status, created) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, amount_total, currency, payment_status, datetime.datetime.now().isoformat())
        )
        conn.commit()
        print(f" Ledger updated: Session {session_id} recorded.")
    except sqlite3.IntegrityError as e:
        print(f"⚠ Session {session_id} is already recorded in ledger.")
        
    # 素早く成功レスポンスを返す
    return "", 200


# 台帳表示ページ
@app.route("/ledger", methods=["GET"])
def show_ledger():
    cursor.execute("SELECT session_id, amount, currency, status, created FROM ledger")
    rows = cursor.fetchall()
    # シンプルにテキストで一覧表示（実際は適切にフォーマットする）
    result = "SessionID, Amount, Currency, Status, Created\n"
    
    for r in rows:
        result += f"{r[0]}, {r[1]}, {r[2]}, {r[3]}, {r[4]}\n"
        
    return "<pre>" + result + "</pre>"


# アプリ起動
if __name__ == "__main__":
    # コンテナ内で実行する際、ホストからアクセス可能にするため0.0.0.0で待機
    app.run(host="0.0.0.0", port=5000)