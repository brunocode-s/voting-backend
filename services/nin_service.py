"""
NIN (National ID) Verification Service
Integrates with Korapay API for Nigerian National Identity verification
"""

import requests
import hashlib
from datetime import datetime
from flask import current_app


class NINVerificationService:
    """
    Handle NIN verification with Korapay API
    
    Features:
    - Basic NIN lookup
    - Name and DOB validation
    - Photo matching (selfie vs NIN photo)
    """
    
    def __init__(self):
        self.base_url = "https://api.korapay.com/merchant/api/v1"
        self.api_key = None
        self._initialized = False
    
    def initialize(self):
        """Initialize NIN verification service"""
        try:
            # Get API key from config
            self.api_key = current_app.config.get('KORAPAY_API_KEY')
            
            if not self.api_key:
                print("[NIN] Korapay API key not configured")
                return False
            
            self._initialized = True
            print("[NIN] NIN verification service initialized")
            return True
            
        except Exception as e:
            print(f"[NIN] Initialization error: {str(e)}")
            return False
    
    def is_enabled(self):
        """Check if NIN verification is enabled"""
        return self._initialized and current_app.config.get('NIN_VERIFICATION_ENABLED', False)
    
    def hash_nin(self, nin):
        """
        Hash NIN for storage (privacy protection)
        Never store actual NIN in database!
        """
        salt = current_app.config.get('NIN_HASH_SALT', 'default_salt')
        nin_string = f"{nin}{salt}"
        return hashlib.sha256(nin_string.encode()).hexdigest()
    
    def verify_nin_basic(self, nin):
        """
        Basic NIN lookup - just verify it exists
        
        Args:
            nin: National Identification Number (11 digits)
            
        Returns:
            dict: Verification result with user data
        """
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'NIN verification not enabled'
            }
        
        try:
            # Prepare request
            url = f"{self.base_url}/identities/ng/nin"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'id': nin,
                'verification_consent': True
            }
            
            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status'):
                    return {
                        'success': True,
                        'data': data.get('data', {}),
                        'message': 'NIN verified successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('message', 'Verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Verification timeout - please try again'
            }
        except Exception as e:
            print(f"[NIN] Verification error: {str(e)}")
            return {
                'success': False,
                'error': 'Verification failed - please try again'
            }
    
    def verify_nin_with_data(self, nin, first_name, last_name, date_of_birth):
        """
        Verify NIN and validate name and DOB
        
        Args:
            nin: National Identification Number
            first_name: First name to validate
            last_name: Last name to validate
            date_of_birth: DOB in format YYYY-MM-DD
            
        Returns:
            dict: Verification result with match status
        """
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'NIN verification not enabled'
            }
        
        try:
            url = f"{self.base_url}/identities/ng/nin"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'id': nin,
                'verification_consent': True,
                'validation': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': date_of_birth
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status'):
                    result_data = data.get('data', {})
                    validation = result_data.get('validation', {})
                    
                    # Check if all fields match
                    first_name_match = validation.get('first_name', {}).get('match', False)
                    last_name_match = validation.get('last_name', {}).get('match', False)
                    dob_match = validation.get('date_of_birth', {}).get('match', False)
                    
                    all_match = first_name_match and last_name_match and dob_match
                    
                    return {
                        'success': True,
                        'data': result_data,
                        'validation': {
                            'first_name_match': first_name_match,
                            'last_name_match': last_name_match,
                            'dob_match': dob_match,
                            'all_match': all_match
                        },
                        'message': 'Verification complete'
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('message', 'Verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }
                
        except Exception as e:
            print(f"[NIN] Data verification error: {str(e)}")
            return {
                'success': False,
                'error': 'Verification failed - please try again'
            }
    
    def verify_nin_with_photo(self, nin, first_name, last_name, date_of_birth, selfie_base64):
        """
        Verify NIN and match photo
        
        Args:
            nin: National Identification Number
            first_name: First name to validate
            last_name: Last name to validate
            date_of_birth: DOB in format YYYY-MM-DD
            selfie_base64: Base64 encoded selfie image
            
        Returns:
            dict: Verification result with photo match score
        """
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'NIN verification not enabled'
            }
        
        try:
            url = f"{self.base_url}/identities/ng/nin"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'id': nin,
                'verification_consent': True,
                'validation': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': date_of_birth,
                    'selfie': selfie_base64
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status'):
                    result_data = data.get('data', {})
                    validation = result_data.get('validation', {})
                    
                    # Check data matches
                    first_name_match = validation.get('first_name', {}).get('match', False)
                    last_name_match = validation.get('last_name', {}).get('match', False)
                    dob_match = validation.get('date_of_birth', {}).get('match', False)
                    
                    # Check photo match
                    selfie_data = validation.get('selfie', {})
                    photo_match = selfie_data.get('match', False)
                    confidence = selfie_data.get('confidence_rating', 0)
                    
                    # Determine overall success
                    # Require: all data match + photo confidence > 70%
                    all_data_match = first_name_match and last_name_match and dob_match
                    photo_acceptable = confidence >= 70
                    
                    overall_success = all_data_match and photo_acceptable
                    
                    return {
                        'success': True,
                        'data': result_data,
                        'validation': {
                            'first_name_match': first_name_match,
                            'last_name_match': last_name_match,
                            'dob_match': dob_match,
                            'photo_match': photo_match,
                            'photo_confidence': confidence,
                            'all_data_match': all_data_match,
                            'photo_acceptable': photo_acceptable,
                            'overall_verified': overall_success
                        },
                        'message': 'Verification complete'
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('message', 'Verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }
                
        except Exception as e:
            print(f"[NIN] Photo verification error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': 'Verification failed - please try again'
            }
    
    def extract_nin_photo(self, verification_data):
        """
        Extract NIN photo from verification response
        For use in biometric enrollment comparison
        
        Args:
            verification_data: Data from successful verification
            
        Returns:
            str: Base64 encoded photo or None
        """
        try:
            return verification_data.get('image')
        except Exception as e:
            print(f"[NIN] Photo extraction error: {str(e)}")
            return None


# Singleton instance
nin_service = NINVerificationService()