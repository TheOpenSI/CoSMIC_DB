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

Write-Host "==> Setup complete!"
Write-Host "IMPORTANT:"
Write-Host " 1. Review all generated files and update credentials/configurations as needed."
Write-Host " 2. Remove insecure default values before running the system."
