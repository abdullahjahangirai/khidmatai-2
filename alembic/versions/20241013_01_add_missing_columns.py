"""Add missing columns to existing tables.

Revision ID: 20241013_01_add_missing_columns
Revises: None
Create Date: 2024-10-13 04:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20241013_01_add_missing_columns"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # contacts: add is_public (default True)
    op.add_column('contacts', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    # branches: add verification_status, google_place_id, google_business_location_id, is_public (default True)
    op.add_column('branches', sa.Column('verification_status', sa.String(), nullable=True))
    op.add_column('branches', sa.Column('google_place_id', sa.String(), nullable=True))
    op.add_column('branches', sa.Column('google_business_location_id', sa.String(), nullable=True))
    op.add_column('branches', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    # optionally, add phone column to branches if needed later
    # op.add_column('branches', sa.Column('phone', sa.String(), nullable=True))

def downgrade():
    op.drop_column('branches', 'is_public')
    op.drop_column('branches', 'google_business_location_id')
    op.drop_column('branches', 'google_place_id')
    op.drop_column('branches', 'verification_status')
    op.drop_column('contacts', 'is_public')
