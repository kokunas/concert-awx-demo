#!/usr/bin/env bash
#
# simulate_disk_full.sh - Simulate a "disk full" monitoring alert and trigger the
# Concert Workflows flow that archives a file to S3 (via AWX) to free space.
#
# Runs ON THE BASTION. It triggers the flow through the Concert Workflows MCP
# (`trigger_flow`) over the solis-gw tunnel with header auth - the path that
# bypasses the external SSO edge (see MCP_SETUP.md). The trigger is async: the
# flow then drives AWX (launch -> poll -> stdout) on its own.
#
# Prerequisites on the bastion:
#   - the solis-gw tunnel is up, e.g. in a tmux session 'mcp':
#       oc -n concert-workflows port-forward svc/solis-gw 8443:443
#   - CONCERT_PASSWORD set in the environment (otherwise you are prompted)
#
# Usage:
#   CONCERT_PASSWORD=... ./simulate_disk_full.sh [host] [mount] [usage_pct]
#   e.g.  ./simulate_disk_full.sh web-prod-01 /var/log 96
#
set -euo pipefail

CONCERT_USER="${CONCERT_USER:-concertuser}"
SOLIS_HOST="solis-gw.concert-workflows.svc.cluster.local"
MCP_LOCAL="https://localhost:8443/workflows/mcp"   # the port-forward endpoint
FLOW_FOLDER="/User/"
FLOW_NAME="Disk_Full_Archive_To_S3"

# --- simulated disk-full alert ---
ALARM_HOST="${1:-web-prod-01}"
ALARM_MOUNT="${2:-/var/log}"
ALARM_USAGE="${3:-96}"
ALARM_ID="DISK-$(date +%Y%m%d-%H%M%S)"

# --- credentials (never embedded / committed) ---
if [[ -z "${CONCERT_PASSWORD:-}" ]]; then
  read -rsp "Concert password for ${CONCERT_USER}: " CONCERT_PASSWORD
  echo
fi

HDR=(-H "Host: ${SOLIS_HOST}"
     -H "Content-Type: application/json"
     -H "Accept: application/json, text/event-stream"
     -H "X-Concert-Username: ${CONCERT_USER}"
     -H "X-Concert-Password: ${CONCERT_PASSWORD}")

echo "==> Checking the MCP tunnel (initialize)…"
init=$(curl -sk -m 10 -X POST "${MCP_LOCAL}" "${HDR[@]}" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"disk-sim","version":"1"}}}' || true)
if ! grep -q '"serverInfo"' <<<"$init"; then
  echo "!! MCP not reachable. Is the tmux 'mcp' tunnel up?"
  echo "   oc -n concert-workflows port-forward svc/solis-gw 8443:443"
  exit 1
fi
echo "    OK"

echo
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  DISK FULL ALERT (simulated)                 │"
echo "  │  host  : ${ALARM_HOST}"
echo "  │  mount : ${ALARM_MOUNT}"
echo "  │  usage : ${ALARM_USAGE}%"
echo "  │  id    : ${ALARM_ID}"
echo "  └─────────────────────────────────────────────┘"
echo
echo "==> Triggering Concert flow '${FLOW_NAME}' (async)…"

BODY=$(printf '{"alarm_host":"%s","alarm_mount":"%s","alarm_usage_pct":%s,"alarm_id":"%s"}' \
  "$ALARM_HOST" "$ALARM_MOUNT" "$ALARM_USAGE" "$ALARM_ID")

REQ=$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"trigger_flow","arguments":{"folder":"%s","name":"%s","body":%s}}}' \
  "$FLOW_FOLDER" "$FLOW_NAME" "$BODY")

resp=$(curl -sk -m 20 -X POST "${MCP_LOCAL}" "${HDR[@]}" -d "$REQ")
echo "Trigger response:"
python3 -m json.tool <<<"$resp" 2>/dev/null || echo "$resp"

echo
echo "==> Done. The flow now drives AWX (launch -> poll -> read stdout)."
echo "    Watch it in Concert (Logs/Executions), or ask Bob:"
echo "      \"muéstrame la última ejecución de ${FLOW_NAME}\""
