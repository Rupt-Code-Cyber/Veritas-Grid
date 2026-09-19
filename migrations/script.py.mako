"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import context
from sqlalchemy import engine_from_config, pool
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Atomic transaction wrapper logic to migrate schema models forward."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Atomic transaction wrapper fallback logic to safely roll schema states backward."""
    ${downgrades if downgrades else "pass"}
