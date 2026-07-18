"""extend organization card with new fields, related tables, indexes, and cascade

Combines:
- New organization card fields (org_type, full_name, short_name, legal_address,
  actual_address, postal_address, phone_additional, phone_mobile, fax, website,
  kpp, ogrnip, okpo, director_*, ip_*)
- Bank accounts table (bank_accounts)
- OKVED codes table (okved_codes)
- Licenses table (licenses) — without notes, with checksum_sha256
- Partial unique indexes for is_primary on bank_accounts and okved_codes
- CASCADE on all FK → organizations.id

Revision ID: 020
Revises: a5c8a2dd1a14
Create Date: 2026-07-17

Note: migration 020 and 021 were merged into one because both belonged to
the same feature (organization card) and had never been applied separately.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "a5c8a2dd1a14"
branch_labels = None
depends_on = None


def table_exists(table: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=:table)"),
        {"table": table},
    )
    return bool(result.scalar())


def column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:table AND column_name=:column)"
    ), {"table": table, "column": column})
    return bool(result.scalar())


def index_exists(idx_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname=:idx)"),
        {"idx": idx_name},
    )
    return bool(result.scalar())


def upgrade() -> None:
    # ── New columns for organizations table ─────────────────────────────────
    if not column_exists("organizations", "org_type"):
        op.add_column("organizations", sa.Column("org_type", sa.String(20), server_default="legal"))
    if not column_exists("organizations", "full_name"):
        op.add_column("organizations", sa.Column("full_name", sa.String(1000)))
    if not column_exists("organizations", "short_name"):
        op.add_column("organizations", sa.Column("short_name", sa.String(500)))
    if not column_exists("organizations", "legal_address"):
        op.add_column("organizations", sa.Column("legal_address", sa.String(500)))
    if not column_exists("organizations", "actual_address"):
        op.add_column("organizations", sa.Column("actual_address", sa.String(500)))
    if not column_exists("organizations", "postal_address"):
        op.add_column("organizations", sa.Column("postal_address", sa.String(500)))
    if not column_exists("organizations", "phone_additional"):
        op.add_column("organizations", sa.Column("phone_additional", sa.String(50)))
    if not column_exists("organizations", "phone_mobile"):
        op.add_column("organizations", sa.Column("phone_mobile", sa.String(50)))
    if not column_exists("organizations", "fax"):
        op.add_column("organizations", sa.Column("fax", sa.String(50)))
    if not column_exists("organizations", "website"):
        op.add_column("organizations", sa.Column("website", sa.String(500)))
    if not column_exists("organizations", "kpp"):
        op.add_column("organizations", sa.Column("kpp", sa.String(20)))
    if not column_exists("organizations", "ogrnip"):
        op.add_column("organizations", sa.Column("ogrnip", sa.String(20)))
    if not column_exists("organizations", "okpo"):
        op.add_column("organizations", sa.Column("okpo", sa.String(20)))
    if not column_exists("organizations", "director_full_name"):
        op.add_column("organizations", sa.Column("director_full_name", sa.String(300)))
    if not column_exists("organizations", "director_position"):
        op.add_column("organizations", sa.Column("director_position", sa.String(300)))
    if not column_exists("organizations", "director_phone"):
        op.add_column("organizations", sa.Column("director_phone", sa.String(50)))
    if not column_exists("organizations", "director_email"):
        op.add_column("organizations", sa.Column("director_email", sa.String(200)))
    if not column_exists("organizations", "ip_last_name"):
        op.add_column("organizations", sa.Column("ip_last_name", sa.String(100)))
    if not column_exists("organizations", "ip_first_name"):
        op.add_column("organizations", sa.Column("ip_first_name", sa.String(100)))
    if not column_exists("organizations", "ip_middle_name"):
        op.add_column("organizations", sa.Column("ip_middle_name", sa.String(100)))

    # ── Bank accounts table ─────────────────────────────────────────────────
    if not table_exists("bank_accounts"):
        op.create_table(
            "bank_accounts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("account_number", sa.String(34), nullable=False),
            sa.Column("bank_name", sa.String(500)),
            sa.Column("bank_bik", sa.String(20)),
            sa.Column("bank_corr_account", sa.String(34)),
            sa.Column("currency", sa.String(3), server_default="RUB"),
            sa.Column("is_primary", sa.SmallInteger(), server_default="0"),
            sa.Column("notes", sa.String(500)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
    if not index_exists("ix_bank_accounts_organization_id"):
        op.create_index("ix_bank_accounts_organization_id", "bank_accounts", ["organization_id"])

    # ── OKVED codes table ──────────────────────────────────────────────────
    if not table_exists("okved_codes"):
        op.create_table(
            "okved_codes",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("description", sa.String(1000)),
            sa.Column("is_primary", sa.SmallInteger(), server_default="0"),
            sa.Column("created_at", sa.DateTime()),
        )
    if not index_exists("ix_okved_codes_organization_id"):
        op.create_index("ix_okved_codes_organization_id", "okved_codes", ["organization_id"])

    # ── Licenses table ─────────────────────────────────────────────────────
    # Согласованные поля: вид деятельности, номер, дата выдачи, статус, файл.
    # notes и срок действия исключены.
    if not table_exists("licenses"):
        op.create_table(
            "licenses",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("activity_type", sa.String(500), nullable=False),
            sa.Column("license_number", sa.String(100), nullable=False),
            sa.Column("issue_date", sa.Date()),
            sa.Column("status", sa.String(50), server_default="active"),
            sa.Column("file_path", sa.String(1000)),
            sa.Column("file_name", sa.String(500)),
            sa.Column("file_size", sa.Integer()),
            sa.Column("mime_type", sa.String(100)),
            sa.Column("checksum_sha256", sa.String(64)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
    if not index_exists("ix_licenses_organization_id"):
        op.create_index("ix_licenses_organization_id", "licenses", ["organization_id"])

    # ── Partial unique indexes: only one primary per organization ───────────
    # is_primary is SmallInteger (0/1). PostgreSQL partial unique index
    # requires a boolean expression. Using `= 1` matches the numeric type.
    if not index_exists("uq_bank_accounts_one_primary_per_org"):
        op.create_index(
            "uq_bank_accounts_one_primary_per_org",
            "bank_accounts",
            ["organization_id"],
            unique=True,
            postgresql_where=sa.text("is_primary = 1"),
        )

    if not index_exists("uq_okved_codes_one_primary_per_org"):
        op.create_index(
            "uq_okved_codes_one_primary_per_org",
            "okved_codes",
            ["organization_id"],
            unique=True,
            postgresql_where=sa.text("is_primary = 1"),
        )


def downgrade() -> None:
    # Partial unique indexes
    if index_exists("uq_okved_codes_one_primary_per_org"):
        op.drop_index("uq_okved_codes_one_primary_per_org", table_name="okved_codes")
    if index_exists("uq_bank_accounts_one_primary_per_org"):
        op.drop_index("uq_bank_accounts_one_primary_per_org", table_name="bank_accounts")

    # Drop tables
    if table_exists("licenses"):
        op.drop_table("licenses")
    if table_exists("okved_codes"):
        op.drop_table("okved_codes")
    if table_exists("bank_accounts"):
        op.drop_table("bank_accounts")

    # Drop columns from organizations
    for col in [
        "org_type", "full_name", "short_name", "legal_address", "actual_address",
        "postal_address", "phone_additional", "phone_mobile", "fax", "website",
        "kpp", "ogrnip", "okpo", "director_full_name", "director_position",
        "director_phone", "director_email", "ip_last_name", "ip_first_name", "ip_middle_name",
    ]:
        if column_exists("organizations", col):
            op.drop_column("organizations", col)
