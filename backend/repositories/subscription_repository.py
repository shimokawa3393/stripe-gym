"""
サブスクリプション関連のリポジトリ
"""
import os
import datetime
import logging
from models import Subscription
from .database import get_session

logger = logging.getLogger(__name__)


def upsert_subscription(webhook_object, user_id=None):
    """サブスクリプションを更新"""
    subscription_id = webhook_object.get("id")
    customer_id = webhook_object.get("customer")
    
    items = (webhook_object.get("items") or {}).get("data", [])
    first_item = items[0] if items else {}

    price_id = (first_item.get("price") or {}).get("id")
    status = webhook_object.get("status")
    cancel_at_period_end = webhook_object.get("cancel_at_period_end", False)  # 解約予定フラグ

    # Noneを回避するフォールバック
    current_period_end = (
        webhook_object.get("current_period_end")
        or first_item.get("current_period_end")
        or webhook_object.get("trial_end")
        or webhook_object.get("billing_cycle_anchor")
    )

    trial_end = webhook_object.get("trial_end")
    latest_invoice = webhook_object.get("latest_invoice")

    # Stripeのcreated（epoch）をISO文字列に変換
    created_epoch = webhook_object.get("created")
    created_at = (
        datetime.datetime.fromtimestamp(created_epoch, tz=datetime.timezone.utc).isoformat()
        if created_epoch
        else datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    try:
        session = get_session()
        
        # 既存のサブスクリプションをチェック
        existing_subscription = session.query(Subscription).filter_by(id=subscription_id).first()
        logger.info(f"Checking existing subscription for ID: {subscription_id}, found: {existing_subscription is not None}")
        
        if existing_subscription:
            # 既存のサブスクリプションを更新
            # user_idがNoneでない場合のみ更新（既存のuser_idを保持）
            if user_id is not None:
                existing_subscription.user_id = user_id
            existing_subscription.price_id = price_id
            existing_subscription.status = status
            existing_subscription.current_period_end = current_period_end
            existing_subscription.cancel_at_period_end = cancel_at_period_end
            existing_subscription.trial_end = trial_end
            existing_subscription.latest_invoice = latest_invoice
            logger.info(f"Subscription updated: {existing_subscription.id}")
        else:
            # 新しいサブスクリプションを作成
            subscription_entry = Subscription(
                id=subscription_id,
                user_id=user_id,
                customer_id=customer_id,
                price_id=price_id,
                status=status,
                current_period_end=current_period_end,
                cancel_at_period_end=cancel_at_period_end,
                trial_end=trial_end,
                latest_invoice=latest_invoice,
                created_at=created_at,
            )
            session.add(subscription_entry)
            logger.info(f"Subscription created: {subscription_entry.id}")
            
        session.commit()
        return existing_subscription if existing_subscription else subscription_entry
    except Exception as e:
        logger.error(f"Error recording subscription: {e}")
        session.rollback()
        
        # 重複キーエラーの場合は既存レコードを返す
        if "duplicate key value violates unique constraint" in str(e):
            logger.info(f"Duplicate key error for subscription_id: {subscription_id}, returning existing entry")
            try:
                existing_subscription = session.query(Subscription).filter_by(id=subscription_id).first()
                if existing_subscription:
                    return existing_subscription
            except Exception as query_error:
                logger.error(f"Error querying existing subscription: {query_error}")
        
        raise e
    finally:
        session.close()


def get_subscriptions():
    """サブスクリプションを取得"""
    session = get_session()
    try:
        subscriptions = session.query(Subscription).all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise e
    finally:
        session.close()


def get_user_subscriptions(user_id):
    """ユーザーのサブスクリプション履歴を取得"""
    session = get_session()
    try:
        subscriptions = session.query(Subscription).filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting user subscriptions: {e}")
        raise e
    finally:
        session.close()


def get_plan_name_from_price_id(price_id):
    """price_idからプラン名を取得"""
    premium_price_id = os.getenv("PREMIUM_PRICE_ID", os.getenv("PRICE_ID"))
    standard_price_id = os.getenv("STANDARD_PRICE_ID")
    
    if price_id == premium_price_id:
        return "プレミアムプラン"
    elif price_id == standard_price_id:
        return "スタンダードプラン"
    else:
        return "不明なプラン"
