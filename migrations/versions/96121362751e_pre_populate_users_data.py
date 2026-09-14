"""pre-populate users data for Users table

Revision ID: 96121362751e
Revises: 8a419f2d7d9d
Create Date: 2026-04-07 18:40:42.124555

"""
from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import UUID, uuid7
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96121362751e'
down_revision: Union[str, Sequence[str], None] = '8a419f2d7d9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Define pre-population tables
    users_table: sa.Table = op.create_table(
        'users',
        sa.Column('id', sa.UUID(as_uuid=True), autoincrement=False, nullable=False),
        sa.Column('role_id', sa.UUID(as_uuid=True), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=255, collation=None), autoincrement=False, nullable=False),
        sa.Column('email', sa.VARCHAR(length=255, collation=None), autoincrement=False, nullable=True),
        sa.Column('create_on', sa.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f(name='PK_USER_ID')),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('FK_USER_ROLE_ID'), onupdate='CASCADE', ondelete='CASCADE', match='FULL'),
        sa.UniqueConstraint('email', name=op.f(name='UK_USER_EMAIL'), postgresql_include=[], postgresql_nulls_not_distinct=False),
        if_not_exists=True
    )


    #  Get database connection so that we can get populated data from
    # `Roles` table
    roles_bind: sa.Connection = op.get_bind()

    # Get created `Roles` table in the db after running the 1st migration script
    roles_table: sa.Table = sa.Table(
        'roles',
        sa.MetaData(),
        # This will lift the heavy work for us by correctly get all columns
        # defined in the table
        autoload_with=roles_bind
    )

    # NOTE:
    # Equivalent SQL query from this ORM style is:
    #   SELECT 
    #       id,
    #       name
    #   FROM
    #       public.roles
    #   WHERE 
    #       name ILIKE 'admin'
    #   OR
    #       name ILIKE 'user'
    roles_stmt: sa.Select[tuple[str, str]] = (
        sa.select(
            roles_table.c.id,
            roles_table.c.name
        )
        .where(
            sa.or_(
                roles_table.c.name.ilike('admin'),
                roles_table.c.name.ilike('user')
            )
        )
    )

    roles_result: sa.CursorResult[tuple[str, str]] = roles_bind.execute(statement=roles_stmt)
    roles_id: dict[str, str] = {
        # Normalise to lowercase no matter what the result would look like in
        # term of naming format
        roles_row.name.lower(): roles_row.id
        for roles_row in roles_result
    }

    # Define data to pre-populate to 'Users' table
    users_data: list[dict[str, UUID | str | None | datetime]] = [
        {
            'id': uuid7(),
            'role_id': roles_id["admin"],
            'name': 'cosmic',
            'email': 'opensi@canberra.edu.au',
            'create_on': datetime.now(tz=timezone.utc)
        }
    ]

    # Pre-populating in bulk (insertion order matters)
    op.bulk_insert(
        table=users_table,
        rows=users_data,
        multiinsert=True # Set to 'False' if pass in pre-populate data literally
    )

    return None


def downgrade() -> None:
    """Downgrade schema."""
    # Wipes table, any FK relationship, and its data automatically since this's
    # just a fresh run
    op.drop_table(
        table_name='users',
        schema='public',
        if_exists=True
    )

    return None
