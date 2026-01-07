from extensions import db
from datetime import datetime

class User(db.Model):
    """Dynamic user model with customizable fields and biometric support"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='voter')
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.Text)
    custom_fields = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime)
    email_verification_token = db.Column(db.String(255), unique=True)
    email_verification_token_expires = db.Column(db.DateTime)
    
    # 🔐 BIOMETRIC AUTHENTICATION FIELDS
    biometric_enabled = db.Column(db.Boolean, default=False)
    biometric_credentials = db.Column(db.JSON)  # Stores WebAuthn credentials
    pending_webauthn_challenge = db.Column(db.String(255))  # Temporary challenge
    pending_challenge_expires = db.Column(db.DateTime)
    biometric_enrolled_at = db.Column(db.DateTime)
    require_biometric_for_voting = db.Column(db.Boolean, default=False)  # Optional: enforce biometric
    
    # Relationships
    votes = db.relationship('Vote', backref='voter', lazy=True)
    elections_created = db.relationship('Election', backref='creator', lazy=True)
    
    def to_dict(self, include_biometric=False):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'voter_id': self.voter_id,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'phone_number': self.phone_number,
            'address': self.address,
            'custom_fields': self.custom_fields,
            'is_active': self.is_active,
            'is_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_biometric:
            data['biometric_enabled'] = self.biometric_enabled
            data['require_biometric_for_voting'] = self.require_biometric_for_voting
            data['biometric_enrolled_at'] = self.biometric_enrolled_at.isoformat() if self.biometric_enrolled_at else None
            # Return number of credentials, not the credentials themselves
            data['biometric_credentials_count'] = len(self.biometric_credentials) if self.biometric_credentials else 0
        
        return data
    
    @staticmethod
    def validate_email_domain(email):
        """Validate email domain"""
        from utils.config_helper import is_valid_fuoye_email
        return is_valid_fuoye_email(email)