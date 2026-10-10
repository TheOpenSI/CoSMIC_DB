from datetime import datetime, timezone
from uuid import uuid7

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.apis.table_models.roles import Roles
from app.apis.table_models.user_identities import UserIdentities
from app.apis.table_models.users import Users

from auth.claims import NormalizedClaims


def ensure_user(session: Session, claims: NormalizedClaims) -> Users:
    if not claims.sub:
        raise HTTPException(status_code=400, detail="Login requires a stable subject (sub)")

    identity = session.exec(
        select(UserIdentities).where(
            UserIdentities.provider == claims.provider,
            UserIdentities.sub == claims.sub,
        )
    ).first()
    if identity:
        user = session.get(Users, identity.user_id)
        if user is None:
            raise HTTPException(status_code=500, detail="Identity points at missing user")
        return user

    if not claims.email:
        raise HTTPException(
            status_code=400,
            detail="Login requires an email claim from the identity provider",
        )
    email = claims.email.strip().lower()

    user = session.exec(
        select(Users).where(func.lower(Users.email) == email)
    ).first()

    if not user:
        default_role = session.exec(
            select(Roles).where(Roles.name.ilike("user"))
        ).first()
        if default_role is None:
            raise HTTPException(status_code=500, detail="Default 'user' role not found")

        user = Users(
            id=uuid7(),
            role_id=default_role.id,
            name=claims.name or email,
            email=email,
            create_on=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()

    session.add(
        UserIdentities(
            id=uuid7(),
            user_id=user.id,
            provider=claims.provider,
            sub=claims.sub,
            created_on=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.refresh(user)
    return user