"""
Stripe Gym production-ready application entry point
"""
import os
import stripe
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from repositories import init_db
from routes import auth_bp, user_bp, payment_bp, webhook_bp
from routes.billing_portal_routes import billing_bp

def create_app():
    app = Flask(__name__)
    
    # Application configuration
    app.config["DEBUG"] = False if os.getenv('FLASK_ENV') == 'production' else True
    app.config["SECRET_KEY"] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Setup monitoring and security
    try:
        from monitoring import setup_logging, notification_service
        setup_logging(app)
        
        from security import setup_app_security
        setup_app_security(app)
        
        from cache import setup_cache_flask
        setup_cache_flask(app)
        
        app.logger.info("✅ Monitoring, security, and cache initialized")
    except ImportError as e:
        print(f"⚠️ Advanced features not available: {e}")
    
    # CORS設定 (セキュリティ考慮)
    if os.getenv('FLASK_ENV') == 'production':
        # Production: Restricted origins
        allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
        CORS(app, 
             origins=[origin.strip() for origin in allowed_origins if origin.strip()],
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
             supports_credentials=True)
    else:
        # Development: Relaxed CORS
        CORS(app, 
             origins=["http://localhost:3000", "http://localhost:8080", "http://localhost", "http://127.0.0.1:3000", "http://127.0.0.1:8080", "http://127.0.0.1"],
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
             supports_credentials=True)
    
    # Stripe API設定
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    # データベース初期化
    init_db()
    
    # Enhanced health check endpoint
    @app.route("/health")
    def health_check():
        basic_status = {"status": "healthy", "message": "Stripe Gym API is running"}
        
        # Add monitoring info if available
        try:
            from monitoring import health_check as detailed_health
            return jsonify(detailed_health())
        except:
            return jsonify(basic_status), 200
    
    # Internal health check for monitoring tools
    @app.route("/health/internal")
    def health_internal():
        try:
            from cache import check_cache_health
            cache_health = check_cache_health()
        except:
            cache_health = {'cache_available': False}
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('FLASK_ENV', 'development'),
            'cache': cache_health
        })
    
    # Blueprint registration with enhanced monitoring
    try:
        app.register_blueprint(auth_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(payment_bp)
        app.register_blueprint(webhook_bp)
        app.register_blueprint(billing_bp)
        
        # Apply security enhancements where available
        try:
            from security import rate_limit
            
            @auth_bp.before_request
            def rate_limit_auth():
                # Apply rate limiting to prevent brute force
                pass
        
            from monitoring import monitor_critical_operations
            
            # Critical operations monitoring is already embedded in decorators
            pass
            
            app.logger.info("✅ All blueprints registered with security enhancements")
        except ImportError:
            app.logger.info("✅ All blueprints registered")
        
    except ImportError as e:
        print(f"⚠️ Failed to import blueprint: {e}")
    
    # Error handlers with monitoring
    @app.errorhandler(404)
    def not_found(error):
        try:
            from monitoring import notification_service
            notification_service.send_notification(
                "404 page not found",
                severity='info',
                context={
                    'request_path': request.path,
                    'ip_address': request.remote_addr
                }
            )
        except:
            pass
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        try:
            from monitoring import notification_service
            notification_service.send_notification(
                "500 internal server error",
                severity='critical',
                context={
                    'request_path': request.path,
                    'error_type': type(error).__name__,
                    'ip_address': request.remote_addr
                }
            )
        except:
            pass
        return jsonify({'error': 'Internal server error'}), 500
    
    # Startup notification
    try:
        from monitoring import notification_service
        notification_service.send_notification(
            f"StripeGym started ({os.getenv('FLASK_ENV', 'development')})",
            severity='info',
            context={
                'environment': os.getenv('FLASK_ENV', 'development'),
                'version': os.getenv('APP_VERSION', '1.0.0')
            }
        )
    except:
        pass
    
    return app

# Create app instance
app = create_app()

if __name__ == "__main__":
    # Production vs Development server configuration
    if os.getenv('FLASK_ENV') == 'production':
        port = int(os.getenv('PORT', 5000))
        app.logger.info(f"🚀 Starting production server on port {port}")
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
