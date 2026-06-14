"""
routes/nin.py
NIN (National ID) Verification Routes
Handles NIN submission, verification status, and admin management.
"""

from flask import Blueprint, request, jsonify, session
from models.user import User
from models.audit import AuditLog
from services.nin_service import nin_service
from utils.decorators import login_required, admin_required
from extensions import db
from datetime import datetime

nin_bp = Blueprint('nin', __name__, url_prefix='/api/nin')


# ─────────────────────────────────────────────
# POST /api/nin/verify
# Submit NIN for verification (basic or with photo)
# ─────────────────────────────────────────────
@nin_bp.route('/verify', methods=['POST'])
@login_required
def verify_nin():
    """
    Verify user's NIN.
    Accepts: nin, date_of_birth, selfie (optional base64 image).
    Returns verification result and updates user record.
    """
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Already verified — no need to re-verify
        if user.nin_verified:
            return jsonify({
                'message': 'NIN already verified',
                'nin_verified': True,
                'verification_level': user.get_verification_level()
            }), 200

        data = request.json or {}
        nin = data.get('nin', '').strip()
        date_of_birth = data.get('date_of_birth', '').strip()
        selfie_base64 = data.get('selfie')          # optional

        # ── Validate inputs ──────────────────────────────────────────
        if not nin:
            return jsonify({'error': 'NIN is required'}), 400

        if len(nin) != 11 or not nin.isdigit():
            return jsonify({'error': 'NIN must be exactly 11 digits'}), 400

        if not date_of_birth:
            return jsonify({'error': 'Date of birth is required'}), 400

        # ── Duplicate-NIN check ──────────────────────────────────────
        nin_hash = nin_service.hash_nin(nin)
        if User.check_nin_duplicate(nin_hash):
            return jsonify({
                'error': 'This NIN is already registered with another account'
            }), 400

        # ── Extract name parts for validation ───────────────────────
        name_parts = user.full_name.strip().split()
        first_name = name_parts[0] if name_parts else ''
        last_name  = name_parts[-1] if len(name_parts) > 1 else name_parts[0]

        # ── Call appropriate Korapay endpoint ────────────────────────
        if selfie_base64:
            result = nin_service.verify_nin_with_photo(
                nin=nin,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                selfie_base64=selfie_base64
            )
        else:
            result = nin_service.verify_nin_with_data(
                nin=nin,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth
            )

        if not result.get('success'):
            return jsonify({
                'error': result.get('error', 'NIN verification failed'),
                'nin_verified': False
            }), 400

        # ── Decide whether we consider this "verified" ────────────────
        validation = result.get('validation', {})
        nin_data   = result.get('data', {})

        data_matched  = validation.get('all_match') or (
            validation.get('first_name_match') and validation.get('last_name_match')
        )
        photo_matched = validation.get('photo_match', False)
        photo_score   = int(validation.get('photo_confidence', 0))

        overall_verified = data_matched  # photo is a bonus, not a blocker

        if not overall_verified:
            return jsonify({
                'error': 'NIN details do not match your account information. '
                         'Please ensure your name and date of birth match your NIN records.',
                'nin_verified': False,
                'validation': {
                    'first_name_match': validation.get('first_name_match'),
                    'last_name_match':  validation.get('last_name_match'),
                    'dob_match':        validation.get('dob_match'),
                }
            }), 400

        # ── Persist verified NIN data ─────────────────────────────────
        user.nin_hash                  = nin_hash
        user.nin_verified              = True
        user.nin_verified_at           = datetime.utcnow()
        user.nin_verification_reference = nin_data.get('reference', '')
        user.nin_data_matched          = data_matched
        user.nin_photo_matched         = photo_matched
        user.nin_photo_match_score     = photo_score

        # Store government-supplied name fields (useful for admin review)
        user.nin_first_name  = nin_data.get('firstname') or nin_data.get('first_name', '')
        user.nin_last_name   = nin_data.get('lastname')  or nin_data.get('last_name', '')
        user.nin_middle_name = nin_data.get('middlename') or nin_data.get('middle_name', '')
        user.nin_gender      = nin_data.get('gender', '')
        user.nin_state_of_origin = nin_data.get('state_of_origin', '')

        db.session.commit()

        AuditLog.log_action(
            user_id=user.id,
            action='NIN_VERIFIED',
            resource_type='user',
            resource_id=user.id,
            details={
                'data_matched':  data_matched,
                'photo_matched': photo_matched,
                'photo_score':   photo_score,
                'has_selfie':    bool(selfie_base64),
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'message': 'NIN verified successfully! You are now eligible to vote.',
            'nin_verified': True,
            'verification_level': user.get_verification_level(),
            'verification_badges': user.get_verification_badges(),
            'details': {
                'data_matched':         data_matched,
                'photo_matched':        photo_matched,
                'photo_match_score':    photo_score,
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[NIN VERIFY] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# GET /api/nin/status
# Return current NIN verification status
# ─────────────────────────────────────────────
@nin_bp.route('/status', methods=['GET'])
@login_required
def nin_status():
    """Return the current NIN verification status for the logged-in user."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        can_vote, vote_reason = user.can_vote()

        return jsonify({
            'nin_verified':          user.nin_verified,
            'nin_verified_at':       user.nin_verified_at.isoformat() if user.nin_verified_at else None,
            'nin_data_matched':      user.nin_data_matched,
            'nin_photo_matched':     user.nin_photo_matched,
            'nin_photo_match_score': user.nin_photo_match_score,
            'verification_level':    user.get_verification_level(),
            'verification_badges':   user.get_verification_badges(),
            'can_vote':              can_vote,
            'vote_eligibility_reason': vote_reason,
            # Tell the frontend what is still needed
            'requirements': {
                'email_verified': user.email_verified,
                'nin_verified':   user.nin_verified,
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# POST /api/nin/check-duplicate
# Public helper – check if a NIN hash is taken
# (used during registration before full verify)
# ─────────────────────────────────────────────
@nin_bp.route('/check-duplicate', methods=['POST'])
@login_required
def check_nin_duplicate():
    """
    Check whether a NIN is already registered.
    Accepts: nin (plain text – hashed server-side, never stored plain).
    """
    try:
        data = request.json or {}
        nin  = data.get('nin', '').strip()

        if not nin or len(nin) != 11 or not nin.isdigit():
            return jsonify({'error': 'Valid 11-digit NIN required'}), 400

        nin_hash   = nin_service.hash_nin(nin)
        is_taken   = User.check_nin_duplicate(nin_hash)

        return jsonify({'is_duplicate': is_taken}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Admin routes
# ─────────────────────────────────────────────

@nin_bp.route('/admin/unverified', methods=['GET'])
@admin_required
def admin_list_unverified():
    """List users who have not yet verified their NIN."""
    try:
        users = User.query.filter_by(nin_verified=False, is_active=True).all()
        return jsonify({
            'count': len(users),
            'users': [u.get_full_verification_status() for u in users]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@nin_bp.route('/admin/verified', methods=['GET'])
@admin_required
def admin_list_verified():
    """List users who have verified their NIN."""
    try:
        users = User.query.filter_by(nin_verified=True).all()
        return jsonify({
            'count': len(users),
            'users': [u.get_full_verification_status() for u in users]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@nin_bp.route('/admin/revoke/<int:user_id>', methods=['POST'])
@admin_required
def admin_revoke_nin(user_id):
    """
    Revoke a user's NIN verification (admin use only).
    Use when fraud is detected or a mistake needs correcting.
    """
    try:
        user = User.query.get_or_404(user_id)
        data = request.json or {}

        user.nin_verified              = False
        user.nin_hash                  = None
        user.nin_verified_at           = None
        user.nin_verification_reference = None
        user.nin_data_matched          = False
        user.nin_photo_matched         = False
        user.nin_photo_match_score     = None

        db.session.commit()

        AuditLog.log_action(
            user_id=session['user_id'],
            action='NIN_REVOKED',
            resource_type='user',
            resource_id=user_id,
            details={'reason': data.get('reason', 'Admin revocation'), 'target_user': user_id},
            ip_address=request.remote_addr
        )

        return jsonify({'message': f'NIN verification revoked for user {user_id}'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500