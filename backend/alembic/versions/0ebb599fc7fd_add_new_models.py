"""Add new models

Revision ID: 0ebb599fc7fd
Revises: d15993654ea8
Create Date: 2025-01-02 23:14:56.491378

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '0ebb599fc7fd'
down_revision = 'd15993654ea8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('white_label',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('source_id', sa.String(), nullable=False),
    sa.Column('redirect_url', sa.String(), nullable=False),
    sa.Column('client_id', sa.String(), nullable=False),
    sa.Column('client_secret', sa.String(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('modified_at', sa.DateTime(), nullable=False),
    sa.Column('created_by_email', sa.String(), nullable=False),
    sa.Column('modified_by_email', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_email'], ['user.email'], ),
    sa.ForeignKeyConstraint(['modified_by_email'], ['user.email'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sync_job',
    sa.Column('sync_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='syncjobstatus'), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('failed_at', sa.DateTime(), nullable=True),
    sa.Column('chunks_detected', sa.Integer(), nullable=False),
    sa.Column('chunks_inserted', sa.Integer(), nullable=False),
    sa.Column('chunks_deleted', sa.Integer(), nullable=False),
    sa.Column('chunks_skipped', sa.Integer(), nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('modified_at', sa.DateTime(), nullable=False),
    sa.Column('created_by_email', sa.String(), nullable=False),
    sa.Column('modified_by_email', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_email'], ['user.email'], ),
    sa.ForeignKeyConstraint(['modified_by_email'], ['user.email'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['sync_id'], ['sync.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chunk',
    sa.Column('sync_job_id', sa.UUID(), nullable=False),
    sa.Column('sync_id', sa.UUID(), nullable=False),
    sa.Column('entity_id', sa.String(), nullable=False),
    sa.Column('hash', sa.String(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('modified_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['sync_id'], ['sync.id'], ),
    sa.ForeignKeyConstraint(['sync_job_id'], ['sync_job.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('sync', sa.Column('description', sa.String(), nullable=True))
    op.add_column('sync', sa.Column('cron_schedule', sa.String(length=100), nullable=False))
    op.add_column('sync', sa.Column('white_label_id', sa.UUID(), nullable=True))
    op.add_column('sync', sa.Column('white_label_user_identifier', sa.String(length=256), nullable=True))
    op.create_unique_constraint('uq_white_label_user', 'sync', ['white_label_id', 'white_label_user_identifier'])
    op.create_foreign_key(None, 'sync', 'white_label', ['white_label_id'], ['id'])
    op.drop_column('sync', 'schedule')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sync', sa.Column('schedule', sa.VARCHAR(length=100), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'sync', type_='foreignkey')
    op.drop_constraint('uq_white_label_user', 'sync', type_='unique')
    op.drop_column('sync', 'white_label_user_identifier')
    op.drop_column('sync', 'white_label_id')
    op.drop_column('sync', 'cron_schedule')
    op.drop_column('sync', 'description')
    op.drop_table('chunk')
    op.drop_table('sync_job')
    op.drop_table('white_label')
    # ### end Alembic commands ###
