"""
routes/password_reset.py
Forgot-password and reset-password endpoints.
Wire into app.py: from routes.password_reset import password_reset_bp
                  app.register_blueprint(password_reset_bp)
"""

from flask import Blueprint, request, jsonify, current_app
from models.user import User
from models.audit import AuditLog
from services.email_service import send_password_reset_email
from extensions import db, bcrypt, mail
import secrets
from datetime import datetime, timedelta

password_reset_bp = Blueprint('password_reset', __name__, url_prefix='/api')


@password_reset_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request a password reset link.
    Accepts: email OR voter_id (at least one required).
    Always returns 200 to prevent user enumeration.
    """
    try:
        data  = request.json or {}
        email    = data.get('email', '').strip().lower()
        voter_id = data.get('voter_id', '').strip().upper()

        if not email and not voter_id:
            return jsonify({'error': 'Email or Voter ID is required'}), 400

        # Find user — try email first, fall back to voter_id
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        if not user and voter_id:
            user = User.query.filter_by(voter_id=voter_id).first()

        # Always return success (don't leak whether account exists)
        generic_ok = jsonify({
            'message': 'If an account with those details exists, a reset link has been sent.'
        }), 200

        if not user or not user.is_active:
            return generic_ok

        # Generate reset token (reuse the email verification token columns
        # — they're already on the User model and indexed)
        reset_token   = secrets.token_urlsafe(32)
        token_expires = datetime.utcnow() + timedelta(hours=1)

        user.email_verification_token         = reset_token
        user.email_verification_token_expires = token_expires
        db.session.commit()

        send_password_reset_email(
            mail=mail,
            user_email=user.email,
            user_name=user.full_name,
            reset_token=reset_token,
        )

        AuditLog.log_action(
            user_id=user.id,
            action='PASSWORD_RESET_REQUESTED',
            resource_type='user',
            resource_id=user.id,
            details={'email': user.email},
            ip_address=request.remote_addr,
        )

        return generic_ok

    except Exception as e:
        db.session.rollback()
        print(f"[FORGOT PASSWORD] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@password_reset_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Complete a password reset using the token from the email link.
    Accepts: token, new_password, confirm_password
    """
    try:
        data = request.json or {}
        token            = data.get('token', '').strip()
        new_password     = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        if not token:
            return jsonify({'error': 'Reset token is required'}), 400

        if not new_password:
            return jsonify({'error': 'New password is required'}), 400

        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400

        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Find user by token
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            return jsonify({'error': 'Invalid or expired reset token'}), 400

        if user.email_verification_token_expires < datetime.utcnow():
            return jsonify({'error': 'Reset token has expired. Please request a new one.'}), 400

        # Check new password is different from current
        if bcrypt.check_password_hash(user.password_hash, new_password):
            return jsonify({'error': 'New password must differ from your current password'}), 400

        # Apply new password and clear token
        user.password_hash                    = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.email_verification_token         = None
        user.email_verification_token_expires = None
        db.session.commit()

        AuditLog.log_action(
            user_id=user.id,
            action='PASSWORD_RESET_COMPLETED',
            resource_type='user',
            resource_id=user.id,
            details={'reset_at': datetime.utcnow().isoformat()},
            ip_address=request.remote_addr,
        )

        return jsonify({'message': 'Password reset successfully. You can now log in.'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[RESET PASSWORD] ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500