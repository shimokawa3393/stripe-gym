"""
ユーザー情報関連のルート
"""
from flask import Blueprint, request, jsonify
import os
from repositories import (
    get_user_by_id,
    get_user_purchase_history,
    get_user_subscriptions,
    get_plan_name_from_price_id,
    get_session,
)
from models import Subscription
import stripe
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/api')


@user_bp.route("/user-info", methods=["POST"])
def user_info():
    """ユーザー情報取得API"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "ユーザーIDが必要です"}), 400
        
        user = get_user_by_id(user_id)
        if user:
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "birthdate": user.birthdate.strftime('%Y-%m-%d') if user.birthdate else None,
                    "created_at": user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None
                }
            }), 200
        else:
            return jsonify({"success": False, "error": "ユーザーが見つかりません"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@user_bp.route("/user-purchase-history", methods=["POST"])
def user_purchase_history():
    """ユーザー購入履歴取得API"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "ユーザーIDが必要です"}), 400
        
        purchases = get_user_purchase_history(user_id)
        return jsonify({
            "success": True,
            "purchases": [
                {
                    "session_id": purchase.session_id,
                    "product_name": purchase.product_name,
                    "amount": float(purchase.amount) if purchase.amount else 0,
                    "currency": purchase.currency,
                    "status": purchase.status,
                    "created_at": purchase.created_at
                }
                for purchase in purchases
            ]
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@user_bp.route("/user-active-subscriptions", methods=["POST"])
def user_active_subscriptions():
    """ユーザーのアクティブサブスクリプション取得API"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "ユーザーIDが必要です"}), 400
        
        session = get_session()
        try:
            # アクティブなサブスクリプションを取得
            active_subscriptions = session.query(Subscription).filter_by(
                user_id=user_id,
                status='active'
            ).all()
            
            PRICE_ID = os.getenv("PRICE_ID")
            premium_price_id = os.getenv("PREMIUM_PRICE_ID", PRICE_ID)
            standard_price_id = os.getenv("STANDARD_PRICE_ID")
            
            result = {
                "has_premium": False,
                "has_standard": False,
                "subscriptions": []
            }
            
            for sub in active_subscriptions:
                if sub.price_id == premium_price_id:
                    result["has_premium"] = True
                elif sub.price_id == standard_price_id:
                    result["has_standard"] = True
                
                # スケジュール情報を取得
                scheduled_change = None
                try:
                    stripe_sub = stripe.Subscription.retrieve(sub.id)
                    schedule_id = stripe_sub.get('schedule')
                    
                    if schedule_id:
                        schedule = stripe.SubscriptionSchedule.retrieve(schedule_id)
                        if len(schedule.phases) > 1:
                            next_phase = schedule.phases[1]
                            next_price_id = next_phase['items'][0]['price']
                            scheduled_change = {
                                "schedule_id": schedule_id,
                                "next_price_id": next_price_id,
                                "next_plan_name": get_plan_name_from_price_id(next_price_id),
                                "change_date": sub.current_period_end
                            }
                except Exception as e:
                    logger.error(f"Error retrieving schedule for subscription {sub.id}: {e}")
                
                result["subscriptions"].append({
                    "id": sub.id,
                    "price_id": sub.price_id,
                    "plan_name": get_plan_name_from_price_id(sub.price_id),
                    "status": sub.status,
                    "current_period_end": sub.current_period_end,  # 有効期限（Unix timestamp）
                    "scheduled_change": scheduled_change
                })
            
            return jsonify({
                "success": True,
                **result
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@user_bp.route("/user-subscription-history", methods=["POST"])
def user_subscription_history():
    """ユーザーサブスクリプション履歴取得API"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "ユーザーIDが必要です"}), 400
        
        subscriptions = get_user_subscriptions(user_id)
        
        # 各サブスクリプションにスケジュール情報を追加
        subscriptions_with_schedule = []
        for subscription in subscriptions:
            sub_data = {
                "id": subscription.id,
                "subscription_id": subscription.id,
                "price_id": subscription.price_id,
                "plan_name": get_plan_name_from_price_id(subscription.price_id),
                "status": subscription.status,
                "created_at": subscription.created_at,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end or False,
                "scheduled_change": None  # デフォルトはなし
            }
            
            # アクティブなサブスクリプションの場合、スケジュールを確認
            if subscription.status == 'active':
                try:
                    stripe_sub = stripe.Subscription.retrieve(subscription.id)
                    schedule_id = stripe_sub.get('schedule')
                    
                    if schedule_id:
                        # スケジュールの詳細を取得
                        schedule = stripe.SubscriptionSchedule.retrieve(schedule_id)
                        
                        # 次のフェーズがあるかチェック
                        if len(schedule.phases) > 1:
                            next_phase = schedule.phases[1]
                            next_price_id = next_phase['items'][0]['price']
                            
                            sub_data["scheduled_change"] = {
                                "schedule_id": schedule_id,
                                "next_price_id": next_price_id,
                                "next_plan_name": get_plan_name_from_price_id(next_price_id),
                                "change_date": subscription.current_period_end
                            }
                except Exception as e:
                    logger.error(f"Error retrieving schedule for subscription {subscription.id}: {e}")
            
            subscriptions_with_schedule.append(sub_data)
        
        return jsonify({
            "success": True,
            "subscriptions": subscriptions_with_schedule
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
