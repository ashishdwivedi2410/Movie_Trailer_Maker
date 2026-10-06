#!/usr/bin/env bash
# Runs ON THE SERVER (from anywhere): pulls the latest backend image and applies changes.
# The GitHub Action calls this after uploading files; you can also run it by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose pull backend
docker compose up -d --remove-orphans

# Re-render the nginx template and reload it without dropping connections.
# If the new config is invalid, nginx keeps running on the old one.
docker compose exec -T nginx sh -c '/docker-entrypoint.d/20-envsubst-on-templates.sh >/dev/null && nginx -t && nginx -s reload'

docker image prune -f >/dev/null
docker compose ps