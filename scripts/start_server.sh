#!/usr/bin/env bash
# Start the static metadata server that serves meta/*.json and images/* over
# HTTP, the way a wallet or marketplace fetches ERC-721 token metadata.
#
# Runs on every environment boot (the `start` phase). It is idempotent: if the
# server is already listening it returns immediately, otherwise it launches the
# server in the background, waits for readiness, and returns.
set -euo pipefail

PORT="${METADATA_SERVER_PORT:-8000}"
LOG="/tmp/metadata-server.log"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/" 2>/dev/null; then
  echo "metadata-server already listening on :${PORT}"
  exit 0
fi

cd "$REPO_ROOT"
nohup python3 -m http.server "$PORT" --bind 0.0.0.0 >"$LOG" 2>&1 &
server_pid=$!

for _ in $(seq 1 40); do
  if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/"; then
    echo "metadata-server ready on :${PORT} (pid ${server_pid}), serving ${REPO_ROOT}"
    exit 0
  fi
  sleep 0.25
done

echo "metadata-server failed to become ready on :${PORT}; see ${LOG}" >&2
exit 1
