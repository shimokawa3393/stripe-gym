"""
認証関連のルート
"""
from flask import Blueprint, request, jsonify
import logging
from repositories import (
    create_user,
    hash_password,
    authenticate_user,
    create_session,
    logout_user,
    validate_session,
    upsert_stripe_customer,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api')


@auth_bp.route("/register", methods=["POST"])
def register():
    """ユーザー登録API"""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        phone = data.get("phone")
        birthdate = data.get("birthdate")
        terms_accepted = data.get("terms") == "on" or data.get("terms") == True
        privacy_accepted = data.get("privacy") == "on" or data.get("privacy") == True
        
        # 必須項目のチェック
        if not email or not password or not name:
            return jsonify({"error": "メールアドレス、パスワード、お名前は必須です"}), 400
        
        # 利用規約とプライバシーポリシーの同意チェック
        if not terms_accepted or not privacy_accepted:
            return jsonify({"error": "利用規約とプライバシーポリシーに同意してください"}), 400
        
        # パスワードの長さチェック
        if len(password) < 8:
            return jsonify({"error": "パスワードは8文字以上で入力してください"}), 400
        
        # パスワードをハッシュ化
        password_hash = hash_password(password)
        
        # ユーザーを作成
        user = create_user(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            birthdate=birthdate,
            terms_accepted=terms_accepted,
            privacy_accepted=privacy_accepted
        )
        
        # Stripe Customerを作成
        try:
            stripe_customer_id = upsert_stripe_customer(user)
            logger.info(f"Stripe Customer created for user {user.id}: {stripe_customer_id}")
        except Exception as e:
            logger.error(f"Failed to create Stripe Customer: {e}")
            # Customerの作成に失敗してもユーザー登録は継続
        
        # セッションを作成
        session_token = create_session(user.id)
        
        return jsonify({
            "success": True,
            "message": "会員登録が完了しました",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            },
            "session_token": session_token
        }), 201
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"登録処理中にエラーが発生しました: {str(e)}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """ログインAPI"""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"error": "メールアドレスとパスワードが必要です"}), 400
        
        # ユーザーを認証
        user = authenticate_user(email, password)
        if not user:
            return jsonify({"error": "メールアドレスまたはパスワードが正しくありません"}), 401
        
        # セッションを作成
        session_token = create_session(user.id)
        print(f"ログイン成功: user_id={user.id}, session_token={session_token[:10]}...")
        
        return jsonify({
            "success": True,
            "message": "ログインが完了しました",
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            },
            "session_token": session_token
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"ログイン処理中にエラーが発生しました: {str(e)}"}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """ログアウトAPI"""
    try:
        data = request.get_json()
        session_token = data.get("session_token")
        
        if not session_token:
            return jsonify({"error": "セッショントークンが必要です"}), 400
        
        # セッションを検証
        user_id = validate_session(session_token)
        if not user_id:
            return jsonify({"error": "無効なセッションです"}), 401
        
        # ログアウト処理
        success = logout_user(session_token)
        
        if success:
            return jsonify({
                "success": True,
                "message": "ログアウトが完了しました"
            }), 200
        else:
            return jsonify({"error": "ログアウトに失敗しました"}), 500
        
    except Exception as e:
        return jsonify({"error": f"ログアウト処理中にエラーが発生しました: {str(e)}"}), 500


@auth_bp.route("/verify-session", methods=["POST"])
def verify_session():
    """セッション検証API"""
    try:
        data = request.get_json()
        session_token = data.get("session_token")
        
        print(f"セッション検証: token={session_token[:10] if session_token else None}...")
        
        if not session_token:
            return jsonify({"error": "セッショントークンが必要です"}), 400
        
        # セッションを検証
        user_id = validate_session(session_token)
        print(f"セッション検証結果: user_id={user_id}")
        
        if not user_id:
            return jsonify({"error": "無効なセッションです"}), 401
        
        return jsonify({
            "success": True,
            "message": "セッションが有効です",
            "user_id": user_id
        }), 200
        
    except Exception as e:
        print(f"セッション検証エラー: {str(e)}")
        return jsonify({"error": f"セッション検証中にエラーが発生しました: {str(e)}"}), 500
