"""add_drift_and_model_versioning

Revision ID: 7f3a8b2c9d1e
Revises: 4a8f2e1b9c3d
Create Date: 2026-01-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7f3a8b2c9d1e'
down_revision: Union[str, None] = '4a8f2e1b9c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ground truth fields to prediction_logs
    op.add_column('prediction_logs', sa.Column('actual_discount', sa.Float(), nullable=True))
    op.add_column('prediction_logs', sa.Column('has_feedback', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create drift_logs table
    op.create_table(
        'drift_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('detection_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('data_drift_score', sa.Float(), nullable=False),
        sa.Column('performance_drift_score', sa.Float(), nullable=True),
        sa.Column('drift_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recommendation', sa.String(length=50), nullable=False),
        sa.Column('drift_metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for drift_logs
    op.create_index('ix_drift_logs_detection_date', 'drift_logs', ['detection_date'])
    
    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(length=100), nullable=False, unique=True),
        sa.Column('model_path', sa.String(length=500), nullable=False),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('training_metrics', postgresql.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('drift_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for model_versions
    op.create_index('ix_model_versions_version', 'model_versions', ['version'])
    op.create_index('ix_model_versions_is_active', 'model_versions', ['is_active'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_model_versions_is_active', table_name='model_versions')
    op.drop_index('ix_model_versions_version', table_name='model_versions')
    op.drop_index('ix_drift_logs_detection_date', table_name='drift_logs')
    
    # Drop tables
    op.drop_table('model_versions')
    op.drop_table('drift_logs')
    
    # Remove columns from prediction_logs
    op.drop_column('prediction_logs', 'has_feedback')
    op.drop_column('prediction_logs', 'actual_discount')

