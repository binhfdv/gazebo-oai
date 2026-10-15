#!/bin/bash
# UE-side capture script — run this ON UP1 (up1@up1.sboai.cs.eurecom.fr)
#
# Runs an iperf3 UDP downlink test against the core's Traffic Server while
# sampling interface counters and (best-effort) modem signal quality.
#
# Usage:
#   ./ue_capture.sh [duration_seconds] [server_ip] [rate]
#
# Example:
#   ./ue_capture.sh 60 172.21.6.12 100M
#
# Prerequisite: the UE must already be attached with a working PDU session
# (run start_quectel_mbim.sh first — the "internet" DNN is the one proven
# working in this session; "oai" DNN currently fails with InvalidUserNamePwd).

set -uo pipefail

DURATION="${1:-60}"
SERVER_IP="${2:-172.21.6.12}"
RATE="${3:-100M}"
IFACE="wwan0"

RUN=$(date -u +%Y%m%d_%H%M%S)
OUTDIR="$HOME/capture_ue_${RUN}"
mkdir -p "$OUTDIR"

ts() { date -u '+%F %T.%3N UTC'; }

{
  echo "START_TEST $(ts)"
  echo "server_ip=$SERVER_IP rate=$RATE duration=${DURATION}s iface=$IFACE"
} | tee "$OUTDIR/events.log"

# --- Background: interface byte/packet/error/drop counters, every 5s ---
(
  END=$(( $(date +%s) + DURATION + 5 ))
  while [ "$(date +%s)" -lt "$END" ]; do
    echo "=== $(ts) ==="
    ip -s link show "$IFACE"
    sleep 5
  done
) > "$OUTDIR/iface_counters.log" 2>&1 &
IFACE_PID=$!

# --- Background: modem signal quality, every 5s ---
# NOTE: --query-signal-state is not verified working in this session — best effort.
# If it errors out, signal.log will just show the error; safe to ignore and rely
# on RU-side RXMeanPower instead.
(
  END=$(( $(date +%s) + DURATION + 5 ))
  while [ "$(date +%s)" -lt "$END" ]; do
    echo "=== $(ts) ==="
    sudo mbimcli -p -d /dev/cdc-wdm0 --query-signal-state 2>&1
    sleep 5
  done
) > "$OUTDIR/signal.log" 2>&1 &
SIGNAL_PID=$!

echo "Starting iperf3 UDP downlink test ($RATE, ${DURATION}s)..." | tee -a "$OUTDIR/events.log"
iperf3 --bind-dev "$IFACE" -c "$SERVER_IP" -u -b "$RATE" -l 1427 -O 5 -t "$DURATION" -R \
  2>&1 | tee "$OUTDIR/iperf.log"

kill "$IFACE_PID" "$SIGNAL_PID" 2>/dev/null
wait "$IFACE_PID" "$SIGNAL_PID" 2>/dev/null

echo "END_TEST $(ts)" | tee -a "$OUTDIR/events.log"
echo ""
echo "Capture saved in: $OUTDIR"
ls -la "$OUTDIR"
