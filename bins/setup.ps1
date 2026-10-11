# Similar concept to the shebang defined in Bash script version
#Requires -Version 7.0

# Similar concept to the `set -e` flag in Bash script version
$ErrorActionPreference = "Stop"


# Navigate to project root (one level up from 'bins/')
$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot
Set-Location $projectRoot

Write-Host "==> Creating required directories..."

New-Item -ItemType Directory -Force -Path "docker\secrets" | Out-Null
New-Item -ItemType Directory -Force -Path "docker\configs" | Out-Null
New-Item -ItemType Directory -Force -Path "cores" | Out-Null
New-Item -ItemType Directory -Force -Path "auth" | Out-Null

Write-Host "==> Checking and preparing environment/configuration files..."

# Helper function to conditionally copy files safely
function Invoke-SafeCopy {
    param(
		$Source,
		$Destination
	)

    if (Test-Path $Destination) {
        Write-Host "Skipped: [$Destination] already exists (left untouched)."
    } else {
        Copy-Item -Path $Source -Destination $Destination
        Write-Host "Copied: [$Source] -> [$Destination]"
    }
}

# Backend service (.env)
foreach ($file in (Get-ChildItem -Path "examples" -Filter "cosmic_cfg*.example.env" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "cores\$newName"
}

# Auth (.env) → auth/
foreach ($file in (Get-ChildItem -Path "examples" -Filter "cosmic_auth.example.env" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "auth\$newName"
}

# PostgreSQL (.txt)
foreach ($file in (Get-ChildItem -Path "examples" -Filter "postgres_*.example.txt" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "docker\secrets\$newName"
}

# pgAdmin secrets (.txt)
foreach ($file in (Get-ChildItem -Path "examples" -Filter "pgadmin_*.example.txt" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "docker\secrets\$newName"
}

# pgAdmin configs (.json)
foreach ($file in (Get-ChildItem -Path "examples" -Filter "pgadmin_*.example.json" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "docker\configs\$newName"
}

# Keycloak secrets (.txt)
foreach ($file in (Get-ChildItem -Path "examples" -Filter "keycloak_*.example.txt" -ErrorAction SilentlyContinue))
{
    $newName = $file.Name -replace "\.example", ""
    Invoke-SafeCopy -Source $file.FullName -Destination "docker\secrets\$newName"
}

# Generates the RS256 key-pair used to sign the CoSMIC session cookie
$secretsDir = Join-Path $projectRoot "docker\secrets"
$privateKey = Join-Path $secretsDir "cosmic_private_session.pem"
$publicKey = Join-Path $secretsDir "cosmic_public_session.pem"

if ((Test-Path $privateKey) -and (Test-Path $publicKey))
{
    Write-Host "==> Skipped: session key-pair already exists at [$secretsDir] (left untouched)."
}
else
{
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
    Write-Host " 1. [$privateKey]"
    Write-Host " 2. [$publicKey]"
    Write-Host "NOTE: Never commit these files. Rotating the keypair invalidates all active sessions."
}

Write-Host "==> Setup complete!"
Write-Host "IMPORTANT:"
Write-Host " 1. Review all generated files and update credentials/configurations as needed."
Write-Host " 2. Remove insecure default values before running the system."
