from flask_mail import Message
from flask import render_template_string, current_app

def send_voter_id_email(mail, user_email, user_name, voter_id):
    """
    Send Voter ID to user's email
    
    Args:
        mail: Flask-Mail instance
        user_email: User's email address
        user_name: User's full name
        voter_id: Generated voter ID
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    frontend_url = current_app.config.get('FRONTEND_URL')
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
            .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
            .voter-id-box { background: white; border: 2px solid #4F46E5; padding: 20px; margin: 20px 0; text-align: center; border-radius: 8px; }
            .voter-id { font-size: 28px; font-weight: bold; color: #4F46E5; letter-spacing: 2px; }
            .info-box { background: #EEF2FF; padding: 15px; border-left: 4px solid #4F46E5; margin: 15px 0; }
            .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            .button { display: inline-block; background: #4F46E5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1> Welcome to  the Voting System!</h1>
            </div>
            
            <div class="content">
                <h2>Hello {{ user_name }},</h2>
                
                <p>Your registration was successful! You are now eligible to participate in upcoming elections.</p>
                
                <div class="voter-id-box">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Your Unique Voter ID</p>
                    <p class="voter-id">{{ voter_id }}</p>
                </div>
                
                <div class="info-box">
                    <p><strong>⚠️ IMPORTANT: Please save this Voter ID</strong></p>
                    <ul>
                        <li>This is your unique identifier in the system</li>
                        <li>You'll need your email and password to login</li>
                        <li>Keep this ID confidential</li>
                        <li>You can find it in your profile after logging in</li>
                    </ul>
                </div>
                
                <h3>How to Vote:</h3>
                <ol>
                    <li>Go to the voting portal</li>
                    <li>Login with your email: <strong>{{ user_email }}</strong></li>
                    <li>Select your preferred candidates</li>
                    <li>Submit your vote</li>
                </ol>
                
                <div style="text-align: center;">
                    <a href="{{ frontend_url }}" class="button">Go to Voting Portal</a>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    If you didn't register for this account, please contact the system administrator immediately.
                </p>
            </div>
            
            <div class="footer">
                <p>© 2026 Intelligent Voting System</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = Message(
            subject='Your Voter ID - Registration Successful',
            recipients=[user_email]
        )
        
        msg.html = render_template_string(
            email_template,
            user_name=user_name,
            voter_id=voter_id,
            user_email=user_email,
            frontend_url=frontend_url
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    
def send_verification_email(mail, user_email, user_name, verification_token, frontend_url):
    """
    Send email verification link to user
    
    Args:
        mail: Flask-Mail instance
        user_email: User's email address
        user_name: User's full name
        verification_token: Token for verification link
        frontend_url: Frontend URL for verification link
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    verification_link = f"{frontend_url}/verify-email?token={verification_token}"
    
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
            .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
            .info-box { background: #EEF2FF; padding: 15px; border-left: 4px solid #4F46E5; margin: 15px 0; }
            .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            .button { display: inline-block; background: #4F46E5; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-top: 15px; }
            .token-box { background: white; border: 1px solid #d1d5db; padding: 15px; margin: 15px 0; border-radius: 6px; font-family: monospace; word-break: break-all; }
            .warning { background: #FEF3C7; border: 1px solid #FCD34D; padding: 15px; border-radius: 6px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Verify Your FUOYE Email</h1>
            </div>
            
            <div class="content">
                <h2>Hello {{ user_name }},</h2>
                
                <p>Welcome to the FUOYE Intelligent Voting System!</p>
                
                <div class="info-box">
                    <p><strong>🔐 Email Verification Required</strong></p>
                    <p>To complete your registration and ensure account security, please verify your FUOYE email address.</p>
                </div>
                
                <p>Click the button below to verify your email:</p>
                
                <div style="text-align: center;">
                    <a href="{{ verification_link }}" class="button">Verify Email</a>
                </div>
                
                <p style="margin-top: 20px; color: #6b7280;">Or copy and paste this link in your browser:</p>
                <div class="token-box">{{ verification_link }}</div>
                
                <div class="warning">
                    <p><strong>⚠️ Important:</strong></p>
                    <ul>
                        <li>This link expires in 24 hours</li>
                        <li>You must use your FUOYE email (@fuoye.edu.ng)</li>
                        <li>Only FUOYE students and staff can register</li>
                        <li>Do not share this link with anyone</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                    If you didn't create this account, please ignore this email or contact the system administrator.
                </p>
            </div>
            
            <div class="footer">
                <p>© 2026 FUOYE Intelligent Voting System</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = Message(
            subject='Verify Your FUOYE Email - Voting System Registration',
            recipients=[user_email]
        )
        
        msg.html = render_template_string(
            email_template,
            user_name=user_name,
            verification_link=verification_link
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def send_password_reset_email(mail, user_email, user_name, reset_token):
    """Send password reset email"""
    # Implementation here
    pass


def send_election_notification(mail, user_email, user_name, election_title):
    """Send election notification email"""
    # Implementation here
    pass