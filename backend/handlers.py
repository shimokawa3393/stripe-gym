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
        # サブスクリプション作成時は、メタデータからユーザーIDを取得してサブスクリプションを更新
        metadata = webhook_object.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_type = metadata.get("plan_type")
        
        # user_idが空文字列の場合はNoneに変換
        if user_id == "":
            user_id = None
        else:
            user_id = int(user_id) if user_id else None
        
        # サブスクリプションIDを取得
        subscription_id = webhook_object.get("subscription")
        if subscription_id and user_id:
            # サブスクリプションのuser_idを更新
            from models_postgres import get_session, Subscription
            session = get_session()
            try:
                subscription = session.query(Subscription).filter_by(id=subscription_id).first()
                if subscription:
                    subscription.user_id = user_id
                    session.commit()
                    print(f"Updated subscription user_id: {subscription_id} -> {user_id}")
            except Exception as e:
                print(f"Error updating subscription user_id: {e}")
                session.rollback()
            finally:
                session.close()
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
    
    # サブスクリプションを作成/更新
    subscription = upsert_subscription(webhook_object, user_id=user_id)
    
    # user_idがNoneの場合、checkout.session.completedのメタデータから取得を試行
    if not user_id and subscription:
        print(f"User ID not found in subscription metadata, trying to find from checkout session...")
        # サブスクリプションIDからcheckout sessionを検索してuser_idを取得
        try:
            import stripe
            # サブスクリプションのcustomer_idを取得
            customer_id = webhook_object.get("customer")
            if customer_id:
                # 最近のcheckout sessionを検索
                sessions = stripe.checkout.Session.list(
                    customer=customer_id,
                    limit=10
                )
                for session in sessions.data:
                    if session.mode == "subscription" and session.subscription == webhook_object.get("id"):
                        session_metadata = session.metadata or {}
                        session_user_id = session_metadata.get("user_id")
                        if session_user_id and session_user_id != "":
                            user_id = int(session_user_id)
                            # サブスクリプションのuser_idを更新
                            from models_postgres import get_session, Subscription
                            db_session = get_session()
                            try:
                                db_subscription = db_session.query(Subscription).filter_by(id=webhook_object.get("id")).first()
                                if db_subscription:
                                    db_subscription.user_id = user_id
                                    db_session.commit()
                                    print(f"Updated subscription user_id from checkout session: {webhook_object.get('id')} -> {user_id}")
                            except Exception as e:
                                print(f"Error updating subscription user_id from checkout session: {e}")
                                db_session.rollback()
                            finally:
                                db_session.close()
                        break
        except Exception as e:
            print(f"Error searching checkout session for user_id: {e}")
    
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
