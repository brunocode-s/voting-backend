import json
from extensions import db
from models.audit import SystemConfiguration

# Email domain configuration
ALLOWED_EMAIL_DOMAINS = ['fuoye.edu.ng']
DOMAIN_ENFORCEMENT_ENABLED = True

def is_valid_fuoye_email(email):
    """Check if email belongs to allowed domain"""
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    return domain in ALLOWED_EMAIL_DOMAINS

def get_email_domain_error():
    """Get formatted error message for invalid domain"""
    domains = ', '.join(ALLOWED_EMAIL_DOMAINS)
    return f'Email must be from {domains} domain. Please use your FUOYE email address.'

def get_system_config(key, default=None):
    """Get dynamic system configuration"""
    try:
        config = SystemConfiguration.query.filter_by(config_key=key).first()
        if config:
            if config.config_type == 'integer':
                return int(config.config_value)
            elif config.config_type == 'boolean':
                return config.config_value.lower() == 'true'
            elif config.config_type == 'json':
                return json.loads(config.config_value)
            return config.config_value
    except:
        pass
    return default


def set_system_config(key, value, config_type='string', description=''):
    """Set dynamic system configuration"""
    config = SystemConfiguration.query.filter_by(config_key=key).first()
    if not config:
        config = SystemConfiguration(config_key=key)
    
    if config_type == 'json':
        config.config_value = json.dumps(value)
    else:
        config.config_value = str(value)
    
    config.config_type = config_type
    config.description = description
    
    db.session.add(config)
    db.session.commit()
    return config