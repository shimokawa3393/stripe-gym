from models_postgres import record_ledger, record_invoice, upsert_subscription

# Webhookイベントハンドラー関数
def handle_checkout_completed(webhook_object):
    """チェックアウト完了時の処理"""
    if webhook_object.get("mode") == "payment":
        # メタデータからユーザーIDと商品名を取得
        metadata = webhook_object.get("metadata", {})
        user_id = metadata.get("user_id")
        product_name = metadata.get("product_name")
        
        # user_idが空文字列の場合はNoneに変換
        if user_id == "":
            user_id = None
        else:
            user_id = int(user_id) if user_id else None
            
        record_ledger(webhook_object, user_id=user_id, product_name=product_name)  # 単発購入の台帳記録
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
    
    # メタデータからユーザーIDと商品名を取得
    metadata = webhook_object.get("metadata", {})
    user_id = metadata.get("user_id")
    print(f"Subscription metadata: {metadata}")
    print(f"Extracted user_id: {user_id}")
    
    # user_idが空文字列の場合はNoneに変換
    if user_id == "":
        user_id = None
    else:
        user_id = int(user_id) if user_id else None
    
    upsert_subscription(webhook_object, user_id=user_id)
    return "", 200


def handle_subscription_updated(webhook_object):
    """サブスクリプション更新時の処理"""
    print(f"✅ Subscription updated: {webhook_object.get('id')}")
    
    # メタデータからユーザーIDと商品名を取得
    metadata = webhook_object.get("metadata", {})
    user_id = metadata.get("user_id")
    
    # user_idが空文字列の場合はNoneに変換
    if user_id == "":
        user_id = None
    else:
        user_id = int(user_id) if user_id else None
    
    upsert_subscription(webhook_object, user_id=user_id)
    return "", 200


def handle_invoice_payment_failed(webhook_object):
    """請求書支払い失敗時の処 理"""
    print(f"❌ Invoice payment failed: {webhook_object.get('id')}")
    return "", 200
