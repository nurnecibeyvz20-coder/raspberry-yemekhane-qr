"""guest requests

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("guest_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ad", sa.String(80), nullable=False), sa.Column("soyad", sa.String(80), nullable=False),
        sa.Column("tc_kimlik_no", sa.String(11)), sa.Column("telefon", sa.String(20), nullable=False),
        sa.Column("ziyaret_nedeni", sa.String(300), nullable=False), sa.Column("ziyaret_tarihi", sa.Date(), nullable=False),
        sa.Column("yemek_adedi", sa.Integer(), nullable=False), sa.Column("kalan_hak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baslangic_saati", sa.Time(), nullable=False), sa.Column("bitis_saati", sa.Time(), nullable=False),
        sa.Column("durum", sa.String(12), nullable=False, server_default="pending"), sa.Column("qr_secret", sa.String(64), unique=True),
        sa.Column("red_nedeni", sa.String(300)), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_guest_requests_owner_id", "guest_requests", ["owner_id"])
    op.create_index("ix_guest_requests_ziyaret_tarihi", "guest_requests", ["ziyaret_tarihi"])
    op.create_table("guest_request_events",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("request_id", sa.Integer(), sa.ForeignKey("guest_requests.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(300), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_index("ix_guest_request_events_request_id", "guest_request_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_guest_request_events_request_id", table_name="guest_request_events")
    op.drop_table("guest_request_events")
    op.drop_index("ix_guest_requests_ziyaret_tarihi", table_name="guest_requests")
    op.drop_index("ix_guest_requests_owner_id", table_name="guest_requests")
    op.drop_table("guest_requests")
