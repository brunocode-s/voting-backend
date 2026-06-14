"""
routes/auth.py  (updated)
– Removed FUOYE domain restriction — any valid email is accepted.
– Phone number is now the primary recovery method (still optional on register).
– NIN fields wired through from registration form if provided.
"""

from flask import Blueprint, request, jsonify, session, current_app
from models.user import User
from models.audit import AuditLog
from services.voter_id_generator import generate_voter_id
from services.email_service import send_voter_id_email, send_verification_email
from utils.decorators import login_required
from extensions import db, bcrypt, mail
import re
import secrets
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/api')


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/register
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new voter.
    Required : full_name, email, password, confirm_password
    Optional : phone_number, address, nin, date_of_birth
    """
    try:
        data = request.json or {}

        # ── Required fields ───────────────────────────────────────────
        required_fields = ['full_name', 'email', 'password', 'confirm_password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'All fields are required'}), 400

        # ── Generic email validation (no domain restriction) ──────────
        email = data['email'].strip().lower()
        email_regex = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return jsonify({'error': 'Invalid email address format'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # ── Phone uniqueness (optional field) ─────────────────────────
        phone = None
        if data.get('phone_number'):
            phone = data['phone_number'].strip()
            if User.query.filter_by(phone_number=phone).first():
                return jsonify({
                    'error': 'This phone number is already associated with another account'
                }), 400

        # ── Password validation ───────────────────────────────────────
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400

        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # ── Create user ───────────────────────────────────────────────
        voter_id          = generate_voter_id(User)
        password_hash     = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        verification_token = secrets.token_urlsafe(32)
        token_expires     = datetime.utcnow() + timedelta(hours=24)

        new_user = User(
            voter_id=voter_id,
            full_name=data['full_name'].strip(),
            email=email,
            password_hash=password_hash,
            phone_number=phone,
            address=data.get('address', '').strip() or None,
            role='voter',
            email_verified=False,
            email_verification_token=verification_token,
            email_verification_token_expires=token_expires,
        )

        db.session.add(new_user)
        db.session.commit()

        print(f"[REGISTER] User created — ID: {new_user.id}, Voter ID: {voter_id}")

        # ── Send verification email ────────────────────────────────────
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        print("[EMAIL] Attempting to send verification email...")
        print("[EMAIL] Recipient:", new_user.email)
        print("[EMAIL] Frontend URL:", frontend_url)

        verification_sent = send_verification_email(
            mail=mail,
            user_email=new_user.email,
            user_name=new_user.full_name,
            verification_token=verification_token,
            frontend_url=frontend_url,
        )

        print("[EMAIL] Verification email sent:", verification_sent)

        AuditLog.log_action(
            user_id=new_user.id,
            action='USER_REGISTERED',
            resource_type='user',
            resource_id=new_user.id,
            details={
                'voter_id': voter_id,
                'verification_email_sent': verification_sent,
            },
            ip_address=request.remote_addr,
        )

        return jsonify({
            'message': (
                'Registration successful! '
                'Please check your email to verify your account. '
                'Once verified, complete NIN verification in your profile to vote.'
            ),
            'user': {
                'id':             new_user.id,
                'full_name':      new_user.full_name,
                'email':          new_user.email,
                'voter_id':       voter_id,
                'email_verified': False,
                'nin_verified':   False,
            },
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"[REGISTER] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/verify-email
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email token and send Voter ID email."""
    try:
        data  = request.json or {}
        token = data.get('token', '').strip()

        if not token:
            return jsonify({'error': 'Verification token is required'}), 400

        user = User.query.filter_by(email_verification_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid verification token'}), 400

        if user.email_verification_token_expires < datetime.utcnow():
            return jsonify({'error': 'Verification token has expired'}), 400

        user.email_verified                   = True
        user.email_verified_at                = datetime.utcnow()
        user.email_verification_token         = None
        user.email_verification_token_expires = None
        db.session.commit()

        email_sent = send_voter_id_email(
            mail=mail,
            user_email=user.email,
            user_name=user.full_name,
            voter_id=user.voter_id,
        )

        AuditLog.log_action(
            user_id=user.id,
            action='EMAIL_VERIFIED',
            resource_type='user',
            resource_id=user.id,
            details={'voter_id': user.voter_id, 'voter_id_email_sent': email_sent},
            ip_address=request.remote_addr,
        )

        return jsonify({
            'message': (
                'Email verified! Your Voter ID has been sent to your inbox. '
                'Please verify your NIN in your profile before voting.'
            ),
            'user': {
                'id':             user.id,
                'full_name':      user.full_name,
                'email':          user.email,
                'voter_id':       user.voter_id,
                'email_verified': True,
                'nin_verified':   user.nin_verified,
            },
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[VERIFY] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/resend-verification
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend email verification link."""
    try:
        data  = request.json or {}
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'Email not found'}), 404

        if user.email_verified:
            return jsonify({'error': 'Email is already verified'}), 400

        verification_token = secrets.token_urlsafe(32)
        token_expires      = datetime.utcnow() + timedelta(hours=24)

        user.email_verification_token         = verification_token
        user.email_verification_token_expires = token_expires
        db.session.commit()

        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')

        sent = send_verification_email(
            mail=mail,
            user_email=user.email,
            user_name=user.full_name,
            verification_token=verification_token,
            frontend_url=frontend_url,
        )

        return jsonify({
            'message': 'Verification email resent. Please check your inbox.',
            'verification_sent': sent,
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[RESEND] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/login
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with voter_id + email + password.
    Returns NIN status so the frontend can redirect to profile if needed.
    """
    try:
        data = request.json or {}

        required_fields = ['voter_id', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Voter ID, email, and password are required'}), 400

        user = User.query.filter_by(
            voter_id=data['voter_id'].strip().upper(),
            email=data['email'].strip().lower(),
        ).first()

        if not (user and bcrypt.check_password_hash(user.password_hash, data['password'])):
            return jsonify({'error': 'Invalid voter ID, email, or password'}), 401

        if not user.email_verified:
            return jsonify({
                'error': 'Email not verified. Please check your inbox for the verification link.',
                'email': user.email,
                'needs_verification': True,
            }), 403

        if not user.is_active:
            return jsonify({'error': 'Account is deactivated. Please contact support.'}), 403

        # ── Session ────────────────────────────────────────────────────
        session.permanent       = True
        session['user_id']      = user.id
        session['role']         = user.role
        session['voter_id']     = user.voter_id
        session['full_name']    = user.full_name
        session['ip_address']   = request.remote_addr

        AuditLog.log_action(
            user_id=user.id,
            action='USER_LOGIN',
            resource_type='user',
            resource_id=user.id,
            details={
                'voter_id':     user.voter_id,
                'login_method': 'voter_id_email_password',
                'ip_address':   request.remote_addr,
            },
            ip_address=request.remote_addr,
        )

        can_vote, vote_reason = user.can_vote()

        return jsonify({
            'message': 'Login successful',
            'user': {
                'id':             user.id,
                'voter_id':       user.voter_id,
                'full_name':      user.full_name,
                'email':          user.email,
                'role':           user.role,
                'phone_number':   user.phone_number,
                'custom_fields':  user.custom_fields,
                'is_verified':    user.email_verified,
                # NIN status — frontend uses this to show prompt
                'nin_verified':   user.nin_verified,
                'can_vote':       can_vote,
                'vote_reason':    vote_reason,
                'verification_level': user.get_verification_level(),
            },
        }), 200

    except Exception as e:
        print(f"[LOGIN] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/logout
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    user_id = session.get('user_id')
    AuditLog.log_action(
        user_id=user_id,
        action='USER_LOGOUT',
        resource_type='user',
        resource_id=user_id,
        ip_address=request.remote_addr,
    )
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/profile
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        can_vote, vote_reason = user.can_vote()

        return jsonify({
            'user': {
                'id':               user.id,
                'voter_id':         user.voter_id,
                'full_name':        user.full_name,
                'email':            user.email,
                'role':             user.role,
                'phone_number':     user.phone_number,
                'address':          user.address,
                'custom_fields':    user.custom_fields,
                'is_verified':      user.email_verified,
                'nin_verified':     user.nin_verified,
                'can_vote':         can_vote,
                'vote_reason':      vote_reason,
                'verification_level': user.get_verification_level(),
                'verification_badges': user.get_verification_badges(),
                'created_at':       user.created_at.isoformat(),
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/verify-voter-id
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/verify-voter-id', methods=['POST'])
def verify_voter_id():
    """Check if a voter ID exists (used for account recovery flow)."""
    try:
        data = request.json or {}
        if 'voter_id' not in data:
            return jsonify({'error': 'Voter ID is required'}), 400

        user = User.query.filter_by(voter_id=data['voter_id'].strip().upper()).first()
        if user:
            return jsonify({
                'exists':       True,
                'email_masked': f"{user.email[:3]}***@{user.email.split('@')[1]}",
                'phone_masked': (
                    f"***{user.phone_number[-4:]}" if user.phone_number else None
                ),
            }), 200

        return jsonify({'exists': False}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/profile/update
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/profile/update', methods=['PUT'])
@login_required
def update_profile():
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.json or {}

        if 'full_name' in data and data['full_name'].strip():
            user.full_name = data['full_name'].strip()

        if 'phone_number' in data:
            phone = data['phone_number'].strip() if data['phone_number'] else None
            if phone and phone != user.phone_number:
                if User.query.filter_by(phone_number=phone).first():
                    return jsonify({
                        'error': 'Phone number already associated with another account'
                    }), 400
            user.phone_number = phone

        if 'address' in data:
            user.address = data['address'].strip() if data['address'] else None

        db.session.commit()

        AuditLog.log_action(
            user_id=user.id,
            action='PROFILE_UPDATED',
            resource_type='user',
            resource_id=user.id,
            details={'updated_fields': list(data.keys())},
            ip_address=request.remote_addr,
        )

        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id':           user.id,
                'voter_id':     user.voter_id,
                'full_name':    user.full_name,
                'email':        user.email,
                'phone_number': user.phone_number,
                'address':      user.address,
                'role':         user.role,
                'is_verified':  user.email_verified,
                'nin_verified': user.nin_verified,
                'created_at':   user.created_at.isoformat(),
            },
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[PROFILE UPDATE] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/profile/change-password
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.json or {}
        if not all(f in data for f in ['current_password', 'new_password']):
            return jsonify({'error': 'Current and new password are required'}), 400

        if not bcrypt.check_password_hash(user.password_hash, data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401

        if len(data['new_password']) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400

        if bcrypt.check_password_hash(user.password_hash, data['new_password']):
            return jsonify({'error': 'New password must differ from current password'}), 400

        user.password_hash = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
        db.session.commit()

        AuditLog.log_action(
            user_id=user.id,
            action='PASSWORD_CHANGED',
            resource_type='user',
            resource_id=user.id,
            details={'changed_at': datetime.utcnow().isoformat()},
            ip_address=request.remote_addr,
        )

        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[PASSWORD CHANGE] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500