"""
routes/voting.py  (updated)
– NIN verification is now a hard requirement before any vote is accepted.
– Biometric remains an optional / per-election layer on top.
"""

from flask import Blueprint, request, jsonify, session
from models.user import User
from models.vote import Vote
from models.election import Election
from models.audit import AuditLog
from services.biometric_service import biometric_service
from utils.decorators import login_required
from extensions import db
from datetime import datetime

voting_bp = Blueprint('voting', __name__, url_prefix='/api/voting')


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _nin_gate(user):
    """
    Return (blocked: bool, response) where response is a ready jsonify()
    call when blocked=True.  Call this at the top of every voting endpoint.
    """
    if not user.nin_verified:
        return True, jsonify({
            'error': 'NIN verification required to vote. '
                     'Please verify your National ID in your profile.',
            'nin_required': True,
            'redirect': '/profile'          # frontend can use this hint
        }), 403
    return False, None, None


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/voting/verify-biometric
# ─────────────────────────────────────────────────────────────────────────────
@voting_bp.route('/verify-biometric', methods=['POST'])
@login_required
def verify_biometric_for_vote():
    """Verify biometric before allowing vote (NIN must already be verified)."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # ── NIN gate ──────────────────────────────────────────────────
        blocked, resp, code = _nin_gate(user)
        if blocked:
            return resp, code

        if user.require_biometric_for_voting and not user.biometric_enabled:
            return jsonify({
                'error': 'Biometric authentication required but not set up.'
            }), 403

        assertion_data = request.json or {}
        success, message = biometric_service.verify_authentication(user, assertion_data)

        if success:
            session['biometric_verified']    = True
            session['biometric_verified_at'] = datetime.utcnow().isoformat()
            session['biometric_credential_id'] = assertion_data.get('id')

            return jsonify({
                'success': True,
                'message': 'Biometric verified. You may now vote.',
                'verified': True
            }), 200
        else:
            return jsonify({'success': False, 'error': message, 'verified': False}), 401

    except Exception as e:
        print(f"[VOTING] Biometric verify error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/voting/submit
# ─────────────────────────────────────────────────────────────────────────────
@voting_bp.route('/submit', methods=['POST'])
@login_required
def submit_vote():
    """
    Cast a vote.
    Requirements (in order):
      1. Email verified
      2. NIN verified          ← NEW hard requirement
      3. Biometric (if election or user setting requires it)
      4. Not already voted for this position
    """
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # ── 1. Full can_vote check (email + NIN + active) ─────────────
        can_vote, reason = user.can_vote()
        if not can_vote:
            return jsonify({
                'error': reason,
                'nin_required':   not user.nin_verified,
                'email_required': not user.email_verified,
                'redirect': '/profile' if not user.nin_verified else None
            }), 403

        data        = request.json or {}
        election_id = data.get('election_id')
        candidate_id = data.get('candidate_id')
        position_id  = data.get('position_id')

        if not all([election_id, candidate_id, position_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        election = Election.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404

        if not election.is_active:
            return jsonify({'error': 'This election is not currently active'}), 400

        # ── 2. Biometric check (optional layer) ───────────────────────
        biometric_verified = False
        credential_id      = None
        verification_method = 'nin_password'   # default — NIN is now baseline

        requires_biometric = (
            user.require_biometric_for_voting or
            getattr(election, 'require_biometric', False)
        )

        if requires_biometric:
            if not user.biometric_enabled:
                return jsonify({
                    'error': 'Biometric authentication required but not set up. '
                             'Please enroll in your profile.',
                    'requires_biometric': True,
                    'needs_setup': True
                }), 403

            if not session.get('biometric_verified'):
                return jsonify({
                    'error': 'Biometric verification required before voting.',
                    'requires_biometric': True
                }), 403

            # Expiry check (5 minutes)
            verified_at = datetime.fromisoformat(session['biometric_verified_at'])
            if (datetime.utcnow() - verified_at).total_seconds() > 300:
                session.pop('biometric_verified', None)
                return jsonify({
                    'error': 'Biometric session expired. Please verify again.',
                    'requires_biometric': True
                }), 403

            biometric_verified  = True
            credential_id       = session.get('biometric_credential_id')
            verification_method = 'nin_biometric'

        # ── 3. Duplicate-vote check ───────────────────────────────────
        if Vote.query.filter_by(
            user_id=user.id,
            election_id=election_id,
            position_id=position_id
        ).first():
            return jsonify({'error': 'You have already voted for this position'}), 400

        # ── 4. Record vote ────────────────────────────────────────────
        new_vote = Vote(
            election_id=election_id,
            user_id=user.id,
            candidate_id=candidate_id,
            position_id=position_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            # NIN fields
            nin_verified=user.nin_verified,
            nin_verification_reference=user.nin_verification_reference,
            # Biometric fields
            biometric_verified=biometric_verified,
            biometric_credential_id=credential_id,
            biometric_verified_at=datetime.utcnow() if biometric_verified else None,
            verification_method=verification_method,
            # Fraud-detection metadata
            device_fingerprint=data.get('device_fingerprint'),
            session_duration=data.get('session_duration'),
            mouse_movements=data.get('mouse_movements'),
            keystroke_patterns=data.get('keystroke_patterns'),
        )

        db.session.add(new_vote)
        db.session.commit()

        # Clear biometric session flag
        for k in ('biometric_verified', 'biometric_verified_at', 'biometric_credential_id'):
            session.pop(k, None)

        AuditLog.log_action(
            user_id=user.id,
            action='VOTE_SUBMITTED',
            resource_type='vote',
            resource_id=new_vote.id,
            details={
                'election_id':        election_id,
                'position_id':        position_id,
                'nin_verified':       user.nin_verified,
                'biometric_verified': biometric_verified,
                'verification_method': verification_method,
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Vote submitted successfully',
            'vote_id': new_vote.id,
            'biometric_verified': biometric_verified,
            'nin_verified': user.nin_verified,
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"[VOTING] Submit error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/voting/check-requirements/<election_id>
# ─────────────────────────────────────────────────────────────────────────────
@voting_bp.route('/check-requirements/<int:election_id>', methods=['GET'])
@login_required
def check_voting_requirements(election_id):
    """
    Return everything the frontend needs to decide what to show before the ballot.
    Now includes NIN status as a primary field.
    """
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        election = Election.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404

        can_vote, vote_reason = user.can_vote()

        requires_biometric = (
            user.require_biometric_for_voting or
            getattr(election, 'require_biometric', False)
        )

        return jsonify({
            # ── NIN (primary gate) ──────────────────────────────────
            'nin_verified':         user.nin_verified,
            'nin_required':         True,           # always required now
            'can_vote':             can_vote,
            'vote_eligibility_reason': vote_reason,

            # ── Biometric (secondary, optional per election) ────────
            'requires_biometric':              requires_biometric,
            'election_requires_biometric':     getattr(election, 'require_biometric', False),
            'user_requires_biometric':         user.require_biometric_for_voting,
            'biometric_enabled':               user.biometric_enabled,
            'biometric_verified_in_session':   session.get('biometric_verified', False),
            'needs_biometric_setup':           requires_biometric and not user.biometric_enabled,

            # ── Email ───────────────────────────────────────────────
            'email_verified': user.email_verified,

            # ── Election info ───────────────────────────────────────
            'election': {
                'id':       election.id,
                'title':    election.title,
                'is_active': election.is_active,
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500