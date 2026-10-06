#!/usr/bin/env bash
# One-time preparation of a fresh Ubuntu Lightsail instance.
# Run from your laptop (repo root):   ssh ubuntu@<static-ip> 'bash -s' < devops/scripts/setup-lightsail.sh
set -euo pipefail

APP_DIR=/opt/movie-trailer-maker

echo "==> Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"
sudo apt-get install -y -qq rsync >/dev/null

# Small instances run out of memory while pulling images / handling uploads.
if [ "$(swapon --show --noheadings | wc -l)" -eq 0 ]; then
  echo "==> Adding 2 GB swap"
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> Creating $APP_DIR"
sudo mkdir -p "$APP_DIR/devops" "$APP_DIR/site"
sudo chown -R "$USER":"$USER" "$APP_DIR"

echo
echo "Done. Log out and back in once so the docker group applies, then continue with devops/README.md step 4."