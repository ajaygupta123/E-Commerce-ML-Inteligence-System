"""add_llm_call_logs_table

Revision ID: 4a8f2e1b9c3d
Revises: 323b50f84bca
Create Date: 2026-01-07 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4a8f2e1b9c3d'
down_revision: Union[str, None] = '323b50f84bca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create llm_call_logs table
    op.create_table(
        'llm_call_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('queue_wait_ms', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('retry_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('query_log_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create foreign key to query_logs
    op.create_foreign_key(
        'fk_llm_call_logs_query_log_id',
        'llm_call_logs',
        'query_logs',
        ['query_log_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for analytics queries
    op.create_index('ix_llm_call_logs_created_at', 'llm_call_logs', ['created_at'])
    op.create_index('ix_llm_call_logs_model_name', 'llm_call_logs', ['model_name'])
    op.create_index('ix_llm_call_logs_query_log_id', 'llm_call_logs', ['query_log_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_llm_call_logs_query_log_id', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_model_name', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_created_at', table_name='llm_call_logs')
    
    # Drop foreign key
    op.drop_constraint('fk_llm_call_logs_query_log_id', 'llm_call_logs', type_='foreignkey')
    
    # Drop table
    op.drop_table('llm_call_logs')

