"""
Updated Vote Model with Biometric Verification Support
"""

from extensions import db
from datetime import datetime

class Vote(db.Model):
    """Dynamic vote records with biometric verification"""
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Fraud detection metadata
    ip_address = db.Column(db.String(50))
    device_fingerprint = db.Column(db.String(255))
    session_duration = db.Column(db.Integer)
    mouse_movements = db.Column(db.Integer)
    keystroke_patterns = db.Column(db.Integer)
    user_agent = db.Column(db.String(255))
    geo_location = db.Column(db.JSON)
    
    # 🔐 BIOMETRIC VERIFICATION
    biometric_verified = db.Column(db.Boolean, default=False)
    biometric_credential_id = db.Column(db.String(255))  # Which credential was used
    biometric_verified_at = db.Column(db.DateTime)
    verification_method = db.Column(db.String(50))  # 'face_id', 'touch_id', 'password'
    
    # ML detection results
    is_flagged = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.String(20))
    anomaly_score = db.Column(db.Float)
    detection_features = db.Column(db.JSON)
    
    def to_dict(self):
        """Convert vote to dictionary"""
        return {
            'id': self.id,
            'election_id': self.election_id,
            'user_id': self.user_id,
            'candidate_id': self.candidate_id,
            'position_id': self.position_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'biometric_verified': self.biometric_verified,
            'verification_method': self.verification_method,
            'is_flagged': self.is_flagged,
            'risk_level': self.risk_level,
            'anomaly_score': self.anomaly_score
        }


class FlaggedActivity(db.Model):
    """Dynamic flagged activities tracking"""
    __tablename__ = 'flagged_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    vote_id = db.Column(db.Integer, db.ForeignKey('votes.id'))
    voter_id = db.Column(db.String(50))
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    risk_level = db.Column(db.String(20))
    anomaly_score = db.Column(db.Float)
    reasons = db.Column(db.JSON)
    extra_metadata = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    
    def to_dict(self):
        """Convert flagged activity to dictionary"""
        return {
            'id': self.id,
            'vote_id': self.vote_id,
            'voter_id': self.voter_id,
            'election_id': self.election_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'risk_level': self.risk_level,
            'anomaly_score': self.anomaly_score,
            'reasons': self.reasons,
            'extra_metadata': self.extra_metadata,
            'ip_address': self.ip_address,
            'resolved': self.resolved,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes
        }