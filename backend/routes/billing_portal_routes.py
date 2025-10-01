"""
Stripe Customer Portal関連のルート
"""
from flask import Blueprint, request, jsonify
import os
import stripe
import logging
from repositories import get_user_by_id

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__, url_prefix='/api')

# Stripeの設定
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


@billing_bp.route("/billing-portal/start", methods=["POST"])
def start_billing_portal():
    """Stripe Customer Portalセッション作成"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "ユーザーIDが必要です"}), 400
        
        # ユーザー情報を取得
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "ユーザーが見つかりません"}), 404
        
        if not user.stripe_customer_id:
            return jsonify({"success": False, "error": "Stripe Customer IDが見つかりません"}), 400
        
        # 戻り先URLを設定（マイページ）
        return_url = os.getenv("FRONTEND_URL", "http://localhost:8080") + "/mypage.html"
        
        # Stripe Customer Portalセッションを作成
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )
        
        logger.info(f"Created billing portal session for user {user_id}, customer {user.stripe_customer_id}")
        
        return jsonify({
            "success": True,
            "url": session.url
        }), 200
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in billing portal: {e}")
        return jsonify({"success": False, "error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error creating billing portal session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
