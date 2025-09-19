import os
import datetime
import logging
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    CheckConstraint,
    create_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Ledger(Base):
    __tablename__ = "ledger"
    session_id = Column(String, primary_key=True)  # Stripeのsession IDを主キーに
    amount = Column(Numeric(10, 2), CheckConstraint("amount >= 0"))
    currency = Column(String(3))
    status = Column(String)  # Stripeの実際のステータス値に合わせて制約を緩和
    created_at = Column(String)  # ISO文字列で統一


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)  # Stripeのsubscription IDを主キーに
    customer_id = Column(String)
    price_id = Column(String)
    status = Column(String)
    current_period_end = Column(Integer)
    trial_end = Column(Integer)
    latest_invoice = Column(String)
    created_at = Column(String)  # ISO文字列で統一


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True)  # Stripeのinvoice IDを主キーに
    subscription_id = Column(String)  # Stripeのsubscription ID
    status = Column(String)  # 請求書ステータス（paidなど）
    amount_due = Column(Numeric(10, 2))
    currency = Column(String(3))
    created = Column(Integer)  # Unix timestampで統一


# データベースを初期化
def init_db():
    global engine
    engine = create_engine(os.getenv("DATABASE_URL"))
    Base.metadata.create_all(engine)


# セッションを取得
def get_session():
    return Session(engine)


# 現在の日時を取得
def now():
    return datetime.datetime.now().isoformat()


# 支払い台帳を記録
def record_ledger(webhook_object):
    session_id = webhook_object.get("id")
    amount_total = webhook_object.get("amount_total")
    currency = webhook_object.get("currency")
    payment_status = webhook_object.get("payment_status")

    # Stripeのcreated（epoch）をISO文字列に変換
    created_epoch = webhook_object.get("created")
    created_at = (
        datetime.datetime.fromtimestamp(created_epoch, tz=datetime.timezone.utc).isoformat()
        if created_epoch
        else datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    
    try:
        session = get_session()

        ledger_entry = Ledger(
            session_id=session_id,
            amount=amount_total,
            currency=currency,
            status=payment_status,
            created_at=created_at,
        )
        session.add(ledger_entry)
        session.commit()
        logger.info(f"Ledger recorded: {ledger_entry.session_id}")
    except Exception as e:
        logger.error(f"Error recording ledger: {e}")
        session.rollback()
        raise e
    finally:
        session.close()


# サブスクリプションを更新
def upsert_subscription(webhook_object):
    subscription_id = webhook_object.get("id")
    customer_id = webhook_object.get("customer")
    
    items = (webhook_object.get("items") or {}).get("data", [])
    first_item = items[0] if items else {}

    price_id = (first_item.get("price") or {}).get("id")
    status = webhook_object.get("status")

    # Noneを回避するフォールバック（優先: top-level -> item -> trial_end -> billing_cycle_anchor）
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
        
        # 既存のサブスクリプションをチェック（Stripe IDで検索）
        existing_subscription = session.query(Subscription).filter_by(id=subscription_id).first()
        
        if existing_subscription:
            # 既存のサブスクリプションを更新
            existing_subscription.price_id = price_id
            existing_subscription.status = status
            existing_subscription.current_period_end = current_period_end
            existing_subscription.trial_end = trial_end
            existing_subscription.latest_invoice = latest_invoice
            logger.info(f"Subscription updated: {existing_subscription.id}")
        else:
            # 新しいサブスクリプションを作成
            subscription_entry = Subscription(
                id=subscription_id,
                customer_id=customer_id,
                price_id=price_id,
                status=status,
                current_period_end=current_period_end,
                trial_end=trial_end,
                latest_invoice=latest_invoice,
                created_at=created_at,
            )
            session.add(subscription_entry)
            logger.info(f"Subscription created: {subscription_entry.id}")
            
        session.commit()
    except Exception as e:
        logger.error(f"Error recording subscription: {e}")
        session.rollback()
        raise e
    finally:
        session.close()


# 請求書を記録
def record_invoice(webhook_object):
    invoice_id = webhook_object.get("id")
    subscription_id = webhook_object.get("subscription")
    status = webhook_object.get("status")
    amount_due = webhook_object.get("amount_due")
    currency = webhook_object.get("currency")
    created = webhook_object.get("created")  # Unix timestamp

    session = get_session()
    try:
        # 既存の請求書をチェック
        existing_invoice = session.query(Invoice).filter_by(id=invoice_id).first()
        
        if not existing_invoice:
            invoice_entry = Invoice(
                id=invoice_id,
                subscription_id=subscription_id,
                status=status,
                amount_due=amount_due,
                currency=currency,
                created=created,
            )
            session.add(invoice_entry)
            logger.info(f"Invoice recorded: {invoice_entry.id}")
        else:
            logger.info(f"Invoice already exists: {invoice_id}")
            
        session.commit()
    except Exception as e:
        logger.error(f"Error recording invoice: {e}")
        session.rollback()
        raise e
    finally:
        session.close()


# 支払い台帳を取得
def get_ledger():
    session = get_session()
    try:
        ledger = session.query(Ledger).all()
        return ledger
    except Exception as e:
        logger.error(f"Error getting ledger: {e}")
        raise e
    finally:
        session.close()


# サブスクリプションを取得
def get_subscriptions():
    session = get_session()
    try:
        subscriptions = session.query(Subscription).all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise e
    finally:
        session.close()
