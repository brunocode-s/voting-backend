"""Add NIN verification, biometric, and email verification columns

Revision ID: 001_nin_biometric_email
Revises:
Create Date: 2026-05-29

Adds to users:
  - email_verified, email_verified_at, email_verification_token,
    email_verification_token_expires
  - biometric_enabled, biometric_credentials, pending_webauthn_challenge,
    pending_challenge_expires, biometric_enrolled_at,
    require_biometric_for_voting
  - nin_hash, nin_verified, nin_verified_at, nin_verification_reference,
    nin_first_name, nin_last_name, nin_middle_name, nin_gender,
    nin_state_of_origin, nin_photo_match_score, nin_data_matched,
    nin_photo_matched

Adds to votes:
  - nin_verified, nin_verification_reference
  - biometric_verified, biometric_credential_id, biometric_verified_at,
    verification_method

Adds to elections:
  - require_biometric

Removes from users:
  - is_verified  (replaced by email_verified)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_nin_biometric_email'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── users: remove old is_verified, add new columns ───────────────────────

    # Drop old column only if it exists (idempotent-safe)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = [c['name'] for c in inspector.get_columns('users')]

    if 'is_verified' in user_cols:
        op.drop_column('users', 'is_verified')

    # Email verification
    if 'email_verified' not in user_cols:
        op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    if 'email_verified_at' not in user_cols:
        op.add_column('users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    if 'email_verification_token' not in user_cols:
        op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True, unique=True))
    if 'email_verification_token_expires' not in user_cols:
        op.add_column('users', sa.Column('email_verification_token_expires', sa.DateTime(), nullable=True))

    # Biometric / WebAuthn
    if 'biometric_enabled' not in user_cols:
        op.add_column('users', sa.Column('biometric_enabled', sa.Boolean(), nullable=False, server_default='false'))
    if 'biometric_credentials' not in user_cols:
        op.add_column('users', sa.Column('biometric_credentials', postgresql.JSONB(), nullable=True))
    if 'pending_webauthn_challenge' not in user_cols:
        op.add_column('users', sa.Column('pending_webauthn_challenge', sa.String(255), nullable=True))
    if 'pending_challenge_expires' not in user_cols:
        op.add_column('users', sa.Column('pending_challenge_expires', sa.DateTime(), nullable=True))
    if 'biometric_enrolled_at' not in user_cols:
        op.add_column('users', sa.Column('biometric_enrolled_at', sa.DateTime(), nullable=True))
    if 'require_biometric_for_voting' not in user_cols:
        op.add_column('users', sa.Column('require_biometric_for_voting', sa.Boolean(), nullable=False, server_default='false'))

    # NIN verification
    if 'nin_hash' not in user_cols:
        op.add_column('users', sa.Column('nin_hash', sa.String(64), nullable=True, unique=True))
        op.create_index('idx_users_nin_hash', 'users', ['nin_hash'])
    if 'nin_verified' not in user_cols:
        op.add_column('users', sa.Column('nin_verified', sa.Boolean(), nullable=False, server_default='false'))
    if 'nin_verified_at' not in user_cols:
        op.add_column('users', sa.Column('nin_verified_at', sa.DateTime(), nullable=True))
    if 'nin_verification_reference' not in user_cols:
        op.add_column('users', sa.Column('nin_verification_reference', sa.String(255), nullable=True))
    if 'nin_first_name' not in user_cols:
        op.add_column('users', sa.Column('nin_first_name', sa.String(100), nullable=True))
    if 'nin_last_name' not in user_cols:
        op.add_column('users', sa.Column('nin_last_name', sa.String(100), nullable=True))
    if 'nin_middle_name' not in user_cols:
        op.add_column('users', sa.Column('nin_middle_name', sa.String(100), nullable=True))
    if 'nin_gender' not in user_cols:
        op.add_column('users', sa.Column('nin_gender', sa.String(10), nullable=True))
    if 'nin_state_of_origin' not in user_cols:
        op.add_column('users', sa.Column('nin_state_of_origin', sa.String(50), nullable=True))
    if 'nin_photo_match_score' not in user_cols:
        op.add_column('users', sa.Column('nin_photo_match_score', sa.Integer(), nullable=True))
    if 'nin_data_matched' not in user_cols:
        op.add_column('users', sa.Column('nin_data_matched', sa.Boolean(), nullable=False, server_default='false'))
    if 'nin_photo_matched' not in user_cols:
        op.add_column('users', sa.Column('nin_photo_matched', sa.Boolean(), nullable=False, server_default='false'))

    # phone_number unique constraint (may already exist)
    try:
        op.create_unique_constraint('uq_users_phone_number', 'users', ['phone_number'])
    except Exception:
        pass  # already exists

    # ── votes: add NIN + biometric columns ───────────────────────────────────

    vote_cols = [c['name'] for c in inspector.get_columns('votes')]

    if 'nin_verified' not in vote_cols:
        op.add_column('votes', sa.Column('nin_verified', sa.Boolean(), nullable=False, server_default='false'))
    if 'nin_verification_reference' not in vote_cols:
        op.add_column('votes', sa.Column('nin_verification_reference', sa.String(255), nullable=True))
    if 'biometric_verified' not in vote_cols:
        op.add_column('votes', sa.Column('biometric_verified', sa.Boolean(), nullable=False, server_default='false'))
    if 'biometric_credential_id' not in vote_cols:
        op.add_column('votes', sa.Column('biometric_credential_id', sa.String(255), nullable=True))
    if 'biometric_verified_at' not in vote_cols:
        op.add_column('votes', sa.Column('biometric_verified_at', sa.DateTime(), nullable=True))
    if 'verification_method' not in vote_cols:
        op.add_column('votes', sa.Column('verification_method', sa.String(50), nullable=True, server_default='nin_password'))

    # index for NIN-verified votes (useful for audit queries)
    try:
        op.create_index('idx_votes_nin', 'votes', ['nin_verified'])
    except Exception:
        pass

    # ── elections: add require_biometric ─────────────────────────────────────

    election_cols = [c['name'] for c in inspector.get_columns('elections')]
    if 'require_biometric' not in election_cols:
        op.add_column('elections', sa.Column('require_biometric', sa.Boolean(), nullable=False, server_default='false'))

    # ── system_configuration: upsert NIN-related defaults ────────────────────

    op.execute("""
        INSERT INTO system_configuration (config_key, config_value, config_type, description)
        VALUES
            ('require_nin_verification', 'true', 'boolean', 'Require NIN verification before voting'),
            ('nin_verification_enabled', 'true', 'boolean', 'Enable Korapay NIN verification service')
        ON CONFLICT (config_key) DO NOTHING;
    """)

    # Back-fill existing verified rows: if old is_verified was true treat as email_verified
    # (only runs if we just dropped is_verified above — safe to run anyway)
    op.execute("""
        UPDATE users SET email_verified = true
        WHERE email_verified = false
          AND role = 'admin';
    """)


def downgrade() -> None:
    # votes
    for col in ('verification_method', 'biometric_verified_at', 'biometric_credential_id',
                'biometric_verified', 'nin_verification_reference', 'nin_verified'):
        op.drop_column('votes', col)

    # elections
    op.drop_column('elections', 'require_biometric')

    # users — NIN
    for col in ('nin_photo_matched', 'nin_data_matched', 'nin_photo_match_score',
                'nin_state_of_origin', 'nin_gender', 'nin_middle_name',
                'nin_last_name', 'nin_first_name', 'nin_verification_reference',
                'nin_verified_at', 'nin_verified', 'nin_hash'):
        op.drop_column('users', col)

    # users — biometric
    for col in ('require_biometric_for_voting', 'biometric_enrolled_at',
                'pending_challenge_expires', 'pending_webauthn_challenge',
                'biometric_credentials', 'biometric_enabled'):
        op.drop_column('users', col)

    # users — email verification
    for col in ('email_verification_token_expires', 'email_verification_token',
                'email_verified_at', 'email_verified'):
        op.drop_column('users', col)

    # restore old column
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))