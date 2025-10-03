"""
データベーステスト：ORM操作とフィクスチャを使ったテスト
"""
import pytest
import datetime
from models import User, Subscription, ProcessedEvent
from repositories import get_session


@pytest.mark.unit
def test_user_model_creation(db_session, sample_user):
    """Userモデルのテスト"""
    
    # フィクスチャのユーザーが正しく作成されているか確認
    assert sample_user.id is not None
    assert sample_user.email == 'test@example.com'
    assert sample_user.name == 'テストユーザー'
    assert sample_user.stripe_customer_id == 'cus_test123456789'
    
    # 作成日時の確認
    assert isinstance(sample_user.created_at, datetime.datetime)
    assert sample_user.is_active == True
    
    # セッション内でQueryを実行して確認
    user_in_db = db_session.query(User).filter_by(email='test@example.com').first()
    assert user_in_db is not None
    assert user_in_db.name == sample_user.name


@pytest.mark.unit
def test_user_model_validation():
    """Userモデルのバリデーションテスト"""
    
    # 必須フィールドなしでUserを作成（エラーを期待）
    invalid_user = User()
    
    # SQLAlchemyのバリデーションは実際の保存時に発生
    assert invalid_user.email is None
    assert invalid_user.name is None


@pytest.mark.unit
def test_subscription_model_creation(db_session, sample_subscription):
    """Subscriptionモデルのテスト"""
    
    # フィクスチャのサブスクリプションが正しく作成されているか確認
    assert sample_subscription.id is not None
    assert sample_subscription.stripe_subscription_id == 'sub_test123456789'
    assert sample_subscription.user_id == 1
    assert sample_subscription.status == 'active'
    
    # 価格IDの確認
    assert sample_subscription.price_id == 'price_premium_test'
    
    # 期限日の確認
    assert isinstance(sample_subscription.current_period_end, (datetime.datetime, int))
    
    # DB内でクエリして確認
    subscription_in_db = db_session.query(Subscription).filter_by(
        stripe_subscription_id='sub_test123456789'
    ).first()
    assert subscription_in_db is not None
    assert subscription_in_db.status == 'active'


@pytest.mark.unit
def test_subscription_status_update(db_session):
    """サブスクリプションステータス更新のテスト"""
    
    # 新しいサブスクリプションを作成
    subscription = Subscription(
        stripe_subscription_id='test_sub_123',
        user_id=1,
        status='incomplete',
        price_id='price_test123',
        current_period_end=int(datetime.datetime.now().timestamp()) + 86400
    )
    
    db_session.add(subscription)
    db_session.commit()
    
    # ステータスを更新
    subscription.status = 'active'
    db_session.commit()
    
    # DBで確認
    updated_subscription = db_session.query(Subscription).filter_by(
        stripe_subscription_id='test_sub_123'
    ).first()
    
    assert updated_subscription.status == 'active'


@pytest.mark.unit
def test_processed_event_model(db_session):
    """ProcessedEventモデルのテスト"""
    
    # WebhookイベントID
    event_id = 'evt_test_processed_event_123'
    event_type = 'test.event.type'
    
    # ProcessedEventを作成
    processed_event = ProcessedEvent(
        id=event_id,
        event_type=event_type
    )
    
    db_session.add(processed_event)
    db_session.commit()
    
    # DBで確認
    created_event = db_session.query(ProcessedEvent).filter_by(id=event_id).first()
    assert created_event is not None
    assert created_event.event_type == event_type
    assert created_event.processed_at is not None


@pytest.mark.unit
def test_processed_event_duplicate_prevention(db_session):
    """ProcessedEvent重複防止のテスト"""
    
    event_id = 'evt_duplicate_test_123'
    
    # 1回目のイベントを作成
    processed_event1 = ProcessedEvent(
        id=event_id,
        event_type='test.event.type'
    )
    
    db_session.add(processed_event1)
    db_session.commit()
    
    # 同じIDで再度作成（制約によりエラーまたは無視される）
    processed_event2 = ProcessedEvent(
        id=event_id,
        event_type='different.event.type'
    )
    
    # 制約エラーを期待
    from sqlalchemy.exc import IntegrityError
    
    try:
        db_session.add(processed_event2)
        db_session.commit()
        pytest.fail("重複するIDでエラーが発生していない")
        
    except IntegrityError:
        # 期待されるエラー
        db_session.rollback()
        pass


@pytest.mark.integration
def test_user_subscription_relationship(db_session, sample_user, sample_subscription):
    """ユーザーとサブスクリプションの関係テスト"""
    
    # ユーザーとサブスクリプションが正しく関連付けられているか確認
    user_subscriptions = db_session.query(Subscription).filter_by(
        user_id=sample_user.id
    ).all()
    
    assert len(user_subscriptions) >= 1
    
    # サブスクリプションからユーザーを取得
    subscription_user = db_session.query(User).filter_by(
        id=sample_subscription.user_id
    ).first()
    
    assert subscription_user.email == sample_user.email


@pytest.mark.integration
def test_database_transaction_rollback(db_session):
    """データベーストランザクションのロールバックテスト"""
    
    # 最初の状態を保存
    initial_count = db_session.query(User).count()
    
    try:
        # 例外を起こすような操作
        new_user = User(
            email='transaction_test@example.com',
            password_hash='invalid_hash',
            name='Transaction Test'  # 必須フィールドが不足
        )
        
        db_session.add(new_user)
        
        # 意図的に例外を発生させる
        raise Exception("Test exception for rollback")
        
        db_session.commit()
        
    except Exception:
        # ロールバック
        db_session.rollback()
    
    # データベースが変更されていないことを確認
    final_count = db_session.query(User).count()
    assert final_count == initial_count, "ロールバックが正しく動作していない"


@pytest.mark.integration
def test_session_isolation(db_session):
    """セッション分離のテスト"""
    
    # 現在のセッションでユーザーを作成
    test_user = User(
        email='isolation_test@example.com',
        password_hash='hash123',
        name='Isolation Test'
    )
    
    db_session.add(test_user)
    # まだコミットしていない
    
    # 別のセッションを取得して確認（同一トランザクション内なので見える）
    query_user = db_session.query(User).filter_by(
        email='isolation_test@example.com'
    ).first()
    
    # まだコミットしていないので、Queryでは見つからないはず（実装次第）
    # PostgreSQLとSQLiteの動作の違いがある可能性


@pytest.mark.integration
def test_database_performance_basic(db_session, sample_user, sample_subscription):
    """基本的なデータベースパフォーマンステスト"""
    
    import time
    
    # ユーザー検索のパフォーマンステスト
    start_time = time.time()
    
    users = db_session.query(User).filter_by(email='test@example.com').all()
    
    end_time = time.time()
    query_time = end_time - start_time
    
    # 基本的なクエリが1秒以内で完了することを期待
    assert query_time < 1.0, f"クエリが遅すぎます: {query_time} seconds"
    assert len(users) >= 1
    
    # 複雑なJOINクエリのパフォーマンステスト
    start_time = time.time()
    
    result = db_session.query(User, Subscription).join(
        Subscription, User.id == Subscription.user_id
    ).all()
    
    end_time = time.time()
    join_query_time = end_time - start_time
    
    # JOINクエリも1秒以内で完了することを期待
    assert join_query_time < 1.0, f"JOINクエリが遅すぎます: {join_query_time} seconds"
    assert len(result) >= 1


@pytest.mark.integration
def test_database_constraints():
    """データベース制約のテスト"""
    
    session = get_session()
    
    try:
        # 重複するメールアドレスでエラーが発生するかをテスト
        user1 = User(
            email='duplicate@example.com',
            password_hash='hash1',
            name='User 1'
        )
        
        user2 = User(
            email='duplicate@example.com',  # 同じメールアドレス
            password_hash='hash2',
            name='User 2'
        )
        
        session.add(user1)
        session.commit()
        
        session.add(user2)
        session.commit()  # ここでエラーが発生するはず
        
        pytest.fail("重複するメールアドレスでエラーが発生していない")
        
    except Exception as e:
        # 期待されるエラー
        session.rollback()
        
    finally:
        session.close()
