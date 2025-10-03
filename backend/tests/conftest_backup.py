"""
pytest設定とフィクスチャ
"""
import pytest
import os
import stripe
import datetime
import tempfile
from app import app, init_db
from repositories import get_session
from models import User, Subscription, Ledger, Invoice, ProcessedEvent


@pytest.fixture(autouse=True)
def setup_test_env():
    """テスト実行時の環境変数設定"""
    test_env_vars = {
        "STRIPE_SECRET_KEY": "sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "STRIPE_PUBLISHABLE_KEY": "pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "DATABASE_URL": "sqlite:///:memory:",
        "FLASK_ENV": "testing",
        "FRONTEND_URL": "http://localhost:8080",
        "PRICE_ID": "price_test123",
        "PREMIUM_PRICE_ID": "price_premium_test123",
        "STANDARD_PRICE_ID": "price_standard_test123"
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    
    yield
    
    # テスト終了後のクリーンアップは自動的に行われる


@pytest.fixture(autouse=True)
def setup_stripe_mock():
    """テスト前にStripe設定をstripe-mockに切り替え"""
    # 元の設定を保存
    original_base = stripe.api_base
    original_version = stripe.api_version
    
    # stripe-mockに設定
    stripe.api_base = "http://stripe-mock-test:12111"
    stripe.api_version = "2020-08-27"
    
    yield
    
    # 元に戻す
    stripe.api_base = original_base
    stripe.api_version = original_version


@pytest.fixture(scope="function")
def db_engine():
    """テスト用データベースエンジン"""
    from sqlalchemy import create_engine
    from repositories import Base
    
    # SQLiteインメモリデータベース
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    return engine


@pytest.fixture()
def client():
    """Flaskテストクライアント"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            # テスト用データベースの初期化
            init_db()
        yield client


@pytest.fixture()
def db_session():
    """テスト用データベースセッション"""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_user(db_session):
    """テスト用サンプルユーザー"""
    import random
    random_id = random.randint(10000, 99999)  # 既存データと重複しないID
    
    user = User(
        id=random_id,
        email=f"test{random_id}@example.com",
        name="テストユーザー",
        phone="090-1234-5678",
        birthdate=datetime.date(1990, 1, 1),
        stripe_customer_id=f"cus_test_{random_id}",
        password_hash="hashed_password",
        terms_accepted=True,
        privacy_accepted=True,
        created_at=datetime.datetime.utcnow()
    )
    
    db_session.add(user)
    db_session.commit()
    
    yield user
    
    # 特定のユーザーを削除（孤立したデータは残らない）
    try:
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture()
def sample_subscription(db_session, sample_user):
    """テスト用サブスクリプション"""
    import random
    import datetime
    
    subscription_id = f"sub_test_{random.randint(10000, 99999)}"
    
    subscription = Subscription(
        id=subscription_id,
        user_id=sample_user.id,
        stripe_subscription_id=subscription_id,
        customer_id=sample_user.stripe_customer_id,
        price_id="price_premium_test",
        status="active",
        current_period_end=int(datetime.datetime.now().timestamp()) + 86400,
        cancel_at_period_end=False,
        created_at=datetime.datetime.utcnow()
    )
    
    db_session.add(subscription)
    db_session.commit()
    
    yield subscription
    
    # クリーンアップ
    try:
        db_session.delete(subscription)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture()
def sample_ledger(db_session, sample_user):
    """テスト用台帳レコード"""
    ledger = Ledger(
        session_id="cs_test123456789",
        user_id=sample_user.id,
        amount=5000,
        currency="jpy",
        status="complete",
        product_name="スタンダードプラン",
        created_at="2024-01-01T00:00:00Z"
    )
    
    db_session.add(ledger)
    db_session.commit()
    
    yield ledger
    
    db_session.delete(ledger)
    db_session.commit()


def load_test_data(filename):
    """テストデータファイルを読み込む"""
    import json
    import os
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'webhook_events', filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_test_data_string(filename):
    """テストデータファイルを文字列として読み込む"""
    import os
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data', 'webhook_events', filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
