#!/usr/bin/env bash
# Copies the deployment files and the static frontend to the server.
# Used by you for the first upload and by the GitHub Action on every deploy.
#   usage: bash devops/scripts/push-to-server.sh ubuntu@<host> [remote_dir]
# Never touches the server's devops/.env or devops/backend.env.
set -euo pipefail

TARGET="${1:?usage: push-to-server.sh user@host [remote_dir]}"
REMOTE_DIR="${2:-/opt/movie-trailer-maker}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Only the files the browser needs - not the frontend's README, lint config, etc.
mkdir -p "$STAGE/site"
cp -r "$ROOT/frontend/index.html" "$ROOT/frontend/css" "$ROOT/frontend/js" "$ROOT/frontend/assets" "$STAGE/site/"

rsync -az --delete --exclude '.env' --exclude 'backend.env' "$ROOT/devops/" "$TARGET:$REMOTE_DIR/devops/"
rsync -az --delete "$STAGE/site/" "$TARGET:$REMOTE_DIR/site/"
echo "Uploaded devops/ and site/ to $TARGET:$REMOTE_DIR"