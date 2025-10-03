"""
データベースモデル定義
"""
import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    CheckConstraint,
    Boolean,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ユーザー
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    birthdate = Column(Date)
    stripe_customer_id = Column(String(255), unique=True)  # Stripe Customer ID
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
    cancel_at_period_end = Column(Boolean, default=False)  # 期間終了時に解約するか
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


# セッション管理用のテーブル
class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # リレーション
    user = relationship("User", backref="sessions")


# Webhookイベント処理済み管理用のテーブル
class ProcessedEvent(Base):
    __tablename__ = 'processed_events'
    
    id = Column(String, primary_key=True)  # Stripe event ID
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String(100))  # イベントタイプ（例：customer.subscription.updated）
