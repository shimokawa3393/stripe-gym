import pytest
import os
import datetime
import stripe
from app import app
from repositories import init_db, get_session
from models import Base, User, Subscription, ProcessedEvent, Ledger

# テスト用DBの初期化とクリーンアップ
@pytest.fixture(scope="session")
def db_engine():
    """セッション単位でテスト用DBエンジンを作成し、テスト終了後に破棄"""
    # SQLite in-memory database for testing
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    # init_db() は engine を作成し、Base.metadata.create_all(engine) を呼び出す
    # ここでは app_context 内で init_db を呼び出すことで、FlaskアプリのDB設定を反映させる
    with app.app_context():
        init_db()
        engine = get_session().get_bind() # 現在のセッションからエンジンを取得
        yield engine
        # テストセッション終了時にテーブルを削除
        Base.metadata.drop_all(engine)

@pytest.fixture()
def client(db_engine):
    """Flaskテストクライアント"""
    app.config["TESTING"] = True
    
    with app.test_client() as client:
        with app.app_context():
            # 各テスト関数実行前にDBをクリーンな状態にする
            # Base.metadata.create_all(db_engine) は既に session スコープで実行済み
            # ここでは既存データを削除してクリーンアップ
            session = get_session()
            session.query(User).delete()
            session.query(Subscription).delete()
            session.query(ProcessedEvent).delete()
            session.query(Ledger).delete()
            session.commit()
            session.close()
        yield client

@pytest.fixture(autouse=True)
def setup_stripe_mock():
    """テスト開始前後にStripe設定を切り替え"""
    original_base = stripe.api_base
    original_api_version = stripe.api_version
    
    # stripe-mockにAPIベースURL変更
    stripe.api_base = "http://stripe-mock-test:12111"
    stripe.api_version = "2020-08-27" # stripe-mockがサポートするAPIバージョンに合わせる
    
    yield  # テスト実行
    
    # 元に戻す
    stripe.api_base = original_base
    stripe.api_version = original_api_version

@pytest.fixture(autouse=True)
def test_env():
    """テスト実行時の環境変数設定"""
    original_env = os.environ.copy()
    test_env_vars = {
        "SUPPORTED_FLASHING": "",
        "STRIPE_SECRET_KEY": "sk_test_xxx",
        "STRIPE_Publishable_KEY": "pk_test_xxx",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_xxx",
        "DATABASE_URL": "sqlite:///:memory:", # SQLite in-memory for tests
        "FLASK_ENVIRONMENT": "testing",
        "FRONTEND_URL": "http://localhost:8080",
        "PRICE_ID": "price_standard_test",
        "PREMIUM_PRICE_ID": "price_premium_test",
        "STANDARD_PRICE_ID": "price_standard_test",
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture()
def db_session(client): # client fixtureに依存してapp_contextを確保
    """テスト用DBセッション"""
    with app.app_context():
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

def load_test_data(filename: str) -> dict:
    """テスト用JSONデータを読み込む"""
    import json
    import os
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'webhook_events')
    file_path = os.path.join(data_dir, filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_test_data_string(filename: str) -> str:
    """テスト用JSONデータを文字列として読み込む"""
    import os
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'webhook_events')
    file_path = os.path.join(data_dir, filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
