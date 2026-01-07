"""Add biometric authentication support

Revision ID: biometric_auth_v1
Revises: 
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'biometric_auth_v1'
down_revision = '4c43a6b36ab1'
branch_labels = None
depends_on = None


def upgrade():
    """Add biometric authentication fields to users and votes tables"""
    
    # Add biometric fields to users table
    op.add_column('users', sa.Column('biometric_enabled', sa.Boolean(), 
                                     nullable=True, server_default='false'))
    op.add_column('users', sa.Column('biometric_credentials', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('pending_webauthn_challenge', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('pending_challenge_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('biometric_enrolled_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('require_biometric_for_voting', sa.Boolean(), 
                                     nullable=True, server_default='false'))
    
    # Add biometric verification fields to votes table
    op.add_column('votes', sa.Column('biometric_verified', sa.Boolean(), 
                                     nullable=True, server_default='false'))
    op.add_column('votes', sa.Column('biometric_credential_id', sa.String(255), nullable=True))
    op.add_column('votes', sa.Column('biometric_verified_at', sa.DateTime(), nullable=True))
    op.add_column('votes', sa.Column('verification_method', sa.String(50), nullable=True))


def downgrade():
    """Remove biometric fields"""
    
    # Remove fields from votes table
    op.drop_column('votes', 'verification_method')
    op.drop_column('votes', 'biometric_verified_at')
    op.drop_column('votes', 'biometric_credential_id')
    op.drop_column('votes', 'biometric_verified')
    
    # Remove fields from users table
    op.drop_column('users', 'require_biometric_for_voting')
    op.drop_column('users', 'biometric_enrolled_at')
    op.drop_column('users', 'pending_challenge_expires')
    op.drop_column('users', 'pending_webauthn_challenge')
    op.drop_column('users', 'biometric_credentials')
    op.drop_column('users', 'biometric_enabled')