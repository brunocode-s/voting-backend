"""
services/email_service.py  (updated)
– Removed FUOYE-specific branding from all templates.
– System is now referred to as "Intelligent Voting System".
– Verification template no longer mentions @fuoye.edu.ng restriction.
"""

from flask_mail import Message
from flask import render_template_string, current_app


# ─────────────────────────────────────────────────────────────────────────────
# Voter ID email  (sent after email verification)
# ─────────────────────────────────────────────────────────────────────────────

def send_voter_id_email(mail, user_email, user_name, voter_id):
    frontend_url = current_app.config.get('FRONTEND_URL', '')

    template = """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body{font-family:Arial,sans-serif;line-height:1.6;color:#333}
        .wrap{max-width:600px;margin:0 auto;padding:20px}
        .hdr{background:#065f46;color:white;padding:24px;text-align:center;border-radius:8px 8px 0 0}
        .body{background:#f9fafb;padding:30px;border:1px solid #e5e7eb}
        .id-box{background:white;border:2px solid #065f46;padding:20px;margin:20px 0;text-align:center;border-radius:8px}
        .voter-id{font-size:28px;font-weight:bold;color:#065f46;letter-spacing:2px}
        .info{background:#ecfdf5;padding:15px;border-left:4px solid #10b981;margin:15px 0}
        .warn{background:#fef3c7;padding:15px;border-left:4px solid #f59e0b;margin:15px 0}
        .footer{text-align:center;padding:20px;color:#6b7280;font-size:12px}
        .btn{display:inline-block;background:#065f46;color:white;padding:12px 30px;text-decoration:none;border-radius:6px;margin-top:15px}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hdr"><h1>🗳️ Registration Successful!</h1></div>
        <div class="body">
          <h2>Hello {{ user_name }},</h2>
          <p>Your account has been verified. You are now registered on the Intelligent Voting System.</p>

          <div class="id-box">
            <p style="margin:0;color:#6b7280;font-size:14px">Your Unique Voter ID</p>
            <p class="voter-id">{{ voter_id }}</p>
          </div>

          <div class="info">
            <p><strong>⚠️ Important — save this Voter ID</strong></p>
            <ul>
              <li>You need your Voter ID + email + password to log in.</li>
              <li>Keep this ID confidential.</li>
              <li>It's also visible in your profile after login.</li>
            </ul>
          </div>

          <div class="warn">
            <p><strong>🆔 Next step: Verify your NIN to vote</strong></p>
            <p>
              Email verification is complete, but you must also verify your
              National Identification Number (NIN) in your profile before
              you can cast a ballot.
            </p>
          </div>

          <h3>How to vote:</h3>
          <ol>
            <li>Log in with your Voter ID and email: <strong>{{ user_email }}</strong></li>
            <li>Go to <strong>Profile → NIN Verification</strong> and verify your NIN.</li>
            <li>Once NIN is confirmed, head to <strong>Vote</strong> and select your candidates.</li>
          </ol>

          <div style="text-align:center">
            <a href="{{ frontend_url }}" class="btn">Go to Voting Portal</a>
          </div>

          <p style="margin-top:30px;color:#6b7280;font-size:14px">
            If you didn't create this account, contact the system administrator immediately.
          </p>
        </div>
        <div class="footer">
          <p>© 2026 Intelligent Voting System</p>
          <p>This is an automated message. Please do not reply.</p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = Message(
            subject='Your Voter ID — Registration Complete',
            recipients=[user_email],
        )
        msg.html = render_template_string(
            template,
            user_name=user_name,
            voter_id=voter_id,
            user_email=user_email,
            frontend_url=frontend_url,
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send voter ID email: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Verification email  (sent on registration)
# ─────────────────────────────────────────────────────────────────────────────

def send_verification_email(mail, user_email, user_name, verification_token, frontend_url):
    verification_link = f"{frontend_url}/verify-email?token={verification_token}"

    template = """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body{font-family:Arial,sans-serif;line-height:1.6;color:#333}
        .wrap{max-width:600px;margin:0 auto;padding:20px}
        .hdr{background:#065f46;color:white;padding:24px;text-align:center;border-radius:8px 8px 0 0}
        .body{background:#f9fafb;padding:30px;border:1px solid #e5e7eb}
        .info{background:#ecfdf5;padding:15px;border-left:4px solid #10b981;margin:15px 0}
        .token{background:white;border:1px solid #d1d5db;padding:15px;margin:15px 0;border-radius:6px;font-family:monospace;word-break:break-all}
        .warn{background:#fef3c7;border:1px solid #fcd34d;padding:15px;border-radius:6px;margin:15px 0}
        .footer{text-align:center;padding:20px;color:#6b7280;font-size:12px}
        .btn{display:inline-block;background:#065f46;color:white;padding:12px 30px;text-decoration:none;border-radius:6px;margin-top:15px}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hdr"><h1>🔐 Verify Your Email</h1></div>
        <div class="body">
          <h2>Hello {{ user_name }},</h2>
          <p>Welcome to the Intelligent Voting System! Please verify your email to activate your account.</p>

          <div class="info">
            <p><strong>Email Verification Required</strong></p>
            <p>Click the button below to verify your email address.</p>
          </div>

          <div style="text-align:center">
            <a href="{{ verification_link }}" class="btn">Verify Email</a>
          </div>

          <p style="margin-top:20px;color:#6b7280">Or paste this link in your browser:</p>
          <div class="token">{{ verification_link }}</div>

          <div class="warn">
            <p><strong>⚠️ Important:</strong></p>
            <ul>
              <li>This link expires in <strong>24 hours</strong>.</li>
              <li>After email verification, verify your <strong>NIN</strong> in your profile to become eligible to vote.</li>
              <li>Do not share this link with anyone.</li>
            </ul>
          </div>

          <p style="margin-top:30px;color:#6b7280;font-size:14px">
            If you didn't create this account, you can safely ignore this email.
          </p>
        </div>
        <div class="footer">
          <p>© 2026 Intelligent Voting System</p>
          <p>This is an automated message. Please do not reply.</p>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = Message(
            subject='Verify Your Email — Intelligent Voting System',
            recipients=[user_email],
        )
        msg.html = render_template_string(template, user_name=user_name, verification_link=verification_link)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send verification email: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Stubs
# ─────────────────────────────────────────────────────────────────────────────
def send_password_reset_email(mail, user_email, user_name, reset_token):
    """Password reset email — was a stub, now implemented."""
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    reset_link   = f"{frontend_url}/reset-password?token={reset_token}"
 
    template = """<!DOCTYPE html><html><head><style>
      body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.wrap{max-width:600px;margin:0 auto;padding:20px}
      .hdr{background:#1e40af;color:white;padding:24px;text-align:center;border-radius:8px 8px 0 0}
      .body{background:#f9fafb;padding:30px;border:1px solid #e5e7eb}
      .info{background:#eff6ff;padding:15px;border-left:4px solid #3b82f6;margin:15px 0}
      .token{background:white;border:1px solid #d1d5db;padding:15px;margin:15px 0;border-radius:6px;font-family:monospace;word-break:break-all}
      .warn{background:#fef2f2;border:1px solid #fca5a5;padding:15px;border-radius:6px;margin:15px 0}
      .footer{text-align:center;padding:20px;color:#6b7280;font-size:12px}
      .btn{display:inline-block;background:#1e40af;color:white;padding:12px 30px;text-decoration:none;border-radius:6px;margin-top:15px}
    </style></head><body><div class="wrap">
      <div class="hdr"><h1>Password Reset Request</h1></div>
      <div class="body">
        <h2>Hello {{ user_name }},</h2>
        <p>We received a request to reset the password for your account.</p>
        <div class="info"><p><strong>Reset your password</strong></p><p>Click below — this link is valid for <strong>1 hour</strong>.</p></div>
        <div style="text-align:center"><a href="{{ reset_link }}" class="btn">Reset Password</a></div>
        <p style="margin-top:20px;color:#6b7280">Or paste this link in your browser:</p>
        <div class="token">{{ reset_link }}</div>
        <div class="warn"><p><strong>Did not request this?</strong></p>
          <p>Ignore this email — your password will not change. If you are concerned, contact support.</p>
        </div>
      </div>
      <div class="footer"><p>© 2026 Intelligent Voting System — automated message, do not reply.</p></div>
    </div></body></html>"""
 
    try:
        msg = Message(subject='Reset Your Password — Intelligent Voting System', recipients=[user_email])
        msg.html = render_template_string(template, user_name=user_name, reset_link=reset_link)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[EMAIL] password_reset: {e}")
        return False

def send_election_notification(mail, user_email, user_name, election_title):
    """TODO: implement election notification email."""
    pass