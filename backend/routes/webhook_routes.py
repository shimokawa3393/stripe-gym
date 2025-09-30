"""
Webhook関連のルート
"""
from flask import Blueprint, request, jsonify
import os
import stripe
from handlers import (
    handle_checkout_completed,
    handle_invoice_paid,
    handle_invoice_payment_failed,
    handle_subscription_created,
    handle_subscription_updated
)

webhook_bp = Blueprint('webhook', __name__)

WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@webhook_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """ウェブフックエンドポイント"""
    payload = request.data  # 生のリクエストボディ
    sig_header = request.headers.get("Stripe-Signature", "")  # 署名ヘッダーの取得
    event = None  # イベントオブジェクトの初期化
    
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
