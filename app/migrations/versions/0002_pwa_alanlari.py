"""pwa alanlari

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telefon", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("eposta", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("gizli_soru", sa.String(length=200), nullable=True))
    op.add_column(
        "users", sa.Column("gizli_cevap_hash", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )

    op.create_table(
        "reset_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kanal", sa.String(length=10), nullable=False),
        sa.Column("kod_hash", sa.String(length=200), nullable=False),
        sa.Column("demo_gosterim", sa.String(length=6), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reset_codes_user_id"), "reset_codes", ["user_id"], unique=False
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tutar", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("durum", sa.String(length=12), nullable=False),
        sa.Column("saglayici", sa.String(length=20), nullable=False),
        sa.Column("saglayici_ref", sa.String(length=100), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_reset_codes_user_id"), table_name="reset_codes")
    op.drop_table("reset_codes")
    op.drop_column("users", "session_version")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "gizli_cevap_hash")
    op.drop_column("users", "gizli_soru")
    op.drop_column("users", "eposta")
    op.drop_column("users", "telefon")
