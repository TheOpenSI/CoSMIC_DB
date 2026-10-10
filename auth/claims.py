"""The single Cosmic claim shape produced from an IdP login."""

from dataclasses import dataclass, field


@dataclass
class NormalizedClaims:
    provider: str
    sub: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = field(default_factory=list)


def keycloak_userinfo_to_claims(userinfo: dict) -> NormalizedClaims:
    """Map Keycloak's OIDC userinfo onto :class:`NormalizedClaims`.

    Roles are read from Keycloak's `realm_access.roles` claim. Google and
    Microsoft logins arrive through Keycloak identity brokering, so they are
    normalised here exactly like a native Keycloak login.
    """
    realm_access = userinfo.get("realm_access") or {}
    roles = list(realm_access.get("roles") or []) if isinstance(realm_access, dict) else []

    return NormalizedClaims(
        provider="keycloak",
        sub=str(userinfo.get("sub") or ""),
        email=userinfo.get("email"),
        name=(
            userinfo.get("name")
            or userinfo.get("preferred_username")
            or userinfo.get("email")
        ),
        roles=roles,
    )
