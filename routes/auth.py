from flask import Blueprint, request, jsonify, session, current_app
from models.user import User
from models.audit import AuditLog
from services.voter_id_generator import generate_voter_id
from services.email_service import send_voter_id_email, send_verification_email
from utils.decorators import login_required
from utils.config_helper import is_valid_fuoye_email, get_email_domain_error
from extensions import db, bcrypt, mail
import re
import secrets
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Enhanced registration with domain enforcement and email verification"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'password', 'confirm_password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'All fields are required'}), 400
        
        # ✅ RULE 1: Enforce @fuoye.edu.ng domain
        if not is_valid_fuoye_email(data['email']):
            return jsonify({'error': get_email_domain_error()}), 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@fuoye\.edu\.ng$'
        if not re.match(email_regex, data['email']):
            return jsonify({'error': 'Invalid FUOYE email format'}), 400
        
        # Normalize email to lowercase for consistency
        email = data['email'].strip().lower()
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # ✅ RULE 3: Enforce one phone per account
        if data.get('phone_number'):
            phone = data['phone_number'].strip()
            existing_phone = User.query.filter_by(phone_number=phone).first()
            if existing_phone:
                return jsonify({
                    'error': 'This phone number is already associated with another account'
                }), 400
        
        # Validate password match
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Validate password strength
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Generate unique Voter ID
        voter_id = generate_voter_id(User)
        
        # Hash password
        password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.utcnow() + timedelta(hours=24)
        
        # Create new user
        new_user = User(
            voter_id=voter_id,
            full_name=data['full_name'],
            email=email,
            password_hash=password_hash,
            phone_number=data.get('phone_number'),
            address=data.get('address'),
            role='voter',
            email_verified=False,  # ✅ RULE 2: Email must be verified
            email_verification_token=verification_token,
            email_verification_token_expires=token_expires
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"[REGISTER] User created with ID: {new_user.id}, Voter ID: {voter_id}")
        
        # Send verification email
        # Get frontend URL from config first, fallback to request
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        
        print(f"[REGISTER] Frontend URL: {frontend_url}")
        print(f"[REGISTER] Sending verification email to: {new_user.email}")
        
        verification_sent = send_verification_email(
            mail=mail,
            user_email=new_user.email,
            user_name=new_user.full_name,
            verification_token=verification_token,
            frontend_url=frontend_url
        )
        
        print(f"[REGISTER] Verification email sent: {verification_sent}")
        
        # Log registration
        AuditLog.log_action(
            user_id=new_user.id,
            action='USER_REGISTERED',
            resource_type='user',
            resource_id=new_user.id,
            details={
                'voter_id': voter_id,
                'email_domain': 'fuoye.edu.ng',
                'verification_email_sent': verification_sent
            },
            ip_address=request.remote_addr
        )
        
        # ✅ FIX: Return voter_id in the response!
        return jsonify({
            'message': 'Registration successful! Check your email to verify your account.',
            'user': {
                'id': new_user.id,
                'full_name': new_user.full_name,
                'email': new_user.email,
                'voter_id': voter_id,  # ← THIS WAS MISSING!
                'email_verified': new_user.email_verified
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[REGISTER] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email and send Voter ID"""
    try:
        data = request.json
        
        if 'token' not in data:
            return jsonify({'error': 'Verification token is required'}), 400
        
        token = data['token'].strip()
        
        print(f"[VERIFY] Attempting to verify token: {token[:20]}...")
        
        # Find user by verification token
        user = User.query.filter_by(
            email_verification_token=token
        ).first()
        
        if not user:
            print(f"[VERIFY] Invalid token - user not found")
            return jsonify({'error': 'Invalid verification token'}), 400
        
        # Check if token is expired
        if user.email_verification_token_expires < datetime.utcnow():
            print(f"[VERIFY] Token expired for user: {user.email}")
            return jsonify({'error': 'Verification token has expired'}), 400
        
        # Mark email as verified
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_token_expires = None
        
        db.session.commit()
        
        print(f"[VERIFY] Email verified for user: {user.email}")
        
        # Now send the Voter ID email
        print(f"[VERIFY] Sending Voter ID email to: {user.email}")
        
        email_sent = send_voter_id_email(
            mail=mail,
            user_email=user.email,
            user_name=user.full_name,
            voter_id=user.voter_id
        )
        
        print(f"[VERIFY] Voter ID email sent: {email_sent}")
        
        # Log email verification
        AuditLog.log_action(
            user_id=user.id,
            action='EMAIL_VERIFIED',
            resource_type='user',
            resource_id=user.id,
            details={'voter_id': user.voter_id, 'voter_id_email_sent': email_sent},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Email verified! Your Voter ID has been sent to your inbox.',
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'voter_id': user.voter_id,
                'email_verified': True
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[VERIFY] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    try:
        data = request.json
        
        if 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
        
        email = data['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'error': 'Email not found'}), 404
        
        if user.email_verified:
            return jsonify({'error': 'Email is already verified'}), 400
        
        # Generate new token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.utcnow() + timedelta(hours=24)
        
        user.email_verification_token = verification_token
        user.email_verification_token_expires = token_expires
        
        db.session.commit()
        
        # Send verification email
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
        
        verification_sent = send_verification_email(
            mail=mail,
            user_email=user.email,
            user_name=user.full_name,
            verification_token=verification_token,
            frontend_url=frontend_url
        )
        
        return jsonify({
            'message': 'Verification email resent. Please check your inbox.',
            'verification_sent': verification_sent
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[RESEND] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login - requires email verification"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['voter_id', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Voter ID, email, and password are required'}), 400
        
        # Find user by BOTH voter_id AND email
        user = User.query.filter_by(
            voter_id=data['voter_id'].strip().upper(),
            email=data['email'].strip().lower()
        ).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, data['password']):
            
            # ✅ RULE 2: Check if email is verified
            if not user.email_verified:
                return jsonify({
                    'error': 'Email not verified. Please check your email for verification link.',
                    'email': user.email,
                    'needs_verification': True
                }), 403
            
            # Check if account is active
            if not user.is_active:
                return jsonify({'error': 'Account is deactivated. Please contact support.'}), 403
            
            # Create session
            session.permanent = True
            session['user_id'] = user.id
            session['role'] = user.role
            session['voter_id'] = user.voter_id
            session['full_name'] = user.full_name
            session['ip_address'] = request.remote_addr
            
            # Log successful login
            AuditLog.log_action(
                user_id=user.id,
                action='USER_LOGIN',
                resource_type='user',
                resource_id=user.id,
                details={
                    'voter_id': user.voter_id,
                    'login_method': 'voter_id_email_password',
                    'ip_address': request.remote_addr
                },
                ip_address=request.remote_addr
            )
            
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'voter_id': user.voter_id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'role': user.role,
                    'phone_number': user.phone_number,
                    'custom_fields': user.custom_fields,
                    'is_verified': user.email_verified
                }
            }), 200
        
        # Generic error to prevent enumeration attacks
        return jsonify({'error': 'Invalid voter ID, email, or password'}), 401
        
    except Exception as e:
        print(f"[LOGIN] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout endpoint"""
    user_id = session.get('user_id')
    
    # Log logout before clearing session
    AuditLog.log_action(
        user_id=user_id,
        action='USER_LOGOUT',
        resource_type='user',
        resource_id=user_id,
        ip_address=request.remote_addr
    )
    
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': user.id,
                'voter_id': user.voter_id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'phone_number': user.phone_number,
                'address': user.address,
                'custom_fields': user.custom_fields,
                'is_verified': user.email_verified,
                'created_at': user.created_at.isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify-voter-id', methods=['POST'])
def verify_voter_id():
    """Verify if a voter ID exists (for password reset, etc.)"""
    try:
        data = request.json
        
        if 'voter_id' not in data:
            return jsonify({'error': 'Voter ID is required'}), 400
        
        user = User.query.filter_by(voter_id=data['voter_id'].strip().upper()).first()
        
        if user:
            return jsonify({
                'exists': True,
                'email_masked': f"{user.email[:3]}***@{user.email.split('@')[1]}"
            }), 200
        
        return jsonify({'exists': False}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@auth_bp.route('/profile/update', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        
        # Update allowed fields
        if 'full_name' in data and data['full_name'].strip():
            user.full_name = data['full_name'].strip()
        
        if 'phone_number' in data:
            phone = data['phone_number'].strip() if data['phone_number'] else None
            
            # Check if phone is being changed and if new phone already exists
            if phone and phone != user.phone_number:
                existing_phone = User.query.filter_by(phone_number=phone).first()
                if existing_phone and existing_phone.id != user.id:
                    return jsonify({
                        'error': 'This phone number is already associated with another account'
                    }), 400
            
            user.phone_number = phone
        
        if 'address' in data:
            user.address = data['address'].strip() if data['address'] else None
        
        db.session.commit()
        
        # Log profile update
        AuditLog.log_action(
            user_id=user.id,
            action='PROFILE_UPDATED',
            resource_type='user',
            resource_id=user.id,
            details={
                'updated_fields': list(data.keys())
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'voter_id': user.voter_id,
                'full_name': user.full_name,
                'email': user.email,
                'phone_number': user.phone_number,
                'address': user.address,
                'role': user.role,
                'is_verified': user.email_verified,
                'created_at': user.created_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[PROFILE UPDATE] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        
        # Validate required fields
        required_fields = ['current_password', 'new_password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Current and new password are required'}), 400
        
        # Verify current password
        if not bcrypt.check_password_hash(user.password_hash, data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        if len(data['new_password']) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        # Check if new password is same as current
        if bcrypt.check_password_hash(user.password_hash, data['new_password']):
            return jsonify({'error': 'New password must be different from current password'}), 400
        
        # Update password
        user.password_hash = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
        db.session.commit()
        
        # Log password change
        AuditLog.log_action(
            user_id=user.id,
            action='PASSWORD_CHANGED',
            resource_type='user',
            resource_id=user.id,
            details={'changed_at': datetime.utcnow().isoformat()},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[PASSWORD CHANGE] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500