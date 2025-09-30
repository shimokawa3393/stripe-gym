"""
ユーザー関連のリポジトリ
"""
import logging
import hashlib
import secrets
import stripe
from models import User, Ledger
from .database import get_session

logger = logging.getLogger(__name__)


# ============================================
# パスワード関連
# ============================================

def hash_password(password):
    """パスワードをハッシュ化"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{password_hash.hex()}"


def verify_password(password, password_hash):
    """パスワードを検証"""
    try:
        salt, hash_hex = password_hash.split(':')
        password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return password_hash_check.hex() == hash_hex
    except:
        return False


# ============================================
# ユーザー管理
# ============================================

def create_user(email, password_hash, name, phone=None, birthdate=None, terms_accepted=False, privacy_accepted=False):
    """ユーザーを登録"""
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


def get_user_by_email(email):
    """メールアドレスでユーザーを取得"""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        return user
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        raise e
    finally:
        session.close()


def get_user_by_id(user_id):
    """IDでユーザーを取得"""
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        return user
    except Exception as e:
        logger.error(f"Error getting user by id: {e}")
        raise e
    finally:
        session.close()


def get_all_users():
    """全ユーザーを取得"""
    session = get_session()
    try:
        users = session.query(User).all()
        return users
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise e
    finally:
        session.close()


def get_user_purchase_history(user_id):
    """ユーザーの購入履歴を取得"""
    session = get_session()
    try:
        purchases = session.query(Ledger).filter_by(user_id=user_id).order_by(Ledger.created_at.desc()).all()
        return purchases
    except Exception as e:
        logger.error(f"Error getting user purchase history: {e}")
        raise e
    finally:
        session.close()


def authenticate_user(email, password):
    """ユーザーのログインを検証"""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        raise e
    finally:
        session.close()


# ============================================
# Stripe Customer管理
# ============================================

def upsert_stripe_customer(user):
    """ユーザーのStripe Customerを作成または取得"""
    # 既にStripe Customer IDが存在する場合は返す
    if user.stripe_customer_id:
        try:
            # Stripeで有効なCustomerか確認
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
            if not customer.get('deleted'):
                return user.stripe_customer_id
        except stripe.error.StripeError:
            # Customer IDが無効な場合は新規作成
            pass
    
    # 新しいStripe Customerを作成
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={
                'user_id': str(user.id)
            }
        )
        
        # DBにCustomer IDを保存
        session = get_session()
        try:
            db_user = session.query(User).filter_by(id=user.id).first()
            if db_user:
                db_user.stripe_customer_id = customer.id
                session.commit()
                logger.info(f"Stripe Customer created and saved: {customer.id} for user {user.id}")
        except Exception as e:
            logger.error(f"Error saving stripe_customer_id: {e}")
            session.rollback()
        finally:
            session.close()
        
        return customer.id
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe Customer: {e}")
        raise e
