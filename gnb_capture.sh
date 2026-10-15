#!/bin/bash
# gNB-side capture script — run this ON PEAFOWL, in a SEPARATE terminal/session
# from the one running nr-softmodem.
#
# IMPORTANT: This script does NOT start or stop nr-softmodem. Restarting it
# means re-running the SR-IOV VF setup again, which is disruptive to a live
# radio link. Instead, this script assumes nr-softmodem is already running
# with its stdout captured to a log file, e.g.:
#
#   sudo LD_LIBRARY_PATH=.:$DPDK_INST/lib/x86_64-linux-gnu/ \
#     ./ran_build/build/nr-softmodem -O /etc/ran_development/CONFs/gnb.sa.band77.273prb.fhi72.4x4-benetel550_c0.conf \
#     --thread-pool 11,12,13,14,15,16,17,18 \
#     2>&1 | tee ~/gnb_run.log
#
# This script's job is just to (a) mark a UTC-timestamped test window you can
# grep out of that log afterward, and (b) best-effort poll a telnet debug
# interface on port 9090 if one happens to be listening — this is UNVERIFIED
# in this session, not documented anywhere in the tutorials repo. If it's not
# there, this step is skipped automatically and costs you nothing.
#
# Usage:
#   ./gnb_capture.sh [duration_seconds] [telnet_port]
#
# Example:
#   ./gnb_capture.sh 60

DURATION="${1:-60}"
TELNET_PORT="${2:-9090}"

RUN=$(date -u +%Y%m%d_%H%M%S)
OUTDIR="$HOME/capture_gnb_${RUN}"
mkdir -p "$OUTDIR"

ts() { date -u '+%F %T.%3N UTC'; }

{
  echo "START_TEST $(ts)"
  echo "NOTE: correlate this window against your nr-softmodem stdout log manually."
} | tee "$OUTDIR/events.log"

TELNET_PID=""
if command -v nc >/dev/null 2>&1 && nc -z -w1 localhost "$TELNET_PORT" 2>/dev/null; then
  echo "Telnet debug interface detected on port $TELNET_PORT, polling every 5s..." | tee -a "$OUTDIR/events.log"
  (
    END=$(( $(date +%s) + DURATION ))
    while [ "$(date +%s)" -lt "$END" ]; do
      echo "=== $(ts) ==="
      { echo "stats"; sleep 1; } | timeout 2 telnet localhost "$TELNET_PORT" 2>&1
      sleep 4
    done
  ) > "$OUTDIR/telnet_stats.log" 2>&1 &
  TELNET_PID=$!
else
  echo "No telnet interface detected on port $TELNET_PORT (or 'nc' unavailable) - skipping." | tee -a "$OUTDIR/events.log"
fi

sleep "$DURATION"
[ -n "$TELNET_PID" ] && kill "$TELNET_PID" 2>/dev/null

echo "END_TEST $(ts)" | tee -a "$OUTDIR/events.log"
echo ""
echo "Capture saved in: $OUTDIR"
echo "Now extract the matching window from your nr-softmodem log, e.g.:"
echo "  sed -n '/<start-time-pattern>/,/<end-time-pattern>/p' ~/gnb_run.log"
ls -la "$OUTDIR"
