# Deploying to AWS Lightsail (livetestingserver.com)

What runs on the server (Docker Compose, `devops/docker-compose.yml`):

| Container | Job |
|---|---|
| `nginx` | HTTPS on 80/443, serves the frontend, proxies `/api/` and `/health` to the backend |
| `backend` | FastAPI app (image `theashishdwivedi/movie_trailer_maker` from Docker Hub) |
| `certbot` | Renews the Let's Encrypt certificate automatically |

Only `/api/*` and `/health` reach the backend. Its older `/trailers` route (which takes server file paths) and `/docs` are not exposed.

## One-time setup

**1. Lightsail instance.** Create an Ubuntu 24.04 instance, at least **2 GB RAM** and 40 GB+ disk (uploaded videos are stored on it). Attach a **static IP**. Under *Networking → IPv4 Firewall* allow **22, 80 and 443**.

**2. DNS.** Add an `A` record: `livetestingserver.com` → the static IP. Wait until `nslookup livetestingserver.com` returns it (the certificate step fails otherwise).

**3. Prepare the server** (from the repo root on your laptop; installs Docker, adds swap, creates `/opt/movie-trailer-maker`):

```bash
ssh ubuntu@<static-ip> 'bash -s' < devops/scripts/setup-lightsail.sh
```

Log out and back in once so the `docker` group takes effect.

**4. Upload the files and create the two settings files.**

```bash
bash devops/scripts/push-to-server.sh ubuntu@<static-ip>
ssh ubuntu@<static-ip>
cd /opt/movie-trailer-maker/devops
cp .env.example .env                  # set LETSENCRYPT_EMAIL
cp backend.env.example backend.env    # set ANTHROPIC_API_KEY, MODEL_PRIMARY, MODEL_FALLBACK
```

**5. Get the backend image onto Docker Hub** (the server pulls it). Either push the repo to GitHub with the secrets below set (CI builds and pushes it; its first deploy step may fail because the server is not ready yet - that is fine), or from your laptop:

```bash
docker build -t theashishdwivedi/movie_trailer_maker:latest backend
docker push theashishdwivedi/movie_trailer_maker:latest
```

**6. First HTTPS certificate** (on the server, in `devops/`):

```bash
bash scripts/init-letsencrypt.sh
```

Open https://livetestingserver.com. (`STAGING=1 bash scripts/init-letsencrypt.sh` does a dry run if you are debugging DNS; Let's Encrypt limits repeated real attempts.)

## GitHub Actions secrets (Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | your Docker Hub username |
| `DOCKERHUB_TOKEN` | a Docker Hub access token (Account settings → Security) |
| `LIGHTSAIL_HOST` | the static IP (or `livetestingserver.com`) |
| `LIGHTSAIL_USER` | `ubuntu` |
| `LIGHTSAIL_SSH_KEY` | private key of a deploy key: `ssh-keygen -t ed25519 -f deploy_key`, append `deploy_key.pub` to `~/.ssh/authorized_keys` on the server, paste the **private** file here |

These replace the old `EC2_*` secrets. From then on every push to `main`: runs tests and lint → builds and pushes the image → uploads `devops/` and the frontend → pulls the image, reloads nginx → checks `https://livetestingserver.com/health`. Pull requests only run tests and lint.

## Everyday operations (on the server, in `/opt/movie-trailer-maker/devops`)

```bash
docker compose ps                      # status
docker compose logs -f backend         # backend logs (also: nginx, certbot)
bash scripts/deploy.sh                 # pull latest image and apply changes by hand
docker compose restart backend         # after editing backend.env
```

- **Roll back:** set `IMAGE_TAG=<commit sha>` in `.env`, then `docker compose up -d`. Every build is also tagged with its commit SHA on Docker Hub.
- **Disk:** every request keeps its uploads under the `runs` volume. Delete old ones, e.g. weekly via `crontab -e`:
  `0 3 * * 0 docker exec movie-trailer-maker-backend-1 find /data/runs -mindepth 1 -maxdepth 1 -mtime +7 -exec rm -rf {} +`
- **Certificate:** renews itself. If a renewal ever needs forcing: `docker compose run --rm certbot renew --force-renewal && bash scripts/deploy.sh`.

## Limits to know about

- The site has **no login**. nginx limits `/api/generate-trailer` to 6 requests/minute per IP, but anyone who finds the URL can use it - and once the real model call exists, that spends your Anthropic budget. Add authentication (e.g. nginx basic auth) before sharing the link.
- Requests are synchronous; a long run holds the connection open (nginx allows up to 15 minutes).
- nginx accepts up to 1 GB per request; the backend limits each file to `MAX_UPLOAD_MB` (default 500).