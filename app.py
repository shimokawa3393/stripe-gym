import os
import stripe
from dotenv import load_dotenv
from flask import Flask, redirect

load_dotenv()

app = Flask(__name__)

# 環境変数からStripeの公開鍵・秘密鍵を取得
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") # テスト秘密鍵をセット
PUBLIC_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY") # テスト公開鍵（必要ならフロントで使用）

@app.route("/")
def index():
    # シンプルなホーム。実際はテンプレートを使ってボタンを配置可能
    return '<h1>デモショップ</h1><p><a href="/checkout">テスト商品を購入</a></p>'

@app.route("/checkout")
def checkout():
    # ドメインURLを組み立て（Dockerの場合ホスト名に注意。ローカルテスト用にlocalhost使用）
    base_url = "http://localhost:5001/"
    try:
        # StripeのCheckout Sessionを作成
        checkout_session = stripe.checkout.Session.create(
            success_url = base_url + "success",    # 支払い成功後に戻るURL
            cancel_url  = base_url + "cancel",     # 支払いキャンセル時に戻るURL
            payment_method_types = ["card"],       # 使用する支払方法
            mode = "payment",                      # 単発の支払いモード
            line_items = [                         # 商品ラインアイテムの指定
                {
                    'price_data': {
                        'currency': 'jpy',
                        'product_data': {'name': 'テスト商品'},
                        'unit_amount': 5000,  # 単価50円（通貨の最小単位：50円を100倍の50*100=5000で指定）
                    },
                    'quantity': 1,
                }
            ]
        )
    except Exception as e:
        return f"Error creating checkout session: {e}", 500

    # Stripeの決済ページURLへリダイレクト
    return redirect(checkout_session.url, code=303)

@app.route("/success")
def success():
    return """
        <h1>支払いが完了しました！ありがとうございます。</h1>
        <button><a href="/">ホームに戻る</a></button>
    """

@app.route("/cancel")
def cancel():
    return """
        <h1>支払いがキャンセルされました。</h1>
        <button><a href="/">ホームに戻る</a></button>
    """

if __name__ == "__main__":
    # コンテナ内で実行する際、ホストからアクセス可能にするため0.0.0.0で待機
    app.run(host="0.0.0.0", port=5000)