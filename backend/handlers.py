from models_postgres import record_ledger, record_invoice, upsert_subscription

# Webhookイベントハンドラー関数
def handle_checkout_completed(webhook_object):
    """チェックアウト完了時の処理"""
    if webhook_object.get("mode") == "payment":
        record_ledger(webhook_object)  # 単発購入の台帳記録
    elif webhook_object.get("mode") == "subscription":
        # ここではあえて台帳は作らず subscription.created / invoice.paid に任せてもOK
        pass
    record_invoice(webhook_object)
    return "", 200


def handle_invoice_paid(webhook_object):
    """請求書支払い完了時の処理"""
    print(f"✅ Invoice paid: {webhook_object.get('id')}")
    record_invoice(webhook_object)
    return "", 200


def handle_subscription_created(webhook_object):
    """サブスクリプション作成時の処理"""
    print(f"✅ Subscription created: {webhook_object.get('id')}")
    upsert_subscription(webhook_object)
    return "", 200


def handle_subscription_updated(webhook_object):
    """サブスクリプション更新時の処理"""
    print(f"✅ Subscription updated: {webhook_object.get('id')}")
    upsert_subscription(webhook_object)
    return "", 200


def handle_invoice_payment_failed(webhook_object):
    """請求書支払い失敗時の処 理"""
    print(f"❌ Invoice payment failed: {webhook_object.get('id')}")
    return "", 200
