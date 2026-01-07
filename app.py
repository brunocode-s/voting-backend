from flask import Flask, jsonify
from datetime import datetime
import os

from config import config
from extensions import init_extensions, db
from services.blockchain_service import blockchain_service


def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)

    # Initialize blockchain service (if enabled)
    with app.app_context():
        if app.config.get('BLOCKCHAIN_ENABLED', False):
            print("[APP] Initializing blockchain service...")
            blockchain_service.initialize()
        else:
            print("[APP] Blockchain service disabled")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    register_health_check(app)
    
    # # Create database tables
    # with app.app_context():
    #     db.create_all()
    
    return app


def register_blueprints(app):
    """Register all blueprints"""
    from routes.auth import auth_bp
    from routes.elections import elections_bp
    from routes.voting import voting_bp
    from routes.admin import admin_bp
    from routes.results import results_bp
    from routes.biometric import biometric_bp 
    from routes.biometric import biometric_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(elections_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(biometric_bp)


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Access forbidden'}), 403
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized access'}), 401


def register_health_check(app):
    """Register health check endpoint"""
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        from models.election import Election
        from services.fraud_detection import fraud_detector
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'ml_model_loaded': fraud_detector.is_trained,
            'active_elections': Election.query.filter_by(is_active=True).count(),
            'blockchain': {
                'enabled': blockchain_service.is_enabled(),
                'connected': blockchain_service._initialized
            }
        })


# Create the Flask app
app = create_app()


if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT']
    )
