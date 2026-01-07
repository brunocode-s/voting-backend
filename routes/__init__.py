from .auth import auth_bp
from .elections import elections_bp
from .voting import voting_bp
from .admin import admin_bp
from .results import results_bp

__all__ = [
    'auth_bp',
    'elections_bp',
    'voting_bp',
    'admin_bp',
    'results_bp'
]