"""pre-populate configs data for Configurations table

Revision ID: a3e40b0c0b7b
Revises: 51a0ff6b910d
Create Date: 2026-04-20 19:37:59.722834

"""
from typing import (
    Any,
    Sequence,
    Union
)
from uuid import (
    UUID,
    uuid7
)
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from datetime import (
    datetime,
    timezone
)
from pydantic import (
    BaseModel,
    ConfigDict
)
from cores.db import cosmic_db_configs



# revision identifiers, used by Alembic.
revision: str = 'a3e40b0c0b7b'
down_revision: Union[str, Sequence[str], None] = '51a0ff6b910d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



#==============================================================================#
# This's copied from `types/json_schemas.py` file because each migration script#
# will be executed independently before FastAPI started up, hence it cannot    #
# "see" these defined Pydantic's Base Model so that we can directly import it. #
#==============================================================================#
class GeneralConfigs(BaseModel):
    """docstring for GeneralConfigs."""
    model_config = ConfigDict(extra="forbid")

    provider:               str         = "ollama"
    model:                  str         = "qwen2.5:0.5b"
    is_quantised:           bool        = False
    seed:                   int         = 0
    default_knowledge_path: str         = "/app/data/default/"
    temp_knowledge_path:    str         = "/app/data/temp/"
    api_key:                str | None  = cosmic_db_configs.get("OPENAI_API_KEY", None)


class QueryAnalyserConfigs(GeneralConfigs):
    """docstring for QueryAnalyserConfigs."""
    model_config = ConfigDict(extra="forbid")

    pass


class ConfigurationSchema(BaseModel):
    """docstring for ConfigurationSchema."""
    model_config = ConfigDict(extra="forbid")

    general:        GeneralConfigs
    query_analyser: QueryAnalyserConfigs



#==============================================================================#
#                   Migration script logic starts from here                    #
#==============================================================================#
def upgrade() -> None:
    """Upgrade schema."""
    # Define pre-population tables
    configs_table: sa.Table = op.create_table(
        'configurations',
        sa.Column('id', sa.UUID(as_uuid=True), autoincrement=False, nullable=False),
        sa.Column('name', sa.TEXT(length=None, collation=None), autoincrement=False, nullable=True),
        sa.Column('details', JSONB(none_as_null=True,astext_type=None), autoincrement=False, nullable=False),
        sa.Column('create_on', sa.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f(name='PK_CONFIGURATION_ID')),
        if_not_exists=True
    )

    # Define data to pre-populate to 'Configurations' table
    configs_data: list[dict[str, UUID | str | dict[str, Any] | datetime]] = [
        {
            'id': uuid7(),
            'name': 'Default Configuration',
            # Need to use `model_dump()` method so Python can see the JSON data
            # as built-in dict type
            'details': ConfigurationSchema(
                general=GeneralConfigs(),
                query_analyser=QueryAnalyserConfigs()
            ).model_dump(mode="json", exclude_unset=False),
            'create_on': datetime.now(tz=timezone.utc)
        }
    ]

    # Pre-populating in bulk (insertion order matters)
    op.bulk_insert(
        table=configs_table,
        rows=configs_data,
        multiinsert=True # Set to 'False' if pass in pre-populate data literally
    )

    return None


def downgrade() -> None:
    """Downgrade schema."""
    # Wipes table, any FK relationship, and its data automatically since this's
    # just a fresh run
    op.drop_table(
        table_name='configurations',
        schema='public',
        if_exists=True
    )

    return None
