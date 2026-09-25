### Core modules ###
from sqlmodel import (
    Field,
    Relationship
)
from sqlalchemy.schema import (
    PrimaryKeyConstraint,
    UniqueConstraint,
    ForeignKeyConstraint
)


### Type hints ###
from datetime import (
    datetime,
    timezone
)
from uuid import (
    UUID,
    uuid7
)
from sqlalchemy.sql.sqltypes import (
    TIMESTAMP,
    VARCHAR,
    Uuid
)
from typing import TYPE_CHECKING
from .user_identities import UserIdentities


### Internal modules ###
from ..base_models import UserBase
if TYPE_CHECKING:
    """
    This's to resolve circular import issues, take a look at:
    https://sqlmodel.tiangolo.com/tutorial/code-structure/#circular-imports
    """
    from .roles import Roles
    from .chatboxes import Chatboxes



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class Users(UserBase, table=True):
    __tablename__: str = "users" # pyright: ignore
    __table_args__: tuple[
        PrimaryKeyConstraint,
        ForeignKeyConstraint,
        UniqueConstraint
    ] = (
        PrimaryKeyConstraint(
            "id",
            name="PK_USER_ID"
        ),
        ForeignKeyConstraint(
            columns=["role_id"],
            refcolumns=["roles.id"],
            name="FK_USER_ROLE_ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            match="FULL"
        ),
        UniqueConstraint(
            "email",
            name="UK_USER_EMAIL"
        ),
    )

    email: str | None = Field(
        default=None,
        max_length=255,
        nullable=True,
        sa_type=VARCHAR(
            length=255,
            collation=None
        ) # pyright: ignore
    )
    id: UUID = Field(
        default_factory=(lambda: uuid7()),
        nullable=False,
        sa_type=Uuid(
            as_uuid=True,
            native_uuid=True
        ) # pyright: ignore
    )
    create_on: datetime = Field(
        default_factory=(lambda: datetime.now(tz=timezone.utc)),
        nullable=False,
        sa_type=TIMESTAMP(timezone=True) # pyright: ignore
    )

    """
    https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/
    """
    role: list["Roles"] = Relationship(
        back_populates="user"
    )
    chatboxes: list["Chatboxes"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        passive_deletes=True
    )
    identities: list["UserIdentities"] = Relationship(
        back_populates="user",
        cascade_delete=True,
        passive_deletes=True
    )
