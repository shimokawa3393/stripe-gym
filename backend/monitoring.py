"""
監視・ログ・エラー通知システム
"""
import os
import logging
import logging.handlers
import json
import requests
import traceback
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# ロガー設定
def setup_logging(app):
    """ログ設定の初期化"""
    
    # ログレベル設定
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    
    # フォーマッター設定
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)8s] %(name)s: %(message)s [%(filename)s:%(lineno)d]'
    )
    
    # ファイルログハンドラ設定
    if not app.debug:
        # ログファイル設定
        log_file = os.getenv('LOG_FILE', '/app/logs/stripe-gym.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # ローテートファイルハンドラ
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=int(os.getenv('LOG_MAX_SIZE', 10485760)),  # 10MB
            backupCount=int(os.getenv('LOG_BACKUP_COUNT', 5))
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
    
    # コンソールハンドラ（開発時）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    app.logger.addHandler(console_handler)
    
    # ログレベル設定
    app.logger.setLevel(log_level)


class NotificationService:
    """通知サービス"""
    
    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.sentry_dsn = os.getenv('SENTRY_DSN')
        self.max_notifications_per_hour = int(os.getenv('MAX_ERROR_NOTIFICATIONS_PER_HOUR', '5'))
        self.throttle_seconds = int(os.getenv('NOTIFICATION_THROTTLE_SECONDS', '300'))
        
        # Redis（通知頻度制限）
        try:
            self.redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
            self.redis_client.ping()
        except:
            self.redis_client = None
    
    def _is_throttled(self, notification_type):
        """通知の頻度制限チェック"""
        if not self.redis_client:
            return False
        
        key = f"notification_throttle:{notification_type}"
        current_count = self.redis_client.get(key)
        
        if current_count is None:
            # 新しい時間枠
            self.redis_client.setex(key, 3600, '1')  # 1時間のウィンドウ
            return False
        else:
            current_count = int(current_count)
            if current_count >= self.max_notifications_per_hour:
                return True
            
            self.redis_client.incr(key)
            return False
    
    def _send_slack_notification(self, message, severity='info'):
        """Slack通知送信"""
        if not self.slack_webhook:
            return False
        
        if self._is_throttled(f"slack_{severity}"):
            return False
        
        # アイコンと色を重大度別に設定
        icons = {
            'info': ':information_source:',
            'warning': ':warning:',
            'error': ':x:',
            'critical': ':fire:'
        }
        
        colors = {
            'info': 'good',
            'warning': 'warning', 
            'error': 'danger',
            'critical': 'danger'
        }
        
        # Slackペイロード作成
        payload = {
            'username': 'StripeGym Monitor',
            'icon_emoji': icons.get(severity, ':robot_face:'),
            'attachments': [{
                'color': colors.get(severity, 'good'),
                'title': f'StripeGym {severity.upper()}',
                'text': message,
                'timestamp': int(datetime.now().timestamp()),
                'fields': [
                    {'title': 'Environment', 'value': os.getenv('FLASK_ENV', 'unknown'), 'short': True},
                    {'title': 'Server', 'value': request.host if request else 'unknown', 'short': True}
                ]
            }]
        }
        
        try:
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            current_app.logger.error(f"Slack通知送信失敗: {e}")
            return False
    
    def _send_sentry_error(self, error, context):
        """Sentryにエラー送信"""
        if not self.sentry_dsn:
            return False
        
        try:
            # TODO: Sentry SDKを使用（実際の実装では適切なライブラリを使用）
            current_app.logger.error(f"Sentry送信が必要: {error}")
            return True
        except Exception as e:
            current_app.logger.error(f"Sentry送信失敗: {e}")
            return False
    
    def send_notification(self, message, severity='info', context=None, include_traceback=True):
        """通知送信（Slack + Sentry）"""
        
        # コンテキスト情報の追加
        if context and isinstance(context, dict):
            context_str = '\n'.join([f"{k}: {v}" for k, v in context.items()])
            message = f"{message}\n\nコンテキスト:\n{context_str}"
        
        # スタックトレースの追加（エラー時）
        if severity in ['error', 'critical'] and include_traceback:
            tb = traceback.format_exc()
            message = f"{message}\n\nスタックトレース:\n{tb}"
        
        # ログ出力
        if severity in ['error', 'critical']:
            current_app.logger.error(message)
        elif severity == 'warning':
            current_app.logger.warning(message)
        else:
            current_app.logger.info(message)
        
        # Slack通知
        if severity in ['warning', 'error', 'critical']:
            self._send_slack_notification(message, severity)
        
        # Sentry送信
        if severity in ['error', 'critical']:
            self._send_sentry_error(message, context)
        
        return True


# グローバル通知サービス
notification_service = NotificationService()


def monitor_performance(func_name=None):
    """パフォーマンス監視デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                result = f(*args, **kwargs)
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                # 遅い処理のログ
                if execution_time > 1.0:  # 1秒以上
                    notification_service.send_notification(
                        f"Slow response detected: {func_name or f.__name__}",
                        severity='warning',
                        context={
                            'function': func_name or f.__name__,
                            'execution_time': f"{execution_time:.2f}s",
                            'request_path': request.path,
                            'request_method': request.method
                        }
                    )
                
                return result
            
            except Exception as e:
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                notification_service.send_notification(
                    f"Error in function: {func_name or f.__name__}",
                    severity='error',
                    context={
                        'function': func_name or f.__name__,
                        'execution_time': f"{execution_time:.2f}s",
                        'request_path': request.path,
                        'request_method': request.method,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
                raise
        
        return decorated_function
    return decorator


def monitor_critical_operations(f):
    """重要操作の監視デコレータ（決済、ユーザー登録等）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        operation_name = f.__name__
        
        try:
            result = f(*args, **kwargs)
            
            # 成功ログ（重要操作）
            notification_service.send_notification(
                f"Critical operation completed: {operation_name}",
                severity='info',
                context={
                    'operation': operation_name,
                    'request_path': request.path,
                    'user_id': getattr(g, 'user_id', None),
                    'ip_address': request.remote_addr
                }
            )
            
            return result
        
        except Exception as e:
            # エラーログ（重要操作）
            notification_service.send_notification(
                f"Critical operation failed: {operation_name}",
                severity='error',
                context={
                    'operation': operation_name,
                    'request_path': request.path,
                    'user_id': getattr(g, 'user_id', None),
                    'ip_address': request.remote_addr,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise
    
    return decorated_function


def monitor_stripe_operations(f):
    """Stripe操作専用監視デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        stripe_operation = f.__name__
        
        try:
            result = f(*args, **kwargs)
            
            # Stripe操作成功ログ
            notification_service.send_notification(
                f"Stripe operation successful: {stripe_operation}",
                severity='info',
                context={
                    'stripe_operation': stripe_operation,
                    'customer_id': getattr(g, 'stripe_customer_id', None),
                    'request_path': request.path
                }
            )
            
            return result
        
        except Exception as e:
            # Stripe操作エラーログ
            notification_service.send_notification(
                f"Stripe operation failed: {stripe_operation}",
                severity='error',
                context={
                    'stripe_operation': stripe_operation,
                    'customer_id': getattr(g, 'stripe_customer_id', None),
                    'request_path': request.path,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
            raise
    
    return decorated_function


def health_check():
    """ヘルスチェック用の内部監視"""
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # データベース接続チェック
    try:
        from repositories import get_session
        session = get_session()
        session.execute('SELECT 1')
        session.close()
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Redis接続チェック
    try:
        if notification_service.redis_client:
            notification_service.redis_client.ping()
            health_status['checks']['redis'] = 'ok'
        else:
            health_status['checks']['redis'] = 'disabled'
    except Exception as e:
        health_status['checks']['redis'] = f'error: {str(e)}'
    
    # Stripe API接続チェック
    try:
        import stripe
        stripe.Customer.list(limit=1)
        health_status['checks']['stripe'] = 'ok'
    except Exception as e:
        health_status['checks']['stripe'] = f'error: {str(e)}'
    
    # Slack通知チェック
    if notification_service.slack_webhook:
        health_status['checks']['slack'] = 'configured'
    else:
        health_status['checks']['slack'] = 'not_configured'
    
    # 重大度ログ
    if health_status['status'] == 'unhealthy':
        notification_service.send_notification(
            "Health check failed",
            severity='critical',
            context=health_status
        )
    
    return health_status
