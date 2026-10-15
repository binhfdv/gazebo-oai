#!/bin/sh
# O-RU-side capture script — run this AS ROOT ON THE O-RU ITSELF
# (e.g. ssh root@10.10.0.109 for the Benetel RAN550 "_c0" unit)
#
# Written in POSIX sh (not bash) since the O-RU runs a minimal embedded Linux.
# Timestamps use plain seconds (no milliseconds) since busybox `date` on the
# O-RU may not support %N — adjust if your build does support it.
#
# Usage:
#   ./ru_capture.sh [duration_seconds]
#
# Example:
#   ./ru_capture.sh 60
#
# Collects, for the duration of the run:
#   - kpi.sh          -> fronthaul timing/health counters (RX_TOTAL, ON_TIME,
#                         EARLY, LATE, CORRUPT, TX_TOTAL) - streams continuously
#                         once started, so it's launched once and killed at the end
#   - RXMeanPower/TXMeanPower -> RSSI / TX power per antenna, every 5s
#   - sync-state      -> PTP lock status, every 5s (should stay "0" = locked)
#   - oru_dpd_stats   -> DPD/EVM per TX chain, every 15s (heavier command)

DURATION="${1:-60}"
RUN=$(date -u +%Y%m%d_%H%M%S)
OUTDIR="/tmp/capture_ru_${RUN}"
mkdir -p "$OUTDIR"

ts() { date -u '+%F %T UTC'; }

echo "START_TEST $(ts)" > "$OUTDIR/events.log"

# --- kpi.sh streams on its own once started; just capture it and kill after DURATION ---
kpi.sh > "$OUTDIR/kpi.log" 2>&1 &
KPI_PID=$!

# --- RX/TX power every 5s ---
(
  END=$(( $(date +%s) + DURATION ))
  while [ "$(date +%s)" -lt "$END" ]; do
    echo "=== $(ts) ==="
    RXMeanPower
    TXMeanPower
    sleep 5
  done
) > "$OUTDIR/power.log" 2>&1 &
POWER_PID=$!

# --- PTP sync state every 5s ---
(
  END=$(( $(date +%s) + DURATION ))
  while [ "$(date +%s)" -lt "$END" ]; do
    echo "$(ts) sync-state=$(cat /var/syncmon/sync-state)"
    sleep 5
  done
) > "$OUTDIR/sync_state.log" 2>&1 &
SYNC_PID=$!

# --- DPD/EVM stats every 15s (heavier command) ---
(
  END=$(( $(date +%s) + DURATION ))
  while [ "$(date +%s)" -lt "$END" ]; do
    echo "=== $(ts) ==="
    oru_dpd_stats
    sleep 15
  done
) > "$OUTDIR/dpd_stats.log" 2>&1 &
DPD_PID=$!

sleep "$DURATION"

kill "$KPI_PID" "$POWER_PID" "$SYNC_PID" "$DPD_PID" 2>/dev/null

echo "END_TEST $(ts)" >> "$OUTDIR/events.log"
echo ""
echo "Capture saved in: $OUTDIR"
ls -la "$OUTDIR"
