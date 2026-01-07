from app import app
from extensions import mail
from services.email_service import send_verification_email, send_voter_id_email

# Test in application context
with app.app_context():
    # Test 1: Send verification email
    result = send_verification_email(
        mail=mail,
        user_email='test@fuoye.edu.ng',
        user_name='Test User',
        verification_token='test-token-12345',
        frontend_url='http://localhost:5173'
    )
    print(f"Verification email sent: {result}")
    
    # Test 2: Send voter ID email
    result = send_voter_id_email(
        mail=mail,
        user_email='test@fuoye.edu.ng',
        user_name='Test User',
        voter_id='ABC123DEF4'
    )
    print(f"Voter ID email sent: {result}")