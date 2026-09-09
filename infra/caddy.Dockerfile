# Build context = repo root:  docker build -f infra/caddy.Dockerfile -t comark-caddy .
FROM caddy:2-alpine
COPY infra/Caddyfile /etc/caddy/Caddyfile
