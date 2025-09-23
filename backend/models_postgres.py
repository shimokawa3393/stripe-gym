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
    Boolean,
    Date,
    create_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ユーザー
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    birthdate = Column(Date)
    terms_accepted = Column(Boolean, default=False)
    privacy_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)


# 支払い台帳
class Ledger(Base):
    __tablename__ = "ledger"
    session_id = Column(String, primary_key=True)  # Stripeのsession IDを主キーに
    user_id = Column(Integer)  # ユーザーID（外部キー）
    amount = Column(Numeric(10, 2), CheckConstraint("amount >= 0"))
    currency = Column(String(3))
    status = Column(String)  # Stripeの実際のステータス値に合わせて制約を緩和
    product_name = Column(String(255))  # 商品名
    created_at = Column(String)  # ISO文字列で統一


# サブスクリプション
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)  # Stripeのsubscription IDを主キーに
    user_id = Column(Integer)  # ユーザーID（外部キー）
    customer_id = Column(String)
    price_id = Column(String)
    status = Column(String)
    current_period_end = Column(Integer)
    trial_end = Column(Integer)
    latest_invoice = Column(String)
    created_at = Column(String)  # ISO文字列で統一


# 請求書
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
def record_ledger(webhook_object, user_id=None, product_name=None):
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
            user_id=user_id,
            amount=amount_total,
            currency=currency,
            status=payment_status,
            product_name=product_name,
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
def upsert_subscription(webhook_object, user_id=None):
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
            existing_subscription.user_id = user_id
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
                user_id=user_id,
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


# ユーザーを登録
def create_user(email, password_hash, name, phone=None, birthdate=None, terms_accepted=False, privacy_accepted=False):
    session = get_session()
    try:
        # メールアドレスの重複チェック
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            raise ValueError("このメールアドレスは既に登録されています")
        
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            birthdate=birthdate,
            terms_accepted=terms_accepted,
            privacy_accepted=privacy_accepted
        )
        session.add(user)
        session.commit()
        logger.info(f"User created: {user.email}")
        return user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        session.rollback()
        raise e
    finally:
        session.close()


# メールアドレスでユーザーを取得
def get_user_by_email(email):
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        return user
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        raise e
    finally:
        session.close()


# IDでユーザーを取得
def get_user_by_id(user_id):
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        return user
    except Exception as e:
        logger.error(f"Error getting user by id: {e}")
        raise e
    finally:
        session.close()


# 全ユーザーを取得
def get_all_users():
    session = get_session()
    try:
        users = session.query(User).all()
        return users
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise e
    finally:
        session.close()


# ユーザーの購入履歴を取得
def get_user_purchase_history(user_id):
    session = get_session()
    try:
        purchases = session.query(Ledger).filter_by(user_id=user_id).order_by(Ledger.created_at.desc()).all()
        return purchases
    except Exception as e:
        logger.error(f"Error getting user purchase history: {e}")
        raise e
    finally:
        session.close()


# ユーザーのサブスクリプション履歴を取得
def get_user_subscriptions(user_id):
    session = get_session()
    try:
        subscriptions = session.query(Subscription).filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error getting user subscriptions: {e}")
        raise e
    finally:
        session.close()


# ユーザーの全履歴を取得（購入履歴とサブスクリプション）
def get_user_all_history(user_id):
    session = get_session()
    try:
        purchases = session.query(Ledger).filter_by(user_id=user_id).order_by(Ledger.created_at.desc()).all()
        subscriptions = session.query(Subscription).filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).all()
        return {
            'purchases': purchases,
            'subscriptions': subscriptions
        }
    except Exception as e:
        logger.error(f"Error getting user all history: {e}")
        raise e
    finally:
        session.close()
