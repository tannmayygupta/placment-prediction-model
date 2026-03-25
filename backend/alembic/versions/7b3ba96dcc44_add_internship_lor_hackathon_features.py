"""add_internship_lor_hackathon_features

Revision ID: 7b3ba96dcc44
Revises: eca4dd22ee2d
Create Date: 2026-03-22 01:43:10.331315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3ba96dcc44'
down_revision: Union[str, Sequence[str], None] = 'eca4dd22ee2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # student_profiles
    op.add_column('student_profiles', sa.Column(
        'internship_duration_weeks', sa.SmallInteger(), nullable=True, server_default=sa.text('0')))
    op.add_column('student_profiles', sa.Column(
        'internship_verified', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('student_profiles', sa.Column(
        'lor_industry_count', sa.SmallInteger(), nullable=True, server_default=sa.text('0')))
    op.add_column('student_profiles', sa.Column(
        'lor_academic_count', sa.SmallInteger(), nullable=True, server_default=sa.text('0')))

    # lors
    op.create_table('lors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('profile_id', sa.String(36),
            sa.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('institution', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # hackathon_certs
    op.create_table('hackathon_certs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('profile_id', sa.String(36),
            sa.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_name', sa.Text(), nullable=False),
        sa.Column('prize_level', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # submissions
    op.add_column('submissions', sa.Column('base_probability', sa.Numeric(5, 2), nullable=True))
    op.add_column('submissions', sa.Column('adjustment_delta', sa.Numeric(6, 3), nullable=True))
    op.add_column('submissions', sa.Column('adjustment_breakdown', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('submissions', 'adjustment_breakdown')
    op.drop_column('submissions', 'adjustment_delta')
    op.drop_column('submissions', 'base_probability')
    op.drop_table('hackathon_certs')
    op.drop_table('lors')
    op.drop_column('student_profiles', 'lor_academic_count')
    op.drop_column('student_profiles', 'lor_industry_count')
    op.drop_column('student_profiles', 'internship_verified')
    op.drop_column('student_profiles', 'internship_duration_weeks')