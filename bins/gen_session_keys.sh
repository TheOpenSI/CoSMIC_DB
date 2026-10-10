#!/usr/bin/env bash
# Similar concept to the `-e` flag used by PowerShell version
set -euo pipefail

# Generates the RS256 keypair used to sign the Cosmic session cookie.
# Idempotent: an existing keypair is left untouched so running setup again does
# not invalidate every active session.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/../auth/secrets"
PRIVATE_KEY="${SECRETS_DIR}/session_private.pem"
PUBLIC_KEY="${SECRETS_DIR}/session_public.pem"

mkdir -p "${SECRETS_DIR}"

if [[ -f "${PRIVATE_KEY}" && -f "${PUBLIC_KEY}" ]]; then
    echo "==> Session keypair already exists at '${SECRETS_DIR}' (left untouched)."
    exit 0
fi

echo "==> Generating RSA-2048 session keypair..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "${PRIVATE_KEY}"
openssl rsa -in "${PRIVATE_KEY}" -pubout -out "${PUBLIC_KEY}"

echo "Generated:"
echo " - ${PRIVATE_KEY}"
echo " - ${PUBLIC_KEY}"
echo "NOTE: Never commit these files. Rotating the keypair invalidates all active sessions."
