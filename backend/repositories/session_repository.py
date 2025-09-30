"""
セッション管理のリポジトリ
"""
import datetime
import logging
import secrets
from models import UserSession
from .database import get_session
from .user_repository import get_user_by_id

logger = logging.getLogger(__name__)


def create_session(user_id):
    """ユーザーセッションを作成"""
    session_token = secrets.token_urlsafe(32)
    
    try:
        session = get_session()
        
        # 既存のセッションを無効化
        session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).update({'is_active': False})
        
        # 新しいセッションを作成
        new_session = UserSession(
            user_id=user_id,
            session_token=session_token,
            created_at=datetime.datetime.utcnow(),
            last_activity=datetime.datetime.utcnow(),
            is_active=True
        )
        
        session.add(new_session)
        session.commit()
        
        return session_token
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        session.rollback()
        raise e
    finally:
        session.close()


def validate_session(session_token):
    """セッションを検証"""
    try:
        session = get_session()
        
        # セッションを検索
        user_session = session.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if not user_session:
            return None
        
        # セッションの有効期限チェック（24時間）
        if datetime.datetime.utcnow() - user_session.created_at > datetime.timedelta(hours=24):
            user_session.is_active = False
            session.commit()
            return None
        
        # 最終アクティビティを更新
        user_session.last_activity = datetime.datetime.utcnow()
        session.commit()
        
        return user_session.user_id
        
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return None
    finally:
        session.close()


def logout_user(session_token):
    """ユーザーをログアウト"""
    try:
        session = get_session()
        
        # セッションを無効化
        user_session = session.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if user_session:
            user_session.is_active = False
            session.commit()
            return True
        return False
            
    except Exception as e:
        logger.error(f"Error logging out user: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_user_from_session(session_token):
    """セッションからユーザー情報を取得"""
    user_id = validate_session(session_token)
    if not user_id:
        return None
    
    return get_user_by_id(user_id)
