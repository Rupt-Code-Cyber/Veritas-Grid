"""Initial database schema baseline configuration snapshot footprint.

Revision ID: 0001_init_db
Revises: None
Create Date: 2026-09-15 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import context
import sqlalchemy as sa


# Revision identifiers, utilized meticulously by the Alembic tracking runtime
revision: str = '0001_init_db'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Atomic transaction layer to build out the multi-tenant relational schema blueprint from scratch."""
    context.execute(
        sa.text("""
            CREATE TABLE IF NOT EXISTS anonymous_ledger_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracker_token TEXT NOT NULL UNIQUE,
                tenant_id TEXT NOT NULL,
                matched_category TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                regulatory_routing_target TEXT NOT NULL,
                anonymized_evidence_body TEXT NOT NULL,
                saved_media_path TEXT,
                keyword_match_density INTEGER DEFAULT 0,
                timestamp_utc DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    )
    
    # Instantiate database tracking indexing profiles explicitly to maintain optimization parity
    context.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_tenant ON anonymous_ledger_records(tenant_id)"))
    context.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_token ON anonymous_ledger_records(tracker_token)"))


def downgrade() -> None:
    """Fallback teardown transaction layer to drop database tables if structural schema states roll backward."""
    context.execute(sa.text("DROP INDEX IF EXISTS idx_token"))
    context.execute(sa.text("DROP INDEX IF EXISTS idx_tenant"))
    context.execute(sa.text("DROP TABLE IF EXISTS anonymous_ledger_records"))
