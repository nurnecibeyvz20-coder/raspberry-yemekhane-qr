"""registration status and permanent QR secret

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("registration_status", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("qr_secret", sa.String(64), nullable=True))
    op.execute("UPDATE users SET registration_status = 'approved'")
    op.alter_column("users", "registration_status", nullable=False,
                    server_default="approved")
    op.create_unique_constraint("uq_users_qr_secret", "users", ["qr_secret"])


def downgrade() -> None:
    op.drop_constraint("uq_users_qr_secret", "users", type_="unique")
    op.drop_column("users", "qr_secret")
    op.drop_column("users", "registration_status")
