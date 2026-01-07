"""
Biometric Authentication Routes
Endpoints for WebAuthn registration and authentication
"""

from flask import Blueprint, request, jsonify, session
from models.user import User
from models.audit import AuditLog
from services.biometric_service import biometric_service
from utils.decorators import login_required
from extensions import db

biometric_bp = Blueprint('biometric', __name__, url_prefix='/api/biometric')


@biometric_bp.route('/enrollment/start', methods=['POST'])
@login_required
def start_enrollment():
    """
    Start biometric enrollment process
    Returns WebAuthn registration options
    """
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate WebAuthn registration options
        options = biometric_service.create_registration_options(user)
        
        return jsonify({
            'success': True,
            'options': options,
            'message': 'Use Face ID or Touch ID to enroll'
        }), 200
        
    except Exception as e:
        print(f"[BIOMETRIC] Enrollment start error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/enrollment/complete', methods=['POST'])
@login_required
def complete_enrollment():
    """
    Complete biometric enrollment
    Verifies and stores the credential
    """
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        credential_data = request.json
        
        # Verify and store credential
        success, message = biometric_service.verify_registration(user, credential_data)
        
        if success:
            user.biometric_enrolled_at = db.func.now()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': message,
                'biometric_enabled': True
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        print(f"[BIOMETRIC] Enrollment complete error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/auth/start', methods=['POST'])
def start_authentication():
    """
    Start biometric authentication for login
    Can be called before full login to prepare authentication
    """
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # User can provide voter_id or email to identify themselves
        identifier = data.get('voter_id') or data.get('email')
        
        if not identifier:
            return jsonify({'error': 'Voter ID or email required'}), 400
        
        # Find user
        user = User.query.filter(
            (User.voter_id == identifier.upper()) | 
            (User.email == identifier.lower())
        ).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.biometric_enabled:
            return jsonify({'error': 'Biometric not enabled for this account'}), 400
        
        # Generate authentication options
        options = biometric_service.create_authentication_options(user)
        
        return jsonify({
            'success': True,
            'options': options,
            'user_id': user.id,  # Needed for next step
            'message': 'Use Face ID or Touch ID to authenticate'
        }), 200
        
    except Exception as e:
        print(f"[BIOMETRIC] Auth start error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/auth/verify', methods=['POST'])
def verify_authentication():
    """
    Verify biometric authentication
    This can replace password login if successful
    """
    try:
        data = request.json

        # Debug logging
        print(f"[BIOMETRIC] Received verify request: {data}")

        user_id = data.get('user_id')
        assertion = data.get('assertion')
        challenge = data.get('challenge')
        
        if not user_id or not assertion:
            return jsonify({'error': 'User ID and assertion required'}), 400
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create a properly structured object for the service
        verification_data = {
            'challenge': challenge,
            'assertion': assertion,
            'user_id': user_id
        }

        print(f"[BIOMETRIC VERIFY] Passing to service: challenge={challenge}")
        
        # Verify biometric authentication
        success, message = biometric_service.verify_authentication(user, verification_data)
        
        if success:
            # Create session (same as password login)
            session.permanent = True
            session['user_id'] = user.id
            session['role'] = user.role
            session['voter_id'] = user.voter_id
            session['full_name'] = user.full_name
            session['ip_address'] = request.remote_addr
            session['auth_method'] = 'biometric'
            
            # Log successful biometric login
            AuditLog.log_action(
                user_id=user.id,
                action='BIOMETRIC_LOGIN',
                resource_type='user',
                resource_id=user.id,
                details={
                    'voter_id': user.voter_id,
                    'login_method': 'webauthn_biometric',
                    'ip_address': request.remote_addr
                },
                ip_address=request.remote_addr
            )
            
            return jsonify({
                'success': True,
                'message': 'Biometric authentication successful',
                'user': user.to_dict(include_biometric=True)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 401
            
    except Exception as e:
        print(f"[BIOMETRIC] Auth verify error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/status', methods=['GET'])
@login_required
def get_biometric_status():
    """Get user's biometric enrollment status"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        credentials_info = []
        if user.biometric_credentials:
            for cred in user.biometric_credentials:
                credentials_info.append({
                    'id': cred['credential_id'][:20] + '...',
                    'created_at': cred.get('created_at'),
                    'last_used': cred.get('last_used'),
                    'transports': cred.get('transports', [])
                })
        
        return jsonify({
            'biometric_enabled': user.biometric_enabled,
            'require_biometric_for_voting': user.require_biometric_for_voting,
            'enrolled_at': user.biometric_enrolled_at.isoformat() if user.biometric_enrolled_at else None,
            'credentials_count': len(user.biometric_credentials) if user.biometric_credentials else 0,
            'credentials': credentials_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/credentials/<credential_id>', methods=['DELETE'])
@login_required
def remove_credential(credential_id):
    """Remove a specific biometric credential"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        success, message = biometric_service.remove_credential(user, credential_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@biometric_bp.route('/settings/require-for-voting', methods=['POST'])
@login_required
def toggle_require_for_voting():
    """Toggle whether biometric is required for voting"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.biometric_enabled:
            return jsonify({'error': 'Biometric must be enabled first'}), 400
        
        data = request.json
        require = data.get('require', False)
        
        user.require_biometric_for_voting = require
        db.session.commit()
        
        return jsonify({
            'success': True,
            'require_biometric_for_voting': user.require_biometric_for_voting
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500