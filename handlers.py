from models import record_ledger, record_invoice, upsert_subscription

# Webhookイベントハンドラー関数
def handle_checkout_completed(session):
    """チェックアウト完了時の処理"""
    if session.get("mode") == "payment":
        record_ledger(session)  # 単発購入の台帳記録
    elif session.get("mode") == "subscription":
        # ここではあえて台帳は作らず subscription.created / invoice.paid に任せてもOK
        pass
    record_invoice(session)
    return "", 200


def handle_invoice_paid(invoice):
    """請求書支払い完了時の処理"""
    print(f"✅ Invoice paid: {invoice.get('id')}")
    record_invoice(invoice)
    return "", 200


def handle_subscription_created(subscription):
    """サブスクリプション作成時の処理"""
    print(f"✅ Subscription created: {subscription.get('id')}")
    upsert_subscription(subscription)
    return "", 200


def handle_subscription_updated(subscription):
    """サブスクリプション更新時の処理"""
    print(f"✅ Subscription updated: {subscription.get('id')}")
    upsert_subscription(subscription)
    return "", 200


def handle_invoice_payment_failed(invoice):
    """請求書支払い失敗時の処 理"""
    print(f"❌ Invoice payment failed: {invoice.get('id')}")
    return "", 200
