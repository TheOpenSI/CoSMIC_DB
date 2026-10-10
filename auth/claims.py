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
    roles:      list[str]   = field(default_factory=list)


def keycloak_userinfo_to_claims(userinfo: dict[str, Any]) -> NormalisedClaims:
    """
    Map Keycloak's OIDC userinfo onto :class:`NormalisedClaims`.

    Roles are read from Keycloak's `realm_access.roles` claim. Google and
    Microsoft logins arrive through Keycloak identity brokering, so they are
    normalised here exactly like a native Keycloak login.
    """
    realm_access: dict[str, Any] = userinfo.get("realm_access") or {}
    roles: list[str] = (
        list(realm_access.get("roles") or [])
        if   (isinstance(realm_access, dict))
        else ([])
    )

    return NormalisedClaims(
        provider="keycloak",
        sub=str(userinfo.get("sub") or ""),
        email=userinfo.get("email"),
        name=(
            userinfo.get("name")
            or
            userinfo.get("preferred_username")
            or
            userinfo.get("email")
        ),
        roles=roles
    )
