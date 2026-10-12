#!/usr/bin/env bash

set -euo pipefail


# Navigate to project root (one level up from 'bins/')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "==> Creating required directories..."

mkdir -p docker/secrets
mkdir -p docker/configs
mkdir -p cores

echo "==> Checking and preparing environment/configuration files..."

# Helper function to conditionally copy files safely
safe_copy() {
    local src="$1"
    local dest="$2"

    if [ -f "$dest" ]; then
        echo "Skipped: [$dest] already exists (left untouched)."
    else
        cp "$src" "$dest"
        echo "Copied: [$src] -> [$dest]"
    fi
}

# Backend service (.env)
for file in examples/cosmic_cfg*.example.env; do
    [ -f "$file" ] || continue
    new_name=$(basename "$file" | sed 's/\.example//')
    safe_copy "$file" "cores/$new_name"
done

# PostgreSQL (.txt)
for file in examples/postgres_*.example.txt; do
    [ -f "$file" ] || continue
    new_name=$(basename "$file" | sed 's/\.example//')
    safe_copy "$file" "docker/secrets/$new_name"
done

# pgAdmin secrets (.txt)
for file in examples/pgadmin_*.example.txt; do
    [ -f "$file" ] || continue
    new_name=$(basename "$file" | sed 's/\.example//')
    safe_copy "$file" "docker/secrets/$new_name"
done

# pgAdmin configs (.json)
for file in examples/pgadmin_*.example.json; do
    [ -f "$file" ] || continue
    new_name=$(basename "$file" | sed 's/\.example//')
    safe_copy "$file" "docker/configs/$new_name"
done

echo "==> Setup complete!"
echo "IMPORTANT:"
echo " 1. Review all generated files and update credentials/configurations as needed."
echo " 2. Remove insecure default values before running the system."
