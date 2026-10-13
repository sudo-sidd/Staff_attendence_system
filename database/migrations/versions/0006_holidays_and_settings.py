"""holidays table + singleton attendance_settings row

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_holidays_date", "holidays", ["date"])

    op.create_table(
        "attendance_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("saturday_holiday", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.execute("INSERT INTO attendance_settings (id, saturday_holiday) VALUES (1, FALSE)")


def downgrade() -> None:
    op.drop_table("attendance_settings")
    op.drop_index("ix_holidays_date", table_name="holidays")
    op.drop_table("holidays")
