# Similar concept to the shebang defined in the Bash script version
#Requires -Version 7.0

# Similar concept to the `set -e` flag in Bash script version
$ErrorActionPreference = "Stop"

# Generates the RS256 keypair used to sign the Cosmic session cookie.
# Idempotent: an existing keypair is left untouched so running setup again does
# not invalidate every active session.
$secretsDir = Join-Path $PSScriptRoot "..\auth\secrets"
$privateKey = Join-Path $secretsDir "session_private.pem"
$publicKey = Join-Path $secretsDir "session_public.pem"

New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null

if ((Test-Path $privateKey) -and (Test-Path $publicKey))
{
    Write-Host "==> Session keypair already exists at '$secretsDir' (left untouched)."
    exit 0
}

Write-Host "==> Generating RSA-2048 session keypair..."
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
try
{
    [System.IO.File]::WriteAllText($privateKey, $rsa.ExportPkcs8PrivateKeyPem())
    [System.IO.File]::WriteAllText($publicKey, $rsa.ExportSubjectPublicKeyInfoPem())
}
finally
{
    $rsa.Dispose()
}

Write-Host "Generated:"
Write-Host " - $privateKey"
Write-Host " - $publicKey"
Write-Host "NOTE: Never commit these files. Rotating the keypair invalidates all active sessions."
