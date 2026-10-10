### Core modules ###
from datetime import (
    datetime,
    timezone
)
from uuid import uuid7
from fastapi import (
    HTTPException,
    status
)
from sqlmodel import select


### Type hints ###


### Internal modules ###
from .claims import NormalisedClaims
from .models import (
    Roles,
    UserIdentities,
    Users
)
from app.cores.db import SessionDependency


def ensure_user(
    session:    SessionDependency,
    claims:     NormalisedClaims
) -> Users:
    if not claims.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Login requires a stable subject (sub)."
            }
        )

    identity: UserIdentities | None = session.exec(
        statement=select(UserIdentities).where(
            UserIdentities.provider == claims.provider,
            UserIdentities.sub == claims.sub
        )
    ).first()

    if identity:
        user: Users | None = session.get(
            entity=Users,
            ident=identity.user_id
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "500 - Internal Server Error",
                    "message": "Identity points at missing user."
                }
            )

        return user

    if not claims.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Login requires an email claim from the IdP."
            }
        )

    email: str = claims.email.strip().lower()

    user: Users | None = session.exec(
        statement=select(Users).where(
            Users.email.ilike(email)
        )
    ).first()

    if not user:
        default_role: Roles | None = session.exec(
            statement=select(Roles).where(
                Roles.name.ilike("user")
            )
        ).first()

        if default_role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "500 - Internal Server Error",
                    "message": "Default 'user' role not found."
                }
            )

        user = Users(
            id=uuid7(),
            role_id=default_role.id,
            name=(
                claims.name
                or
                email
            ),
            email=email,
            create_on=datetime.now(tz=timezone.utc)
        )

        session.add(user)
        session.flush()

    session.add(
        instance=UserIdentities(
            id=uuid7(),
            user_id=user.id,
            provider=claims.provider,
            sub=claims.sub,
            created_on=datetime.now(tz=timezone.utc)
        )
    )

    session.commit()
    session.refresh(user)

    return user
