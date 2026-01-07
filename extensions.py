"""
Flask extensions initialization
This file prevents circular imports by initializing extensions separately
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_cors import CORS
from flask_session import Session
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate() 
mail = Mail()
cors = CORS()
session = Session()


def init_extensions(app):
    """Initialize all Flask extensions with app context"""
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db) 
    mail.init_app(app)
    cors.init_app(app, supports_credentials=True)
    session.init_app(app)