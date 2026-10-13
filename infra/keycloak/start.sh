#!/usr/bin/env bash
# Starts Keycloak in DEVELOPMENT mode. Not suitable for production.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set -a
source "$ROOT/.env"
set +a

: "${KEYCLOAK_HOME:?Set KEYCLOAK_HOME in .env}"

# Keycloak reads these environment variables, so no password appears on the command line
export KC_BOOTSTRAP_ADMIN_USERNAME="$KEYCLOAK_ADMIN_USER"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD"
export KC_DB_PASSWORD="$KEYCLOAK_DB_PASSWORD"

exec "$KEYCLOAK_HOME/bin/kc.sh" start-dev \
  --http-port=8080 \
  --db=postgres \
  --db-url="jdbc:postgresql://localhost:5432/keycloak" \
  --db-username="keycloak_user"