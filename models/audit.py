from extensions import db
from datetime import datetime

class AuditLog(db.Model):
    """Dynamic audit trail for all system actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None, ip_address=None):
        """Log an audit action"""
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
        db.session.add(audit)
        db.session.commit()
        return audit
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class SystemConfiguration(db.Model):
    """Dynamic system-wide configurations"""
    __tablename__ = 'system_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(50))  # string, integer, boolean, json
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MLModelConfiguration(db.Model):
    """Dynamic ML model configurations"""
    __tablename__ = 'ml_model_configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(50))  # isolation_forest, random_forest, etc.
    is_active = db.Column(db.Boolean, default=False)
    parameters = db.Column(db.JSON)  # Model hyperparameters
    threshold_config = db.Column(db.JSON)  # Dynamic thresholds
    feature_weights = db.Column(db.JSON)  # Feature importance weights
    training_date = db.Column(db.DateTime)
    accuracy_metrics = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert ML configuration to dictionary"""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'is_active': self.is_active,
            'parameters': self.parameters,
            'threshold_config': self.threshold_config,
            'feature_weights': self.feature_weights,
            'training_date': self.training_date.isoformat() if self.training_date else None,
            'accuracy_metrics': self.accuracy_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }