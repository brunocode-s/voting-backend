"""
utils/config_helper.py  (updated)
– Removed FUOYE-specific email domain enforcement.
– is_valid_email() now accepts any well-formed address.
– Legacy is_valid_fuoye_email kept as a no-op alias so existing imports
  don't crash during migration (remove after cleanup).
"""

import re
import json
from extensions import db
from models.audit import SystemConfiguration


# ─────────────────────────────────────────────────────────────────────────────
# Email validation (domain-agnostic)
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)


def is_valid_email(email: str) -> bool:
    """Return True for any syntactically valid e-mail address."""
    if not email or '@' not in email:
        return False
    return bool(EMAIL_REGEX.match(email.strip().lower()))


# ── Legacy alias — kept so old imports don't break immediately ────────────────
def is_valid_fuoye_email(email: str) -> bool:
    """
    DEPRECATED — domain restriction removed.
    Now simply delegates to is_valid_email().
    Remove all call-sites then delete this function.
    """
    return is_valid_email(email)


def get_email_domain_error() -> str:
    """
    DEPRECATED — domain restriction removed.
    Returns an empty string so any leftover call doesn't crash.
    """
    return ''


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic system configuration helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_system_config(key: str, default=None):
    """Read a value from the SystemConfiguration table."""
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
    except Exception:
        pass
    return default


def set_system_config(key: str, value, config_type: str = 'string', description: str = ''):
    """Write (upsert) a value in the SystemConfiguration table."""
    config = SystemConfiguration.query.filter_by(config_key=key).first()
    if not config:
        config = SystemConfiguration(config_key=key)

    config.config_value = json.dumps(value) if config_type == 'json' else str(value)
    config.config_type  = config_type
    config.description  = description

    db.session.add(config)
    db.session.commit()
    return config