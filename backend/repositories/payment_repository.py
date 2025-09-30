"""
支払い・請求書関連のリポジトリ
"""
import datetime
import logging
from models import Ledger, Invoice
from .database import get_session

logger = logging.getLogger(__name__)


# ============================================
# 支払い台帳
# ============================================

def record_ledger(webhook_object, user_id=None, product_name=None):
    """支払い台帳を記録"""
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

        # 既存のレコードをチェック
        existing_entry = session.query(Ledger).filter_by(session_id=session_id).first()
        if existing_entry:
            logger.info(f"Ledger entry already exists: {session_id}")
            return existing_entry

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
        return ledger_entry
    except Exception as e:
        logger.error(f"Error recording ledger: {e}")
        session.rollback()
        
        # 重複キーエラーの場合は既存レコードを返す
        if "duplicate key value violates unique constraint" in str(e):
            logger.info(f"Duplicate key error for session_id: {session_id}, returning existing entry")
            try:
                existing_entry = session.query(Ledger).filter_by(session_id=session_id).first()
                if existing_entry:
                    return existing_entry
            except Exception as query_error:
                logger.error(f"Error querying existing entry: {query_error}")
        
        raise e
    finally:
        session.close()


def get_ledger():
    """支払い台帳を取得"""
    session = get_session()
    try:
        ledger = session.query(Ledger).all()
        return ledger
    except Exception as e:
        logger.error(f"Error getting ledger: {e}")
        raise e
    finally:
        session.close()


# ============================================
# 請求書
# ============================================

def record_invoice(webhook_object):
    """請求書を記録"""
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
        logger.info(f"Checking existing invoice for ID: {invoice_id}, found: {existing_invoice is not None}")
        
        if existing_invoice:
            logger.info(f"Invoice already exists: {invoice_id}")
            return existing_invoice
        
        # 新しいインボイスを作成
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
        session.commit()
        return invoice_entry
    except Exception as e:
        logger.error(f"Error recording invoice: {e}")
        session.rollback()
        
        # 重複キーエラーの場合は既存レコードを返す
        if "duplicate key value violates unique constraint" in str(e):
            logger.info(f"Duplicate key error for invoice_id: {invoice_id}, returning existing entry")
            try:
                existing_invoice = session.query(Invoice).filter_by(id=invoice_id).first()
                if existing_invoice:
                    return existing_invoice
            except Exception as query_error:
                logger.error(f"Error querying existing invoice: {query_error}")
        
        raise e
    finally:
        session.close()
