import os
import stripe
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify, request
from flask_cors import CORS
from models_postgres import init_db, get_ledger, get_subscriptions, create_user, hash_password, authenticate_user, create_session, logout_user, validate_session
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


# オリジナルプロテイン購入ページ
# API エンドポイント（フロントエンド用）
@app.route("/api/checkout", methods=["POST"])
def checkout_api():
    # ドメインURLを組み立て（Dockerの場合ホスト名に注意。ローカルテスト用にlocalhost使用）
    try:
        # StripeのCheckout Sessionを作成
        checkout_session = stripe.checkout.Session.create(
            success_url = f"{BASE_URL}/success-checkout?session_id={{CHECKOUT_SESSION_ID}}",    # 支払い成功後に戻るURL
            cancel_url  = f"{BASE_URL}/cancel",     # 支払いキャンセル時に戻るURL
            payment_method_types = ["card"],       # 使用する支払方法
            mode = "payment",                      # 単発の支払いモード
            line_items = [                         # 商品ラインアイテムの指定
                {
                    'price_data': {
                        'currency': 'jpy',
                        'product_data': {'name': 'オリジナルプロテイン'},
                        'unit_amount': 4980,  # 単価50円（通貨の最小単位：50円）
                    },
                    'quantity': 1,
                }
            ]
        )
        return jsonify({"id": checkout_session.id})   # ← JSONで返す
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# サブスクリプション課金ページ
# API エンドポイント（フロントエンド用）
@app.route("/api/subscription", methods=["POST"])
def subscription_api():
    try:
        subscription_session = stripe.checkout.Session.create(
            success_url=f"{BASE_URL}/success-subscription?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/cancel",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            allow_promotion_codes=True,
        )
        return jsonify({"id": subscription_session.id})   # ← JSONで返す
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ユーザー登録API
@app.route("/api/register", methods=["POST"])
def register_api():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        phone = data.get("phone")
        birthdate = data.get("birthdate")
        terms_accepted = data.get("terms", False)
        privacy_accepted = data.get("privacy", False)
        
        # 必須項目のチェック
        if not email or not password or not name:
            return jsonify({"error": "メールアドレス、パスワード、お名前は必須です"}), 400
        
        # 利用規約とプライバシーポリシーの同意チェック
        if not terms_accepted or not privacy_accepted:
            return jsonify({"error": "利用規約とプライバシーポリシーに同意してください"}), 400
        
        # パスワードの長さチェック
        if len(password) < 8:
            return jsonify({"error": "パスワードは8文字以上で入力してください"}), 400
        
        # パスワードをハッシュ化
        password_hash = hash_password(password)
        
        # ユーザーを作成
        user = create_user(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            birthdate=birthdate,
            terms_accepted=terms_accepted,
            privacy_accepted=privacy_accepted
        )
        
        # セッションを作成
        session_token = create_session(user.id)
        
        return jsonify({
            "success": True,
            "message": "会員登録が完了しました",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            },
            "session_token": session_token
        }), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"登録処理中にエラーが発生しました: {str(e)}"}), 500


# ログインAPI
@app.route("/api/login", methods=["POST"])
def login_api():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"error": "メールアドレスとパスワードが必要です"}), 400
        
        # ユーザーを認証
        user = authenticate_user(email, password)
        if not user:
            return jsonify({"error": "メールアドレスまたはパスワードが正しくありません"}), 401
        
        # セッションを作成
        session_token = create_session(user.id)
        
        return jsonify({
            "success": True,
            "message": "ログインが完了しました",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            },
            "session_token": session_token
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"ログイン処理中にエラーが発生しました: {str(e)}"}), 500


# ログアウトAPI
@app.route("/api/logout", methods=["POST"])
def logout_api():
    try:
        data = request.get_json()
        session_token = data.get("session_token")
        
        if not session_token:
            return jsonify({"error": "セッショントークンが必要です"}), 400
        
        # セッションを検証
        user_id = validate_session(session_token)
        if not user_id:
            return jsonify({"error": "無効なセッションです"}), 401
        
        # ログアウト処理
        success = logout_user(session_token)
        
        if success:
            return jsonify({
                "success": True,
                "message": "ログアウトが完了しました"
            }), 200
        else:
            return jsonify({"error": "ログアウトに失敗しました"}), 500
        
    except Exception as e:
        return jsonify({"error": f"ログアウト処理中にエラーが発生しました: {str(e)}"}), 500


# セッション検証API
@app.route("/api/verify-session", methods=["POST"])
def verify_session_api():
    try:
        data = request.get_json()
        session_token = data.get("session_token")
        
        if not session_token:
            return jsonify({"error": "セッショントークンが必要です"}), 400
        
        # セッションを検証
        user_id = validate_session(session_token)
        if not user_id:
            return jsonify({"error": "無効なセッションです"}), 401
        
        return jsonify({
            "success": True,
            "message": "セッションが有効です",
            "user_id": user_id
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"セッション検証中にエラーが発生しました: {str(e)}"}), 500


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


# アプリ起動
if __name__ == "__main__":
    # コンテナ内で実行する際、ホストからアクセス可能にするため0.0.0.0で待機
    app.run(host="0.0.0.0", port=5000)