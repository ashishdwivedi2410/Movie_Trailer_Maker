#!/usr/bin/env bash
# Run ON THE SERVER once, after devops/.env and devops/backend.env exist and the
# domain's DNS already points at this server. Gets the first HTTPS certificate.
#   bash scripts/init-letsencrypt.sh            real certificate
#   STAGING=1 bash scripts/init-letsencrypt.sh  test run (untrusted cert, no rate limits)
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Missing devops/.env (copy .env.example)"; exit 1; }
[ -f backend.env ] || { echo "Missing devops/backend.env (copy backend.env.example)"; exit 1; }
set -a
# shellcheck source=/dev/null
. ./.env
set +a
: "${DOMAIN:?DOMAIN not set in .env}"
: "${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL not set in .env}"

LIVE="/etc/letsencrypt/live/$DOMAIN"

echo "==> Creating a temporary self-signed certificate so nginx can start"
docker compose run --rm --entrypoint sh certbot -c "
  mkdir -p $LIVE &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem -subj '/CN=localhost'"

echo "==> Pulling the backend image and starting backend + nginx"
docker compose pull backend || {
  echo "Could not pull the backend image from Docker Hub."
  echo "Push it first (CI does this on every push to main) - see devops/README.md step 5."
  exit 1
}
docker compose up -d backend nginx

echo "==> Removing the temporary certificate"
docker compose run --rm --entrypoint sh certbot -c "
  rm -rf /etc/letsencrypt/live/$DOMAIN /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf"

STAGING_FLAG=""
[ "${STAGING:-0}" = "1" ] && STAGING_FLAG="--staging"

echo "==> Requesting the real certificate for $DOMAIN"
# shellcheck disable=SC2086
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email \
  --non-interactive $STAGING_FLAG

docker compose exec -T nginx nginx -s reload
docker compose up -d certbot
echo "Done: https://$DOMAIN"