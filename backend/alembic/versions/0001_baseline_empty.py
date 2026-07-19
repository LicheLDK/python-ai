"""baseline_empty

Revision ID: 0001_baseline_empty
Revises:
Create Date: 2026-07-18

Empty baseline migration for T-0.06.
No domain tables yet (User/Auth models belong to later tasks).
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001_baseline_empty"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op baseline — establishes Alembic version table only."""
    pass


def downgrade() -> None:
    """No-op baseline downgrade."""
    pass
