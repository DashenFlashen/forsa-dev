#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Building React dashboard..."
cd "$REPO_ROOT/dashboard"
npm install
npm run build

echo "Static files written to src/forsa_dev/dashboard/static/"
echo "Done."
