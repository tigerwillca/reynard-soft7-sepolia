#!/usr/bin/env bash
# Start the static metadata server that serves the public site over HTTP,
# the way a wallet or marketplace fetches ERC-721 token metadata.
#
# Runs on every environment boot (the `start` phase). It is idempotent: if the
# server is already listening it returns immediately, otherwise it launches the
# server in the background, waits for readiness, and returns.
#
# The server binds to loopback and serves an allowlisted copy of the public
# files. It does not publish the repository root.
set -euo pipefail

PORT="${METADATA_SERVER_PORT:-8000}"
LOG="/tmp/metadata-server.log"
PUBLIC_ROOT="/tmp/metadata-public"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "METADATA_SERVER_PORT must be an integer from 1 to 65535" >&2
  exit 1
fi

if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:${PORT}/"; then
  echo "metadata-server already listening on 127.0.0.1:${PORT}"
  exit 0
fi

bash "$REPO_ROOT/scripts/assemble_public_site.sh" "$PUBLIC_ROOT"

cd "$PUBLIC_ROOT"
nohup python3 -m http.server "$PORT" --bind 127.0.0.1 >"$LOG" 2>&1 &
server_pid=$!

for _ in $(seq 1 40); do
  if curl -sf -o /dev/null --max-time 2 "http://127.0.0.1:${PORT}/"; then
    echo "metadata-server ready on 127.0.0.1:${PORT} (pid ${server_pid}), serving ${PUBLIC_ROOT}"
    exit 0
  fi
  sleep 0.25
done

echo "metadata-server failed to become ready on 127.0.0.1:${PORT}; see ${LOG}" >&2
exit 1
