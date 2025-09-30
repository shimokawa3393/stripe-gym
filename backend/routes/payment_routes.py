"""
決済・サブスクリプション関連のルート
"""
from flask import Blueprint, request, jsonify
import os
import stripe
import datetime
import logging
from repositories import (
    validate_session,
    get_user_by_id,
    upsert_stripe_customer,
    get_plan_name_from_price_id,
    get_session,
)
from models import Subscription

logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__, url_prefix='/api')

# 環境変数
BASE_URL = os.getenv("BASE_URL")
PRICE_ID = os.getenv("PRICE_ID")


@payment_bp.route("/checkout", methods=["POST"])
def checkout():
    """オリジナルプロテイン購入API"""
    try:
        # セッショントークンからユーザーIDを取得
        session_token = request.headers.get('Authorization')
        if not session_token or not session_token.startswith('Bearer '):
            return jsonify({"error": "ログインが必要です"}), 401
        
        token = session_token[7:]  # "Bearer "を除去
        user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"error": "無効なセッションです。再度ログインしてください"}), 401
        
        # ユーザー情報を取得
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404
        
        # Stripe Customerを取得または作成
        stripe_customer_id = upsert_stripe_customer(user)
        
        # StripeのCheckout Sessionを作成
        checkout_session = stripe.checkout.Session.create(
            customer = stripe_customer_id,  # Customer IDを指定
            success_url = f"{BASE_URL}/success-checkout?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url  = f"{BASE_URL}/cancel",
            payment_method_types = ["card"],
            mode = "payment",
            line_items = [
                {
                    'price_data': {
                        'currency': 'jpy',
                        'product_data': {'name': 'オリジナルプロテイン'},
                        'unit_amount': 4980,
                    },
                    'quantity': 1,
                }
            ],
            metadata={
                'user_id': str(user_id),
                'product_name': 'オリジナルプロテイン'
            }
        )
        return jsonify({"id": checkout_session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payment_bp.route("/subscription", methods=["POST"])
def subscription():
    """サブスクリプション課金API"""
    try:
        # リクエストボディからプラン情報を取得
        data = request.get_json()
        plan_name = data.get("plan_name", "プレミアムプラン")
        plan_type = data.get("plan_type", "premium")  # standard または premium
        
        # セッショントークンからユーザーIDを取得
        session_token = request.headers.get('Authorization')
        if not session_token or not session_token.startswith('Bearer '):
            return jsonify({"error": "ログインが必要です"}), 401
        
        token = session_token[7:]  # "Bearer "を除去
        user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"error": "無効なセッションです。再度ログインしてください"}), 401
        
        # ユーザーが既に同じプランに契約していないかチェック
        session = get_session()
        try:
            # プランタイプに応じて価格IDを決定
            if plan_type == "standard":
                price_id = os.getenv("STANDARD_PRICE_ID", PRICE_ID)
                product_name = "スタンダードプラン"
            else:
                price_id = os.getenv("PREMIUM_PRICE_ID", PRICE_ID)
                product_name = "プレミアムプラン"
            
            # アクティブなサブスクリプションをチェック
            active_subscription = session.query(Subscription).filter_by(
                user_id=user_id,
                price_id=price_id,
                status='active'
            ).first()
            
            if active_subscription:
                return jsonify({
                    "error": f"既に{product_name}に契約しています。同じプランに複数契約することはできません。",
                    "already_subscribed": True
                }), 400
        except Exception as e:
            print(f"Error checking existing subscription: {e}")
        finally:
            session.close()
        
        # ユーザー情報を取得
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404
        
        # Stripe Customerを取得または作成
        stripe_customer_id = upsert_stripe_customer(user)
        
        # プランタイプに応じて価格IDを決定
        if plan_type == "standard":
            price_id = os.getenv("STANDARD_PRICE_ID", PRICE_ID)
            product_name = "スタンダードプラン"
        else:
            price_id = os.getenv("PREMIUM_PRICE_ID", PRICE_ID)
            product_name = "プレミアムプラン"
        
        subscription_session = stripe.checkout.Session.create(
            customer = stripe_customer_id,  # Customer IDを指定
            success_url=f"{BASE_URL}/success-subscription?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/cancel",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            allow_promotion_codes=True,
            metadata={
                'user_id': str(user_id),
                'product_name': product_name,
                'plan_type': plan_type
            }
        )
        return jsonify({"id": subscription_session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@payment_bp.route("/schedule-plan-change", methods=["POST"])
def schedule_plan_change():
    """プラン変更予約API（次回更新時にプラン変更）"""
    try:
        data = request.get_json()
        new_plan_type = data.get("new_plan_type")
        
        if not new_plan_type:
            return jsonify({"success": False, "error": "新しいプランタイプが必要です"}), 400
        
        # セッショントークンからユーザーIDを取得
        session_token = request.headers.get('Authorization')
        if not session_token or not session_token.startswith('Bearer '):
            return jsonify({"error": "ログインが必要です"}), 401
        
        token = session_token[7:]
        user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"error": "無効なセッションです"}), 401
        
        # 新しいプランの価格IDを取得
        if new_plan_type == "standard":
            new_price_id = os.getenv("STANDARD_PRICE_ID", PRICE_ID)
            new_plan_name = "スタンダードプラン"
        else:
            new_price_id = os.getenv("PREMIUM_PRICE_ID", PRICE_ID)
            new_plan_name = "プレミアムプラン"
        
        # 現在のアクティブなサブスクリプションを取得
        session = get_session()
        try:
            active_subscription = session.query(Subscription).filter_by(
                user_id=user_id,
                status='active',
                cancel_at_period_end=False
            ).first()
            
            if not active_subscription:
                return jsonify({"success": False, "error": "アクティブなサブスクリプションがありません"}), 400
            
            # 既に同じプランに契約しているかチェック
            if active_subscription.price_id == new_price_id:
                return jsonify({
                    "success": False,
                    "error": f"既に{new_plan_name}に契約しています"
                }), 400
            
            # サブスクリプションの現在のスケジュールを取得
            current_sub = stripe.Subscription.retrieve(active_subscription.id)
            existing_schedule_id = current_sub.get('schedule')
            
            logger.info(f"Current subscription data: {current_sub}")
            logger.info(f"Schedule ID: {existing_schedule_id}")
            
            if existing_schedule_id:
                # 既存のスケジュールを取得して詳細を確認
                existing_schedule = stripe.SubscriptionSchedule.retrieve(existing_schedule_id)
                logger.info(f"Existing schedule phases: {existing_schedule.phases}")
                
                # 既存のスケジュールがある場合は、それを更新
                logger.info(f"Updating existing schedule: {existing_schedule_id}")
                
                # 現在のフェーズの開始日を取得
                current_phase_start = existing_schedule.phases[0]['start_date']
                
                schedule = stripe.SubscriptionSchedule.modify(
                    existing_schedule_id,
                    end_behavior='release',
                    phases=[
                        {
                            # フェーズ1: 現在のプラン（期間終了まで）
                            'items': [{'price': active_subscription.price_id, 'quantity': 1}],
                            'start_date': current_phase_start,
                            'end_date': active_subscription.current_period_end,
                        },
                        {
                            # フェーズ2: 新しいプラン（期間終了後から）
                            'items': [{'price': new_price_id, 'quantity': 1}],
                        }
                    ],
                    metadata={
                        'user_id': str(user_id),
                        'scheduled_plan_change': 'true',
                        'new_plan_type': new_plan_type
                    }
                )
            else:
                # スケジュールがない場合は、新規作成
                schedule = stripe.SubscriptionSchedule.create(
                    from_subscription=active_subscription.id,
                )
                
                # 次に、スケジュールを更新して新しいプランへの切り替えを設定
                schedule = stripe.SubscriptionSchedule.modify(
                    schedule.id,
                    end_behavior='release',
                    phases=[
                        {
                            # フェーズ1: 現在のプラン（期間終了まで）
                            'items': [{'price': active_subscription.price_id, 'quantity': 1}],
                            'start_date': schedule.phases[0]['start_date'],
                            'end_date': active_subscription.current_period_end,
                        },
                        {
                            # フェーズ2: 新しいプラン（期間終了後から）
                            'items': [{'price': new_price_id, 'quantity': 1}],
                        }
                    ],
                    metadata={
                        'user_id': str(user_id),
                        'scheduled_plan_change': 'true',
                        'new_plan_type': new_plan_type
                    }
                )
            
            logger.info(f"Subscription schedule created: {schedule.id} for user {user_id}")
            
            return jsonify({
                "success": True,
                "message": f"次回更新時（{datetime.datetime.fromtimestamp(active_subscription.current_period_end).strftime('%Y年%m月%d日')}）に{new_plan_name}へ変更予約が完了しました",
                "schedule_id": schedule.id,
                "change_date": active_subscription.current_period_end
            }), 200
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating subscription schedule: {e}")
            return jsonify({"success": False, "error": f"Stripeエラー: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"Error scheduling plan change: {e}")
            return jsonify({"success": False, "error": f"プラン変更予約中にエラーが発生しました: {str(e)}"}), 500
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({"success": False, "error": f"プラン変更予約中にエラーが発生しました: {str(e)}"}), 500


@payment_bp.route("/cancel-scheduled-change", methods=["POST"])
def cancel_scheduled_change():
    """プラン変更予約取り消しAPI"""
    try:
        data = request.get_json()
        schedule_id = data.get("schedule_id")
        
        if not schedule_id:
            return jsonify({"success": False, "error": "スケジュールIDが必要です"}), 400
        
        # セッショントークンからユーザーIDを取得
        session_token = request.headers.get('Authorization')
        if not session_token or not session_token.startswith('Bearer '):
            return jsonify({"success": False, "error": "ログインが必要です"}), 401
        
        token = session_token[7:]
        user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"success": False, "error": "無効なセッションです"}), 401
        
        # スケジュールを解除（サブスクリプションを通常の状態に戻す）
        stripe.SubscriptionSchedule.release(schedule_id)
        
        logger.info(f"Subscription schedule released: {schedule_id}")
        
        return jsonify({
            "success": True,
            "message": "プラン変更予約をキャンセルしました"
        }), 200
        
    except stripe.error.StripeError as e:
        logger.error(f"Error releasing schedule: {e}")
        return jsonify({"success": False, "error": f"Stripeエラー: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error canceling scheduled change: {e}")
        return jsonify({"success": False, "error": f"予約キャンセル処理中にエラーが発生しました: {str(e)}"}), 500


@payment_bp.route("/cancel-subscription", methods=["POST"])
def cancel_subscription():
    """サブスクリプション解約API"""
    try:
        data = request.get_json()
        subscription_id = data.get("subscription_id")
        
        if not subscription_id:
            return jsonify({"success": False, "error": "サブスクリプションIDが必要です"}), 400
        
        # セッショントークンからユーザーIDを取得
        user_id = None
        session_token = request.headers.get('Authorization')
        if session_token and session_token.startswith('Bearer '):
            token = session_token[7:]  # "Bearer "を除去
            user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"success": False, "error": "ログインが必要です"}), 401
        
        # Stripeでサブスクリプションをキャンセル
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True  # 現在の期間終了時にキャンセル
        )
        
        # データベースのサブスクリプションステータスを即座に更新
        session = get_session()
        try:
            subscription = session.query(Subscription).filter_by(id=subscription_id).first()
            if subscription:
                subscription.cancel_at_period_end = True  # 解約予定フラグを設定
                session.commit()
                logger.info(f"Subscription cancel_at_period_end set: {subscription_id}")
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            session.rollback()
        finally:
            session.close()
        
        return jsonify({
            "success": True,
            "message": "サブスクリプションの解約予約が完了しました。現在の期間終了時にキャンセルされます。"
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({"success": False, "error": f"Stripeエラー: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"解約処理中にエラーが発生しました: {str(e)}"}), 500


@payment_bp.route("/reactivate-subscription", methods=["POST"])
def reactivate_subscription():
    """サブスクリプション解約取り消しAPI"""
    try:
        data = request.get_json()
        subscription_id = data.get("subscription_id")
        
        if not subscription_id:
            return jsonify({"success": False, "error": "サブスクリプションIDが必要です"}), 400
        
        # セッショントークンからユーザーIDを取得
        session_token = request.headers.get('Authorization')
        if not session_token or not session_token.startswith('Bearer '):
            return jsonify({"success": False, "error": "ログインが必要です"}), 401
        
        token = session_token[7:]
        user_id = validate_session(token)
        
        if not user_id:
            return jsonify({"success": False, "error": "無効なセッションです"}), 401
        
        # Stripeで解約を取り消す
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False  # 解約をキャンセル
        )
        
        # データベースのサブスクリプションステータスを更新
        session = get_session()
        try:
            subscription = session.query(Subscription).filter_by(id=subscription_id).first()
            if subscription:
                subscription.cancel_at_period_end = False
                session.commit()
                logger.info(f"Subscription reactivated: {subscription_id}")
        except Exception as e:
            logger.error(f"Error reactivating subscription: {e}")
            session.rollback()
        finally:
            session.close()
        
        return jsonify({
            "success": True,
            "message": "サブスクリプションの解約を取り消しました。引き続きご利用いただけます。"
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({"success": False, "error": f"Stripeエラー: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"解約取り消し処理中にエラーが発生しました: {str(e)}"}), 500


@payment_bp.route("/get-checkout-session", methods=["POST"])
def get_checkout_session():
    """チェックアウトセッション情報取得API"""
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        
        if not session_id:
            return jsonify({"success": False, "error": "セッションIDが必要です"}), 400
        
        # Stripeからセッション情報を取得
        session = stripe.checkout.Session.retrieve(session_id)
        
        # メタデータから情報を抽出
        metadata = session.get('metadata', {})
        product_name = metadata.get('product_name', '不明な商品')
        plan_type = metadata.get('plan_type', '')
        
        return jsonify({
            "success": True,
            "session": {
                "id": session.id,
                "mode": session.mode,
                "product_name": product_name,
                "plan_type": plan_type,
                "amount_total": session.amount_total,
                "currency": session.currency,
                "payment_status": session.payment_status
            }
        }), 200
        
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving checkout session: {e}")
        return jsonify({"success": False, "error": f"Stripeエラー: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error getting checkout session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
