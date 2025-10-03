"""
セキュリティ関連の設定とユーティリティ
"""
import os
import logging
from functools import wraps
from flask import request, jsonify, g, redirect
from werkzeug.exceptions import TooManyRequests
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from datetime import datetime, timedelta
import hashlib
import ipaddress

logger = logging.getLogger(__name__)

# Redis接続（レート制限用）
try:
    redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis接続失敗（レート制限は無効）: {e}")
    redis_client = None


class SecurityConfig:
    """セキュリティ設定クラス"""
    
    # レート制限設定
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_REQUESTS_PER_HOUR = 1000
    
    # IP制限設定
    ALLOWED_IPS = []  # 本番では管理者IPなど
    BLOCKED_IPS = []  # 問題のあるIP
    
    # セキュリティヘッダー設定
    SECURITY_HEADERS = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self' https:",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }


def setup_security_headers(app):
    """セキュリティヘッダーの設定"""
    
    @app.after_request
    def add_security_headers(response):
        """レスポンスにセキュリティヘッダーを追加"""
        if os.getenv('SECURITY_HEADERS', 'true').lower() == 'true':
            for header, value in SecurityConfig.SECURITY_HEADERS.items():
                response.headers[header] = value
        return response
    
    # HTTPS強制リダイレクト
    if os.getenv('FORCE_HTTPS', 'false').lower() == 'true':
        @app.before_request
        def force_https():
            """HTTPS強制リダイレクト"""
            if not request.is_secure and 'localhost' not in request.host:
                return redirect(request.url.replace('http://', 'https://'))


def is_valid_ip(ip_str):
    """IPアドレスの妥当性チェック"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_ip_allowed(ip_str):
    """IPアドレスが許可されているかチェック"""
    if not is_valid_ip(ip_str):
        return False
    
    # ブロックリストチェック
    if ip_str in SecurityConfig.BLOCKED_IPS:
        return False
    
    # 許可リスト設定されている場合はホワイトリスト型
    if SecurityConfig.ALLOWED_IPS:
        return ip_str in SecurityConfig.ALLOWED_IPS
    
    # 許可リスト未設定の場合は基本的に全許可
    return True


def rate_limit(key_func=None, max_requests=None, window_size=60):
    """レート制限デコレータ"""
    if not redis_client:
        # Redisが使用できない場合はスキップ
        return lambda fn: fn
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # クライアント識別子を取得
            if key_func:
                client_id = key_func()
            else:
                client_id = request.remote_addr
            
            # ウィンドウサイズを秒で設定
            key = f"rate_limit:{client_id}:{func.__name__}"
            
            # 現在のリクエスト数を取得
            current_requests = redis_client.get(key)
            if current_requests is None:
                # 新しいウィンドウ
                redis_client.setex(key, window_size, 1)
            else:
                current_requests = int(current_requests)
                if current_requests >= max_requests:
                    logger.warning(f"Rate limit exceeded for {client_id} on {func.__name__}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': window_size
                    }), 429
                
                # インクリメント
                redis_client.incr(key)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_security_event(event_type, details, severity="info"):
    """セキュリティイベントをログ記録"""
    
    def get_event_logger(level):
        log_messages = {
            "debug": lambda msg: logger.debug(msg),
            "info": lambda msg: logger.info(msg),
            "warning": lambda msg: logger.warning(msg),
            "error": lambda msg: logger.error(msg)
        }
        return log_messages.get(level, logger.info)
    
    log_message = f"SECURITY_EVENT [{severity.upper()}] {event_type}: {details}"
    get_event_logger(severity)(log_message)
    
    # 重要なセキュリティイベントはSlack通知も検討
    if severity in ["warning", "error"]:
        # TODO: Slack通知の実装
        pass


def validate_user_input(data, rules):
    """ユーザー入力のバリデーション"""
    errors = []
    
    for field, rule_data in rules.items():
        value = data.get(field)
        field_rules = rule_data if isinstance(rule_data, list) else [rule_data]
        
        for rule in field_rules:
            if rule == 'required' and (value is None or value == ''):
                errors.append(f"Field {field} is required")
            elif rule == 'email' and value and '@' not in value:
                errors.append(f"Field {field} must be a valid email")
            elif rule == 'password' and value and len(value) < 8:
                errors.append(f"Field {field} must be at least 8 characters")
            elif isinstance(rule, dict):
                if 'min_length' in rule and len(str(value)) < rule['min_length']:
                    errors.append(f"Field {field} must be at least {rule['min_length']} characters")
                if 'max_length' in rule and len(str(value)) > rule['max_length']:
                    errors.append(f"Field {field} must not exceed {rule['max_length']} characters")
    
    return errors


def sanitize_log_data(data):
    """ログに出力する前にセンシティブなデータをマスキング"""
    sensitive_keys = [
        'password', 'token', 'key', 'secret', 'authorization',
        'stripe_secret_key', 'webhook_secret', 'api_key'
    ]
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***MASKED***'
            elif isinstance(value, dict):
                sanitized[key] = sanitize_log_data(value)
            else:
                sanitized[key] = value
        return sanitized
    
    return data


def create_hash(input_string, algorithm='sha256'):
    """入力文字列のハッシュを生成"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(input_string.encode('utf-8'))
    return hash_obj.hexdigest()


# アプリケーションルートでのセキュリティチェック
def setup_app_security(app):
    """アプリケーション全体のセキュリティ設定"""
    
    @app.before_request
    def before_request():
        """リクエスト前のセキュリティチェック"""
        
        # IP制限チェック
        client_ip = request.remote_addr
        if not is_ip_allowed(client_ip):
            log_security_event("blocked_ip_access", f"Blocked IP {client_ip} attempted access")
            return jsonify({'error': 'Access denied'}), 403
        
        # リクエストデータのログ（マスキング済み）
        if os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true':
            safe_data = sanitize_log_data(dict(request.args))
            log_security_event("request_log", f"{request.method} {request.path} from {client_ip}: {safe_data}")
    
    # セキュリティヘッダー設定
    setup_security_headers(app)


# 管理者専用エンドポイント保護
def admin_required(f):
    """管理者権限が必要なデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: 実際の管理者認証ロジックを実装
        # 後でJWT、OAuth、セッション認証などに置き換え
        is_admin = False  # 仮実装
        
        if not is_admin:
            log_security_event("unauthorized_admin_access", f"Access denied to admin endpoint")
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# APIキー認証（サービス間通信用）
def api_key_required(f):
    """APIキー認証が必要なデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('INTERNAL_API_KEY')
        
        if not api_key or api_key != expected_key:
            log_security_event("invalid_api_key", f"Invalid API key attempted")
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function
