from extensions import db
from datetime import datetime

class Election(db.Model):
    """Dynamic elections - multiple elections can be created"""
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    allow_multiple_positions = db.Column(db.Boolean, default=True)
    require_voter_verification = db.Column(db.Boolean, default=True)
    max_votes_per_position = db.Column(db.Integer, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    require_biometric = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    positions = db.relationship('Position', backref='election', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='election', lazy=True)
    
    def to_dict(self, include_positions=False):
        """Convert election to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'allow_multiple_positions': self.allow_multiple_positions,
            'require_voter_verification': self.require_voter_verification,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'positions_count': len(self.positions)
        }
        
        if include_positions:
            data['positions'] = [pos.to_dict(include_candidates=True) for pos in self.positions if pos.is_active]
        
        return data


class Position(db.Model):
    """Dynamic positions/categories within elections"""
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    max_candidates_to_select = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidates = db.relationship('Candidate', backref='position', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_candidates=False):
        """Convert position to dictionary"""
        data = {
            'id': self.id,
            'election_id': self.election_id,
            'title': self.title,
            'description': self.description,
            'display_order': self.display_order,
            'max_candidates_to_select': self.max_candidates_to_select,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_candidates:
            data['candidates'] = [c.to_dict() for c in self.candidates if c.is_active]
        
        return data


class Candidate(db.Model):
    """Dynamic candidates with customizable attributes"""
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100))
    biography = db.Column(db.Text)
    manifesto = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    social_media = db.Column(db.JSON)  # Dynamic social links
    custom_fields = db.Column(db.JSON)  # Dynamic additional fields
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    votes = db.relationship('Vote', backref='candidate', lazy=True)
    
    def to_dict(self, include_vote_count=False):
        """Convert candidate to dictionary"""
        data = {
            'id': self.id,
            'position_id': self.position_id,
            'name': self.name,
            'party': self.party,
            'biography': self.biography,
            'manifesto': self.manifesto,
            'image_url': self.image_url,
            'video_url': self.video_url,
            'social_media': self.social_media,
            'custom_fields': self.custom_fields,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_vote_count:
            data['vote_count'] = len([v for v in self.votes if not v.is_flagged])
        
        return data