"""Add cascade relationships to connection models

Revision ID: 1de8ee6ba9e0
Revises: 00cb22315e1b
Create Date: 2025-05-06 23:50:26.692377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1de8ee6ba9e0'
down_revision = '00cb22315e1b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('sync_connection_connection_id_fkey', 'sync_connection', type_='foreignkey')
    op.create_foreign_key(None, 'sync_connection', 'connection', ['connection_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'sync_connection', type_='foreignkey')
    op.create_foreign_key('sync_connection_connection_id_fkey', 'sync_connection', 'connection', ['connection_id'], ['id'])
    # ### end Alembic commands ###
