"""
RSA key material for the Cosmic session JWT (RS256).


The private key stays local to the Auth BFF. The public half is published at
``{AUTH_API_PREFIX}/jwks.json`` so the other CoSMIC microservices can verify a
session cookie without sharing a symmetric secret.
"""


### Core modules ###
from functools import lru_cache
from pathlib import Path
from joserfc.jwk import RSAKey


### Type hints ###


### Internal modules ###
from . import config


class SessionKeyError(RuntimeError):
    """Raised when the RS256 session keypair cannot be loaded."""


def _load_pem(
    path: Path,
    label: str
) -> str:
    pem_path: Path = Path(path)

    if not pem_path.is_file():
        raise SessionKeyError(
            f"Missing {label} RSA key at '{pem_path}'. Run `bins/gen_session_keys.ps1` (Windows) or `bins/gen_session_keys.sh` (Linux/macOS) to generate the keypair."
        )

    return pem_path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def private_key() -> RSAKey:
    key: RSAKey = RSAKey.import_key(
        value=_load_pem(
            path=config.SESSION_PRIVATE_KEY_PATH,
            label="private"
        )
    )

    # `ensure_kid` uses the RFC 7638 thumbprint, so the key id is stable across
    # restarts and identical for the public and private half of the keypair.
    key.ensure_kid()

    return key


@lru_cache(maxsize=1)
def public_key() -> RSAKey:
    public_path: Path = Path(config.SESSION_PUBLIC_KEY_PATH)

    if public_path.is_file():
        key: RSAKey = RSAKey.import_key(
            value=_load_pem(
                path=public_path,
                label="public"
            )
        )

    else:
        # Derive the public half when only the private PEM was provisioned.
        key: RSAKey = RSAKey.import_key(value=private_key().as_pem(private=False))

    key.ensure_kid()

    return key


def key_id() -> str:
    return (
        config.SESSION_KEY_ID
        or
        public_key().kid
    )


def jwk_set() -> dict[str, list[dict[str, str | list[str]]]]:
    """Public JWKS document consumed by the other microservices."""
    data: dict[str, str | list[str]] = dict(public_key().as_dict(private=False))
    data.update(
        {
            "kid": key_id(),
            "alg": "RS256",
            "use": "sig"
        }
    )

    return {"keys": [data]}
