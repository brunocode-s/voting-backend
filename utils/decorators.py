"""
utils/decorators.py  (updated)
Adds @nin_required on top of the existing decorators.
"""

from functools import wraps
from flask import session, jsonify


def login_required(f):
    """Require an active session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def nin_required(f):
    """
    Require that the logged-in user has a verified NIN.
    Use on any endpoint that should only be reachable after NIN verification
    (e.g. viewing ballot, submitting vote).

    Returns a structured 403 that the frontend can act on:
      { error, nin_required: true, redirect: '/profile' }
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from models.user import User

        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.nin_verified:
            return jsonify({
                'error': (
                    'NIN verification required. '
                    'Please verify your National Identification Number in your profile.'
                ),
                'nin_required': True,
                'redirect': '/profile',
            }), 403

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from models.user import User

        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Require one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from models.user import User

            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401

            user = User.query.get(session['user_id'])
            if not user or user.role not in roles:
                return jsonify({
                    'error': f'Required role: {", ".join(roles)}'
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator