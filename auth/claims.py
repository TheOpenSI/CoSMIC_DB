"""The single Cosmic claim shape produced from an IdP login."""

### Core modules ###
from dataclasses import (
    dataclass,
    field
)


### Type hints ###
from typing import Any


### Internal modules ###


@dataclass
class NormalisedClaims:
    provider:   str
    sub:        str
    email:      str | None  = None
    name:       str | None  = None
    roles:      list[str]   = field(default_factory=list[str])


def keycloak_user_info_to_claims(user_info: dict[str, Any]) -> NormalisedClaims:
    """
    Map Keycloak's OIDC user info onto :class:`NormalisedClaims`.

    Roles are read from Keycloak's `realm_access.roles` claim. Google & Microsoft
    logins arrive through Keycloak identity brokering, so they are normalised here
    exactly like a native Keycloak login.
    """
    realm_access: dict[str, Any] = user_info.get("realm_access") or {}
    roles: list[str] = (
        list(realm_access.get("roles") or [])
        if   (realm_access)
        else ([])
    )

    return NormalisedClaims(
        provider="keycloak",
        sub=user_info.get(
            "sub",
            ""
        ),
        email=user_info.get(
            "email",
            None
        ),
        name=(
            user_info.get(
                "name",
                None
            )
            or
            user_info.get(
                "preferred_username",
                None
            )
            or
            user_info.get(
                "email",
                None
            )
        ),
        roles=roles
    )
