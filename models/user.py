"""
models/user.py  (updated)
NIN is now required to vote (can_vote enforces it).
Email domain restriction removed (any valid email accepted).
get_verification_level reflects the new NIN-first hierarchy.
"""

from extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    # ── Core ──────────────────────────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)
    voter_id      = db.Column(db.String(50),  unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20),  default='voter')
    phone_number  = db.Column(db.String(20),  unique=True, nullable=True)
    date_of_birth = db.Column(db.Date)
    address       = db.Column(db.Text)
    custom_fields = db.Column(db.JSON)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Email verification ─────────────────────────────────────────────────
    email_verified                   = db.Column(db.Boolean, default=False)
    email_verified_at                = db.Column(db.DateTime)
    email_verification_token         = db.Column(db.String(255), unique=True)
    email_verification_token_expires = db.Column(db.DateTime)

    # ── Biometric authentication ───────────────────────────────────────────
    biometric_enabled              = db.Column(db.Boolean, default=False)
    biometric_credentials          = db.Column(db.JSON)
    pending_webauthn_challenge     = db.Column(db.String(255))
    pending_challenge_expires      = db.Column(db.DateTime)
    biometric_enrolled_at          = db.Column(db.DateTime)
    require_biometric_for_voting   = db.Column(db.Boolean, default=False)

    # ── NIN verification ───────────────────────────────────────────────────
    nin_hash                    = db.Column(db.String(64), unique=True, nullable=True, index=True)
    nin_verified                = db.Column(db.Boolean, default=False)
    nin_verified_at             = db.Column(db.DateTime)
    nin_verification_reference  = db.Column(db.String(255))
    nin_first_name              = db.Column(db.String(100))
    nin_last_name               = db.Column(db.String(100))
    nin_middle_name             = db.Column(db.String(100))
    nin_gender                  = db.Column(db.String(10))
    nin_state_of_origin         = db.Column(db.String(50))
    nin_photo_match_score       = db.Column(db.Integer)
    nin_data_matched            = db.Column(db.Boolean, default=False)
    nin_photo_matched           = db.Column(db.Boolean, default=False)

    # ── Relationships ──────────────────────────────────────────────────────
    votes             = db.relationship('Vote',     backref='voter',   lazy=True)
    elections_created = db.relationship('Election', backref='creator', lazy=True)

    # ─────────────────────────────────────────────────────────────────────
    def to_dict(self, include_biometric=False, include_nin=False):
        data = {
            'id':                 self.id,
            'voter_id':           self.voter_id,
            'full_name':          self.full_name,
            'email':              self.email,
            'role':               self.role,
            'phone_number':       self.phone_number,
            'address':            self.address,
            'custom_fields':      self.custom_fields,
            'is_active':          self.is_active,
            'is_verified':        self.email_verified,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
            'verification_level': self.get_verification_level(),
            'verification_badges': self.get_verification_badges(),
        }

        if include_biometric:
            data.update({
                'biometric_enabled':             self.biometric_enabled,
                'require_biometric_for_voting':  self.require_biometric_for_voting,
                'biometric_enrolled_at':         self.biometric_enrolled_at.isoformat()
                                                 if self.biometric_enrolled_at else None,
                'biometric_credentials_count':   len(self.biometric_credentials)
                                                 if self.biometric_credentials else 0,
            })

        if include_nin:
            # NEVER return actual NIN or nin_hash to client
            data.update({
                'nin_verified':          self.nin_verified,
                'nin_verified_at':       self.nin_verified_at.isoformat()
                                         if self.nin_verified_at else None,
                'nin_photo_match_score': self.nin_photo_match_score,
                'nin_data_matched':      self.nin_data_matched,
                'nin_photo_matched':     self.nin_photo_matched,
            })

        return data

    # ─────────────────────────────────────────────────────────────────────
    def get_verification_level(self):
        """
        Hierarchy (highest → lowest):
          'full'      – email + NIN + biometric
          'biometric' – NIN + biometric (email missing — rare edge case)
          'nin'       – email + NIN verified  ← MINIMUM TO VOTE
          'email'     – email only            ← cannot vote
          'basic'     – nothing verified      ← cannot vote
        """
        if self.biometric_enabled and self.nin_verified and self.email_verified:
            return 'full'
        if self.nin_verified and self.biometric_enabled:
            return 'biometric'
        if self.nin_verified and self.email_verified:
            return 'nin'        # ← can vote
        if self.email_verified:
            return 'email'      # ← cannot vote yet
        return 'basic'

    def get_verification_badges(self):
        badges = []

        if self.email_verified:
            badges.append({
                'type':        'email',
                'label':       'Email Verified',
                'icon':        '✉️',
                'color':       'blue',
                'verified_at': self.email_verified_at.isoformat()
                               if self.email_verified_at else None,
            })

        if self.nin_verified:
            badge = {
                'type':        'nin',
                'label':       'NIN Verified',
                'icon':        '🆔',
                'color':       'green',
                'verified_at': self.nin_verified_at.isoformat()
                               if self.nin_verified_at else None,
            }
            if self.nin_photo_match_score and self.nin_photo_match_score >= 90:
                badge['label'] = 'NIN Verified ⭐'
                badge['match_score'] = self.nin_photo_match_score
            badges.append(badge)

        if self.biometric_enabled:
            badges.append({
                'type':        'biometric',
                'label':       'Face ID Enrolled',
                'icon':        '👤',
                'color':       'purple',
                'verified_at': self.biometric_enrolled_at.isoformat()
                               if self.biometric_enrolled_at else None,
            })

        return badges

    def has_nin_verified(self):
        return self.nin_verified and self.nin_hash is not None

    def can_vote(self):
        """
        Returns (bool, str).
        All three conditions must pass for a user to cast a ballot:
          1. Account active
          2. Email verified
          3. NIN verified   ← now enforced
        Biometric is an optional add-on, not a blocker unless explicitly required.
        """
        if not self.is_active:
            return False, 'Account is deactivated'

        if not self.email_verified:
            return False, 'Email not verified. Please check your inbox.'

        # ✅ NIN is now required
        if not self.nin_verified:
            return False, (
                'NIN verification required. '
                'Please verify your National Identification Number in your profile.'
            )

        if self.require_biometric_for_voting and not self.biometric_enabled:
            return False, 'Biometric enrollment required for this account.'

        return True, 'Eligible to vote'

    def get_full_verification_status(self):
        """Full status dict for admin views."""
        can, reason = self.can_vote()
        return {
            'user_id':              self.id,
            'voter_id':             self.voter_id,
            'full_name':            self.full_name,
            'email_verified':       self.email_verified,
            'email_verified_at':    self.email_verified_at.isoformat()
                                    if self.email_verified_at else None,
            'biometric_enabled':    self.biometric_enabled,
            'biometric_enrolled_at': self.biometric_enrolled_at.isoformat()
                                    if self.biometric_enrolled_at else None,
            'nin_verified':         self.nin_verified,
            'nin_verified_at':      self.nin_verified_at.isoformat()
                                    if self.nin_verified_at else None,
            'nin_data_matched':     self.nin_data_matched,
            'nin_photo_matched':    self.nin_photo_matched,
            'nin_photo_match_score': self.nin_photo_match_score,
            'verification_level':   self.get_verification_level(),
            'can_vote':             can,
            'vote_eligibility_reason': reason,
        }

    @staticmethod
    def validate_email(email):
        """Validate any standard email address (domain-agnostic)."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))

    @staticmethod
    def check_nin_duplicate(nin_hash):
        return User.query.filter_by(nin_hash=nin_hash).first() is not None