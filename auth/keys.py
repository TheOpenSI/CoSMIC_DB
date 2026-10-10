"""
RSA key material for CoSMIC JWT session token using RS256 encryption algorithm.


The private key stays local to the Auth BFF while the public one is published at
``{AUTH_API_PREFIX}/jwks.json``. This way, other CoSMIC micro-services can verify
a session cookie without sharing a symmetric secret.
"""


### Core modules ###
from functools import lru_cache
from pathlib import Path
from joserfc.jwk import RSAKey


### Type hints ###


### Internal modules ###
from .config import (
    SESSION_KEY_ID,
    SESSION_PRIVATE_KEY_PATH,
    SESSION_PUBLIC_KEY_PATH
)


class SessionKeyError(RuntimeError):
    """Raised when the RS256 session key-pair (PEM file) cannot be loaded."""


def _load_pem(
    path:   Path,
    label:  str
) -> str:
    pem_path: Path = Path(path)

    if not pem_path.is_file():
        raise SessionKeyError(
            f"Missing {label} RSA key at '{pem_path}'. Have you tried running `bins\\Setup.ps1` (Windows) or `bins/setup.sh` (Linux/macOS)?"
        )

    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def private_key() -> RSAKey:
    private_path: Path = Path(str(SESSION_PRIVATE_KEY_PATH))

    key: RSAKey = RSAKey.import_key(
        value=_load_pem(
            path=private_path,
            label="private"
        )
    )

    # `ensure_kid` uses the RFC 7638 thumbprint so that the key ID is stable
    # across restarts and identical for the public and private half of the
    # keypair.
    key.ensure_kid()

    return key


@lru_cache(maxsize=1)
def public_key() -> RSAKey:
    public_path: Path = Path(str(SESSION_PUBLIC_KEY_PATH))

    if public_path.is_file():
        key: RSAKey = RSAKey.import_key(
            value=_load_pem(
                path=public_path,
                label="public"
            )
        )

    else:
        # Derive the public half when only the private PEM was provisioned.
        key = RSAKey.import_key(value=private_key().as_pem(private=False))

    key.ensure_kid()

    return key


def key_id() -> str:
    current_key_id:     str = str(SESSION_KEY_ID)
    fallback_key_id:    str = str(public_key().kid)

    return (
        current_key_id
        or
        fallback_key_id
    )


def jwk_set() -> dict[str, list[dict[str, str | list[str]]]]:
    """Public JWKS document consumed by the other micro-services"""
    data: dict[str, str | list[str]] = dict(public_key().as_dict(private=False))
    data.update(
        {
            "kid": key_id(),
            "alg": "RS256",
            "use": "sig"
        }
    )

    return {"keys": [data]}
