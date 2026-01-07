from app import app

with app.app_context():
    print("=== Flask-Mail Configuration ===")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
    print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
    print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
    print(f"MAIL_PASSWORD: {'*' * len(app.config.get('MAIL_PASSWORD', ''))}")
    print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
    print(f"FRONTEND_URL: {app.config.get('FRONTEND_URL')}")
    
    from extensions import mail
    print(f"\nFlask-Mail initialized: {mail}")
    print(f"Mail app: {mail.app}")