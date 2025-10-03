"""
キャッシュ機能の設定とユーティリティ
"""
import os
import json
import hashlib
import time
from functools import wraps
from datetime import datetime, timedelta
try:
    import redis
    REDIS_AVAILABLE_TRUE = True
except ImportError:
    REDIS_AVAILABLE_TRUE = False
    redis = None
import logging

logger = logging.getLogger(__name__)

# Redis接続
try:
    redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    redis_client.ping()
    CACHE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis接続失敗（キャッシュは無効）: {e}")
    redis_client = None
    CACHE_AVAILABLE = False


class CacheService:
    """キャッシュサービス"""
    
    CACHE_DEFAULT_TTL = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))  # 5分
    CACHE_PREFIX = os.getenv('CACHE_PREFIX', 'stripe_gym')
    
    @staticmethod
    def _generate_cache_key(*args, **kwargs):
        """キャッシュキーの生成"""
        # 引数から一意なキーを生成
        key_data = f"{args}{sorted(kwargs.items())}"
        return f"{CacheService.CACHE_PREFIX}:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    @staticmethod
    def get(key_prefix, *args, **kwargs):
        """キャッシュから値取得"""
        if not CACHE_AVAILABLE:
            return None
        
        try:
            cache_key = CacheService._generate_cache_key(key_prefix, *args, **kwargs)
            cached_value = redis_client.get(cache_key)
            
            if cached_value:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_value)
            else:
                logger.debug(f"Cache miss: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    def set(key_prefix, value, ttl=None, *args, **kwargs):
        """キャッシュに値保存"""
        if not CACHE_AVAILABLE:
            return False
        
        try:
            cache_key = CacheService._generate_cache_key(key_prefix, *args, **kwargs)
            serialized_value = json.dumps(value, default=str)
            cache_ttl = ttl or CacheService.CACHE_DEFAULT_TTL
            
            redis_client.setex(cache_key, cache_ttl, serialized_value)
            logger.debug(f"Cache set: {cache_key} (TTL: {cache_ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    def delete(key_prefix, *args, **kwargs):
        """キャッシュから値削除"""
        if not CACHE_AVAILABLE:
            return False
        
        try:
            cache_key = CacheService._generate_cache_key(key_prefix, *args, **kwargs)
            redis_client.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    @staticmethod
    def clear_pattern(pattern):
        """パターンにマッチするキャッシュを削除"""
        if not CACHE_AVAILABLE:
            return 0
        
        try:
            keys = redis_client.keys(f"{CacheService.CACHE_PREFIX}:{pattern}")
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0


def cached(ttl=None, key_prefix=None):
    """キャッシュデコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュが無効な場合は直接実行
            if not CACHE_AVAILABLE:
                return func(*args, **kwargs)
            
            # キャッシュキーの決定
            prefix = key_prefix or func.__name__
            
            # キャッシュからの取得を試行
            cached_result = CacheService.get(prefix, *args, **kwargs)
            if cached_result is not None:
                return cached_result
            
            # キャッシュにない場合は関数実行
            result = func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            if result is not None:
                CacheService.clear_pattern(prefix)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern=None):
    """キャッシュ無効化デコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 関連するキャッシュをクリア
            if pattern:
                CacheService.clear_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator


# アプリケーション固有のキャッシュ関数
class StripeGymCache:
    """StripeGym専用キャッシュ機能"""
    
    @staticmethod
    def cache_user_data(user_id, ttl=900):  # 15分
        """ユーザーデータのキャッシュデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"user_data:{user_id}"
                cached_data = CacheService.get(cache_key)
                
                if cached_data:
                    return cached_data
                
                result = func(*args, **kwargs)
                CacheService.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def cache_subscription_data(subscription_id, ttl=1800):  # 30分
        """サブスクリプションデータのキャッシュデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"subscription:{subscription_id}"
                cached_data = CacheService.get(cache_key)
                
                if cached_data:
                    return cached_data
                
                result = func(*args, **kwargs)
                CacheService.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """ユーザー関連キャッシュの無効化"""
        CacheService.clear_pattern(f"user_data:{user_id}")
        CacheService.clear_pattern(f"user_subscriptions:{user_id}")
        logger.info(f"Cache invalidated for user: {user_id}")
    
    @staticmethod
    def invalidate_subscription_cache(subscription_id):
        """サブスクリプション関連キャッシュの無効化"""
        CacheService.clear_pattern(f"subscription:{subscription_id}")
        logger.info(f"Cache invalidated for subscription: {subscription_id}")
    
    @staticmethod
    def cache_stripe_products(ttl=3600):  # 1時間
        """Stripe商品データのキャッシュデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = "stripe_products"
                cached_data = CacheService.get(cache_key)
                
                if cached_data:
                    return cached_data
                
                result = func(*args, **kwargs)
                CacheService.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator


# パフォーマンスボトルネックの検出と最適化
class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    @staticmethod
    def track_execution_time(func_name):
        """実行時間測定デコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # 遅い処理のログ
                if execution_time > 1.0:
                    logger.warning(f"Slow operation: {func_name} took {execution_time:.2f}s")
                
                # Redisにメトリクス保存（CACHE_AVAILABLE であれば）
                if CACHE_AVAILABLE:
                    try:
                        metrics_key = f"performance_metrics:{func_name}"
                        metrics_data = {
                            'execution_time': execution_time,
                            'timestamp': datetime.now().isoformat(),
                            'function': func_name
                        }
                        redis_client.lpush(metrics_key, json.dumps(metrics_data))
                        redis_client.expire(metrics_key, 86400)  # 1日保存
                    except Exception as e:
                        logger.error(f"Performance metrics error: {e}")
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def get_performance_stats(func_name, hours=24):
        """パフォーマンス統計の取得"""
        if not CACHE_AVAILABLE:
            return None
        
        try:
            metrics_key = f"performance_metrics:{func_name}"
            metrics_data = redis_client.lrange(metrics_key, 0, -1)
            
            if not metrics_data:
                return None
            
            # 時間範囲でフィルタ
            cutoff_time = datetime.now() - timedelta(hours=hours)
            valid_metrics = []
            
            for metric_json in metrics_data:
                try:
                    metric = json.loads(metric_json)
                    metric_time = datetime.fromisoformat(metric['timestamp'])
                    
                    if metric_time >= cutoff_time:
                        valid_metrics.append(float(metric['execution_time']))
                except Exception:
                    continue
            
            if not valid_metrics:
                return None
            
            # 統計計算
            stats = {
                'count': len(valid_metrics),
                'avg_time': sum(valid_metrics) / len(valid_metrics),
                'max_time': max(valid_metrics),
                'min_time': min(valid_metrics),
                'function': func_name
            }
            
            return stats
        except Exception as e:
            logger.error(f"Performance stats error: {e}")
            return None


# データベースクエリ最適化用のキャッシュ
class QueryCache:
    """データベースクエリ専用キャッシュ"""
    
    @staticmethod
    def cache_query(query_key, ttl=300):
        """クエリ結果のキャッシュデコレータ"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"query:{query_key}:{hash(str(args) + str(kwargs))}"
                cached_result = CacheService.get(cache_key)
                
                if cached_result:
                    logger.debug(f"Query cache hit: {query_key}")
                    return cached_result
                
                result = func(*args, **kwargs)
                CacheService.set(cache_key, result, ttl)
                logger.debug(f"Query cached: {query_key}")
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_query_cache(query_pattern):
        """クエリキャッシュの無効化"""
        CacheService.clear_pattern(f"query:{query_pattern}")
        logger.info(f"Query cache invalidated: {query_pattern}")


# Flask アプリケーションのキャッシュ設定
def setup_cache_flask(app):
    """Flask アプリのキャッシュ設定"""
    
    if CACHE_AVAILABLE:
        app.config['CACHE_TYPE'] = 'redis'
        app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        app.config['CACHE_DEFAULT_TIMEOUT'] = CacheService.CACHE_DEFAULT_TTL
        
        try:
            from flask_caching import Cache
            cache = Cache(app)
            app.extensions['cache'] = cache
            
            logger.info("Flask caching enabled with Redis")
        except ImportError:
            logger.warning("Flask-Caching not installed, using basic cache")
    else:
        logger.warning("Cache not available, caching disabled")


# ヘルスチェック付きのキャッシュ状態確認
def check_cache_health():
    """キャッシュの健全性チェック"""
    health_info = {
        'cache_available': CACHE_AVAILABLE,
        'redis_connected': False,
        'test_result': False
    }
    
    if CACHE_AVAILABLE:
        try:
            # 接続テスト
            redis_client.ping()
            health_info['redis_connected'] = True
            
            # 書き込みテスト
            test_key = CacheService.CACHE_PREFIX + ':health_test'
            test_value = {'test': True, 'timestamp': datetime.now().isoformat()}
            
            CacheService.set(test_key, test_value, 60)
            retrieved_value = CacheService.get(test_key)
            
            health_info['test_result'] = retrieved_value == test_value
            
            # テストデータクリーンアップ
            CacheService.delete(test_key)
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            health_info['error'] = str(e)
    
    return health_info
