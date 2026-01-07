"""
Updated Voting Route with Biometric Verification
Add this to your existing routes/voting.py file
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


@voting_bp.route('/verify-biometric', methods=['POST'])
@login_required
def verify_biometric_for_vote():
    """
    Verify biometric before allowing vote
    This endpoint should be called before submitting the actual vote
    """
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user requires biometric
        if user.require_biometric_for_voting and not user.biometric_enabled:
            return jsonify({
                'error': 'Biometric authentication required but not enabled'
            }), 403
        
        assertion_data = request.json
        
        # Verify biometric
        success, message = biometric_service.verify_authentication(user, assertion_data)
        
        if success:
            # Store verification in session (temporary)
            session['biometric_verified'] = True
            session['biometric_verified_at'] = datetime.utcnow().isoformat()
            session['biometric_credential_id'] = assertion_data.get('id')
            
            return jsonify({
                'success': True,
                'message': 'Biometric verified. You may now vote.',
                'verified': True
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message,
                'verified': False
            }), 401
            
    except Exception as e:
        print(f"[VOTING] Biometric verify error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@voting_bp.route('/submit', methods=['POST'])
@login_required
def submit_vote():
    """
    Submit vote with optional biometric verification
    Enhanced version of your existing vote submission
    """
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        election_id = data.get('election_id')
        candidate_id = data.get('candidate_id')
        position_id = data.get('position_id')
        
        # Validate inputs
        if not all([election_id, candidate_id, position_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # ✅ GET ELECTION AND CHECK ITS BIOMETRIC REQUIREMENT
        election = Election.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        # Check if biometric verification is required
        biometric_verified = False
        credential_id = None
        verification_method = 'password'
        
        # ✅ CHECK BOTH USER AND ELECTION REQUIREMENTS
        requires_biometric = user.require_biometric_for_voting or election.require_biometric
        
        if requires_biometric:
            # Check if user has biometric enabled
            if not user.biometric_enabled:
                return jsonify({
                    'error': 'Biometric authentication is required but not enabled. Please set it up in your profile.',
                    'requires_biometric': True,
                    'needs_setup': True
                }), 403
            
            # Check if biometric was verified in this session
            if not session.get('biometric_verified'):
                return jsonify({
                    'error': 'Biometric verification required before voting',
                    'requires_biometric': True
                }), 403
            
            # Check verification is recent (within 5 minutes)
            verified_at = datetime.fromisoformat(session.get('biometric_verified_at'))
            time_diff = (datetime.utcnow() - verified_at).total_seconds()
            
            if time_diff > 300:  # 5 minutes
                session.pop('biometric_verified', None)
                return jsonify({
                    'error': 'Biometric verification expired. Please verify again.',
                    'requires_biometric': True
                }), 403
            
            biometric_verified = True
            credential_id = session.get('biometric_credential_id')
            verification_method = 'biometric'
        
        # Check if user already voted for this position
        existing_vote = Vote.query.filter_by(
            user_id=user.id,
            election_id=election_id,
            position_id=position_id
        ).first()
        
        if existing_vote:
            return jsonify({'error': 'You have already voted for this position'}), 400
        
        # Create vote record
        new_vote = Vote(
            election_id=election_id,
            user_id=user.id,
            candidate_id=candidate_id,
            position_id=position_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            biometric_verified=biometric_verified,
            biometric_credential_id=credential_id,
            biometric_verified_at=datetime.utcnow() if biometric_verified else None,
            verification_method=verification_method,
            # Add fraud detection metadata
            device_fingerprint=data.get('device_fingerprint'),
            session_duration=data.get('session_duration'),
            mouse_movements=data.get('mouse_movements'),
            keystroke_patterns=data.get('keystroke_patterns')
        )
        
        db.session.add(new_vote)
        db.session.commit()
        
        # Clear biometric verification from session
        session.pop('biometric_verified', None)
        session.pop('biometric_verified_at', None)
        session.pop('biometric_credential_id', None)
        
        # Log vote submission
        AuditLog.log_action(
            user_id=user.id,
            action='VOTE_SUBMITTED',
            resource_type='vote',
            resource_id=new_vote.id,
            details={
                'election_id': election_id,
                'position_id': position_id,
                'biometric_verified': biometric_verified,
                'verification_method': verification_method
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'Vote submitted successfully',
            'vote_id': new_vote.id,
            'biometric_verified': biometric_verified
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[VOTING] Submit error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@voting_bp.route('/check-requirements/<int:election_id>', methods=['GET'])
@login_required
def check_voting_requirements(election_id):
    """
    Check what's required before user can vote
    Returns whether biometric is needed
    """
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        election = Election.query.get(election_id)
        
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        # ✅ CHECK BOTH USER AND ELECTION REQUIREMENTS
        requires_biometric = user.require_biometric_for_voting or election.require_biometric
        
        return jsonify({
            'can_vote': True,
            'requires_biometric': requires_biometric,
            'election_requires_biometric': election.require_biometric,  # Add this
            'user_requires_biometric': user.require_biometric_for_voting,  # Add this
            'biometric_enabled': user.biometric_enabled,
            'biometric_verified_in_session': session.get('biometric_verified', False),
            'needs_biometric_setup': requires_biometric and not user.biometric_enabled,
            'election': {
                'id': election.id,
                'title': election.title,
                'is_active': election.is_active
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500