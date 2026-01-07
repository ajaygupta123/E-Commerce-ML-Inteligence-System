"""remove_brand_column

Revision ID: 323b50f84bca
Revises: 
Create Date: 2026-01-06 18:27:58.913110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '323b50f84bca'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the brand column from products table
    op.drop_column('products', 'brand')


def downgrade() -> None:
    # Add the brand column back (nullable, with index)
    op.add_column('products', sa.Column('brand', sa.String(length=200), nullable=True))
    op.create_index(op.f('ix_products_brand'), 'products', ['brand'], unique=False)
