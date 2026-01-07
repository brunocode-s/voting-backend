"""
Biometric Authentication Service using WebAuthn
Supports Face ID, Touch ID, and fingerprint across all platforms
"""

from flask import current_app
import secrets
import base64
import hashlib
import json
from datetime import datetime, timedelta
from extensions import db
from models.audit import AuditLog


class BiometricService:
    """Handle WebAuthn registration and authentication"""
    
    @staticmethod
    def _get_current_time():
        """Get current UTC time (naive datetime for database compatibility)"""
        return datetime.utcnow()
    
    @staticmethod
    def generate_challenge():
        """Generate a cryptographically secure random challenge"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    @staticmethod
    def create_registration_options(user):
        """
        Create WebAuthn registration options for biometric enrollment
        
        Args:
            user: User model instance
            
        Returns:
            dict: WebAuthn registration options
        """
        challenge = BiometricService.generate_challenge()
        
        # Store challenge in user session or temporary storage
        user.pending_webauthn_challenge = challenge
        user.pending_challenge_expires = BiometricService._get_current_time() + timedelta(minutes=2)
        db.session.commit()
        
        return {
            'challenge': challenge,
            'rp': {
                'name': current_app.config.get('APP_NAME', 'FUOYE Voting System'),
                'id': current_app.config.get('RP_ID', 'localhost')  # Your domain
            },
            'user': {
                'id': base64.urlsafe_b64encode(str(user.id).encode()).decode('utf-8').rstrip('='),
                'name': user.email,
                'displayName': user.full_name
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': -7},   # ES256
                {'type': 'public-key', 'alg': -257}  # RS256
            ],
            'authenticatorSelection': {
                'authenticatorAttachment': 'platform',  # Built-in biometrics only
                'requireResidentKey': False,
                'userVerification': 'required'  # Face ID / Touch ID required
            },
            'timeout': 60000,
            'attestation': 'none'
        }
    
    @staticmethod
    def verify_registration(user, credential_data):
        """
        Verify and store biometric credential after enrollment
        
        Args:
            user: User model instance
            credential_data: WebAuthn credential from client
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Check if challenge has expired
            if user.pending_challenge_expires:
                if BiometricService._get_current_time() > user.pending_challenge_expires:
                    return False, 'Challenge expired'
            
            # Verify challenge matches
            if user.pending_webauthn_challenge != credential_data.get('challenge'):
                return False, 'Invalid challenge'
            
            # Extract and store credential
            credential = {
                'credential_id': credential_data['id'],
                'public_key': credential_data['rawId'],
                'counter': credential_data.get('counter', 0),
                'transports': credential_data.get('transports', []),
                'created_at': BiometricService._get_current_time().isoformat()
            }
            
            # Store in user's biometric_credentials JSON field
            if not user.biometric_credentials:
                user.biometric_credentials = []
            
            user.biometric_credentials.append(credential)
            user.biometric_enabled = True
            user.pending_webauthn_challenge = None
            user.pending_challenge_expires = None
            db.session.commit()
            
            # Log enrollment
            AuditLog.log_action(
                user_id=user.id,
                action='BIOMETRIC_ENROLLED',
                resource_type='user',
                resource_id=user.id,
                details={
                    'credential_id': credential['credential_id'][:20],
                    'transports': credential['transports']
                }
            )
            
            return True, 'Biometric enrolled successfully'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Biometric enrollment error: {str(e)}")
            return False, f'Enrollment failed: {str(e)}'
    
    @staticmethod
    def create_authentication_options(user):
        """
        Create WebAuthn authentication options for login/voting
        
        Args:
            user: User model instance
            
        Returns:
            dict: WebAuthn authentication options
        """
        challenge = BiometricService.generate_challenge()
        
        # Store challenge with expiration
        user.pending_webauthn_challenge = challenge
        user.pending_challenge_expires = BiometricService._get_current_time() + timedelta(minutes=2)
        db.session.commit()
        
        # Get user's registered credentials
        allowed_credentials = []
        if user.biometric_credentials:
            for cred in user.biometric_credentials:
                allowed_credentials.append({
                    'type': 'public-key',
                    'id': cred['credential_id'],
                    'transports': cred.get('transports', ['internal'])
                })
        
        return {
            'challenge': challenge,
            'timeout': 60000,
            'rpId': current_app.config.get('RP_ID', 'localhost'),
            'allowCredentials': allowed_credentials,
            'userVerification': 'required'
        }
    
    @staticmethod
    def verify_authentication(user, assertion_data):
        """
        Verify biometric authentication
        
        Args:
            user: User model instance
            assertion_data: WebAuthn assertion from client
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Check if challenge has expired
            if user.pending_challenge_expires:
                current_time = BiometricService._get_current_time()
                
                if current_time > user.pending_challenge_expires:
                    current_app.logger.warning(f"Challenge expired for user {user.id}")
                    return False, 'Challenge expired'
            
            # Verify challenge
            stored_challenge = user.pending_webauthn_challenge
            received_challenge = assertion_data.get('challenge')

            # Debug logging
            current_app.logger.info(f"Challenge comparison for user {user.id}:")
            current_app.logger.info(f"  Stored:  '{stored_challenge}'")
            current_app.logger.info(f"  Received: '{received_challenge}'")
            current_app.logger.info(f"  Match: {stored_challenge == received_challenge}")
            
            if stored_challenge != received_challenge:
                current_app.logger.warning(
                    f"Challenge mismatch for user {user.id}: "
                    f"stored={stored_challenge[:20] if stored_challenge else 'None'}... "
                    f"received={received_challenge[:20] if received_challenge else 'None'}..."
                )
                return False, 'Invalid challenge'
            
            # Get assertion details
            assertion = assertion_data.get('assertion', {})
            credential_id = assertion.get('id') or assertion.get('rawId')
            
            if not credential_id:
                current_app.logger.warning(f"Missing credential ID for user {user.id}")
                return False, 'Missing credential ID'
            
            # Find matching credential
            matching_cred = None
            if user.biometric_credentials:
                for cred in user.biometric_credentials:
                    if cred['credential_id'] == credential_id:
                        matching_cred = cred
                        break
            
            if not matching_cred:
                current_app.logger.warning(
                    f"Credential not found for user {user.id}, credential_id: {credential_id[:20]}..."
                )
                return False, 'Credential not found'
            
            # Update counter (prevents replay attacks)
            new_counter = assertion.get('counter', 0)
            old_counter = matching_cred.get('counter', 0)
            
            # Only check counter if it's being used (some authenticators don't increment it)
            if new_counter > 0 and old_counter > 0 and new_counter <= old_counter:
                current_app.logger.warning(
                    f"Counter mismatch for user {user.id}: {new_counter} <= {old_counter}"
                )
                return False, 'Counter mismatch - possible replay attack'
            
            # Update credential usage
            matching_cred['counter'] = new_counter
            matching_cred['last_used'] = BiometricService._get_current_time().isoformat()
            
            # Clear the challenge
            user.pending_webauthn_challenge = None
            user.pending_challenge_expires = None
            
            # Mark as modified for JSON field
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(user, 'biometric_credentials')
            
            db.session.commit()
            
            # Log successful authentication
            AuditLog.log_action(
                user_id=user.id,
                action='BIOMETRIC_AUTH_SUCCESS',
                resource_type='user',
                resource_id=user.id,
                details={
                    'credential_id': credential_id[:20],
                    'auth_type': 'webauthn'
                }
            )
            
            return True, 'Authentication successful'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Biometric auth error for user {user.id}: {str(e)}", exc_info=True)
            
            # Log failed attempt
            try:
                AuditLog.log_action(
                    user_id=user.id,
                    action='BIOMETRIC_AUTH_FAILED',
                    resource_type='user',
                    resource_id=user.id,
                    details={'error': str(e)}
                )
            except Exception:
                pass  # Don't fail on audit log error
            
            return False, f'Authentication failed: {str(e)}'
    
    @staticmethod
    def remove_credential(user, credential_id):
        """Remove a biometric credential"""
        try:
            if user.biometric_credentials:
                original_count = len(user.biometric_credentials)
                user.biometric_credentials = [
                    cred for cred in user.biometric_credentials 
                    if cred['credential_id'] != credential_id
                ]
                
                if len(user.biometric_credentials) == original_count:
                    return False, 'Credential not found'
                
                if not user.biometric_credentials:
                    user.biometric_enabled = False
                
                # Mark as modified for JSON field
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user, 'biometric_credentials')
                
                db.session.commit()
                
                # Log removal
                AuditLog.log_action(
                    user_id=user.id,
                    action='BIOMETRIC_CREDENTIAL_REMOVED',
                    resource_type='user',
                    resource_id=user.id,
                    details={'credential_id': credential_id[:20]}
                )
                
                return True, 'Credential removed'
            
            return False, 'No credentials found'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Remove credential error: {str(e)}")
            return False, str(e)


# Singleton instance
biometric_service = BiometricService()