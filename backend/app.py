"""
Flask アプリケーションのエントリーポイント
"""
import os
import stripe
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from repositories import init_db
from routes import auth_bp, user_bp, payment_bp, webhook_bp

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
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# データベース初期化
init_db()

# Blueprintを登録
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(webhook_bp)


# ヘルスチェックエンドポイント
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "message": "Stripe Gym API is running"}), 200


# アプリ起動
if __name__ == "__main__":
    # コンテナ内で実行する際、ホストからアクセス可能にするため0.0.0.0で待機
    app.run(host="0.0.0.0", port=5000)
