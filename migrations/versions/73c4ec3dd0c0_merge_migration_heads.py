"""merge migration heads

Revision ID: 73c4ec3dd0c0
Revises: 001_nin_biometric_email, e53edabbb844
Create Date: 2026-05-29 12:06:39.155465

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73c4ec3dd0c0'
down_revision = ('001_nin_biometric_email', 'e53edabbb844')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
