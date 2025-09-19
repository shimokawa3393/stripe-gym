import os
import stripe
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify, request
from flask_cors import CORS
from models_postgres import init_db, get_ledger, get_subscriptions
from handlers import handle_checkout_completed, handle_invoice_paid, handle_invoice_payment_failed, handle_subscription_created, handle_subscription_updated

load_dotenv()

app = Flask(__name__)

# デバッグモードを有効化
app.config["DEBUG"] = True

# CORS設定を追加
CORS(app, 
     origins=["http://localhost:3000", "http://localhost:8080", "http://localhost", "http://127.0.0.1:3000", "http://127.0.0.1:8080", "http://127.0.0.1"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True)


# 環境変数からStripeの公開鍵・秘密鍵を取得
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") # テスト秘密鍵をセット
PUBLIC_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY") # テスト公開鍵（必要ならフロントで使用）
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") # ウェブフックシークレットキー
PRICE_ID = os.getenv("PRICE_ID")

BASE_URL = os.getenv("BASE_URL")

init_db()

# ホームページ
@app.route("/")
def index():
    # シンプルなホーム。実際はテンプレートを使ってボタンを配置可能
    return """
        <h1>デモショップ</h1>
        <p><a href="/checkout">テスト商品を購入</a></p>
        <p><a href="/subscription">テストサブスクを開始</a></p>
        <p><a href="/ledger">購入履歴を表示</a></p>
        <p><a href="/subscriptions">サブスクリプションを表示</a></p>
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


# 定期課金ページ
@app.route("/subscription", methods=["POST"])
def subscription():
    try:
        # Checkout で “定期課金” を開始する
        subscription_session = stripe.checkout.Session.create(
            success_url=f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/cancel",
            mode="subscription",
            payment_method_types=["card"],                       # 支払い方法をクレジットカードに限定
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            # subscription_data={"trial_period_days": 7},          # トライアル期間を7日に設定
            allow_promotion_codes=True,                          # プロモーションコードの使用を許可
        )
    except Exception as e:
        return f"Error creating subscription session: {e}", 500
    
    # Stripeの決済ページURLへリダイレクト
    return redirect(subscription_session.url, code=303)


# API エンドポイント（フロントエンド用）
@app.route("/api/subscription", methods=["POST"])
def subscription_api():
    try:
        subscription_session = stripe.checkout.Session.create(
            success_url="http://localhost:8080/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:8080/cancel",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            allow_promotion_codes=True,
        )
        return jsonify({"id": subscription_session.id})   # ← JSONで返す
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 支払い成功後のページ
@app.route("/success")
def success():
    session_id = request.args.get("session_id")
    if not session_id:
        return "session_id missing", 400
    
    session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
    
    return f"""
        <h1>支払いが完了しました！ありがとうございます。</h1>
        <p>支払い金額: {session.amount_total} {session.currency}</p>
        <p>支払いステータス: {session.payment_status}</p>
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

    event_type = event.get("type")
    webhook_object = event["data"]["object"]

    # イベントタイプによって処理を分岐
    if event_type == "checkout.session.completed":
        handle_checkout_completed(webhook_object)
    elif event_type == "invoice.paid":
        handle_invoice_paid(webhook_object)
    elif event_type == "invoice.payment_failed":
        handle_invoice_payment_failed(webhook_object)
    elif event_type == "customer.subscription.created":
        handle_subscription_created(webhook_object)
    elif event_type == "customer.subscription.updated":
        handle_subscription_updated(webhook_object)
    else:
        print(f"⚠ Unhandled event type: {event_type}")
        return "", 200
        
    # 素早く成功レスポンスを返す
    return "", 200  


# 台帳表示ページ
@app.route("/ledger", methods=["GET"])
def show_ledger():
    rows = get_ledger()
    # シンプルにテキストで一覧表示（実際は適切にフォーマットする）
    result = "SessionID | Amount | Currency | Status | Created\n"
    
    for r in rows:
        result += f"{r.session_id}, {r.amount}, {r.currency}, {r.status}, {r.created_at}\n"
        
    return "<pre>" + result + "</pre>"


# 定期課金情報表示ページ
@app.route("/subscriptions", methods=["GET"])
def show_subscriptions():
    rows = get_subscriptions()
    result = "SubscriptionID | CustomerID | PriceID | Status | CurrentPeriodEnd | TrialEnd | LatestInvoice | Created\n"
    for r in rows:
        result += f"{r.id}, {r.customer_id}, {r.price_id}, {r.status}, {r.current_period_end}, {r.trial_end}, {r.latest_invoice}, {r.created_at}\n"
    return "<pre>" + result + "</pre>"


# ヘルスチェックエンドポイント
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "message": "Stripe Gym API is running"}), 200

# API エンドポイント（フロントエンド用）
@app.route("/api/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.get_json()
        price_id = data.get("price_id", PRICE_ID)
        
        checkout_session = stripe.checkout.Session.create(
            success_url=f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/cancel",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
        )
        
        return jsonify({"id": checkout_session.id}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# アプリ起動
if __name__ == "__main__":
    # コンテナ内で実行する際、ホストからアクセス可能にするため0.0.0.0で待機
    app.run(host="0.0.0.0", port=5000)