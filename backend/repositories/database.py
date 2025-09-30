"""
データベース初期化・共通ユーティリティ
"""
import os
import datetime
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from models import Base, User, Ledger, Subscription, UserSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = None


def init_db():
    global engine
    engine = create_engine(os.getenv("DATABASE_URL"))
    
    # テーブルが存在しない場合のみ作成
    try:
        # 既存のテーブルをチェック
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # 必要なテーブルを個別に作成
        tables_to_create = []
        
        if 'users' not in existing_tables:
            tables_to_create.append(User.__table__)
        if 'ledger' not in existing_tables:
            tables_to_create.append(Ledger.__table__)
        if 'subscriptions' not in existing_tables:
            tables_to_create.append(Subscription.__table__)
        if 'user_sessions' not in existing_tables:
            tables_to_create.append(UserSession.__table__)
        
        # 必要なテーブルのみ作成
        for table in tables_to_create:
            table.create(engine, checkfirst=True)
            
        logger.info("データベース初期化完了")
        
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
        # フォールバック: 全テーブルを作成
        try:
            Base.metadata.create_all(engine)
        except Exception as fallback_error:
            logger.warning(f"フォールバックでもエラー: {fallback_error}")


def get_session():
    """セッションを取得"""
    return Session(engine)


def now():
    """現在の日時を取得"""
    return datetime.datetime.now().isoformat()
