#!/usr/bin/env python3
"""
Parse FlexRIC KPM xApp (xapp_kpm_moni) console output into CSV.

Expects a log captured like:

    XAPP_DURATION=20000 ./build/examples/xApp/c/monitor/xapp_kpm_moni \
        2>&1 | tee ~/xapp_run_$(date -u +%Y%m%d_%H%M%S).log

Usage:
    python3 parse_xapp_log.py <input_log> <output_csv>
"""

import argparse
import csv
import re
import sys

# NOTE: the tool itself labels this field "latency", but the value is
# actually a raw epoch microsecond timestamp (confirmed by decoding it),
# not a real latency measurement. Named honestly here instead.
SAMPLE_RE = re.compile(r'^\s*(\d+)\s+KPM ind_msg latency\s*=\s*(\d+)\s*\[')
UE_HEADER_RE = re.compile(r'^UE ID type\s*=\s*(\S+?),\s*amf_ue_ngap_id\s*=\s*(\d+)')
RAN_UE_ID_RE = re.compile(r'^ran_ue_id\s*=\s*(\d+)')
METRIC_RE = re.compile(r'^([\w.]+)\s*=\s*([-\d.]+)\s*\[')

METRIC_FIELDS = [
    "DRB.PdcpSduVolumeDL",
    "DRB.PdcpSduVolumeUL",
    "DRB.RlcSduDelayDl",
    "DRB.UEThpDl",
    "DRB.UEThpUl",
    "RRU.PrbTotDl",
    "RRU.PrbTotUl",
]

CSV_FIELDS = [
    "sample_index",
    "ind_msg_timestamp_us",
    "ue_id_type",
    "amf_ue_ngap_id",
    "ran_ue_id",
] + METRIC_FIELDS


def parse_log(path):
    records = []
    sample_index = None
    ind_ts = None
    current = None

    def flush():
        nonlocal current
        if current is not None:
            if all(current[field] != "" for field in METRIC_FIELDS):
                records.append(current)
            # else: incomplete record (e.g. process was killed mid-block
            # before all metric lines were printed) - dropped silently.
            current = None

    with open(path, "r", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()

            m = SAMPLE_RE.match(line)
            if m:
                flush()
                sample_index = int(m.group(1))
                ind_ts = int(m.group(2))
                continue

            m = UE_HEADER_RE.match(line)
            if m:
                flush()
                current = {field: "" for field in CSV_FIELDS}
                current["sample_index"] = sample_index
                current["ind_msg_timestamp_us"] = ind_ts
                current["ue_id_type"] = m.group(1)
                current["amf_ue_ngap_id"] = m.group(2)
                continue

            if current is None:
                # Not inside a UE record yet (still in the startup/setup
                # banner at the top of the log) - skip.
                continue

            m = RAN_UE_ID_RE.match(line)
            if m:
                current["ran_ue_id"] = m.group(1)
                continue

            m = METRIC_RE.match(line)
            if m and m.group(1) in METRIC_FIELDS:
                current[m.group(1)] = m.group(2)
                continue

            if line == "":
                flush()
                continue

    flush()
    return records


def main():
    ap = argparse.ArgumentParser(description="Parse xapp_kpm_moni log output into CSV")
    ap.add_argument("input_log", help="Path to the xApp log file (captured via tee)")
    ap.add_argument("output_csv", help="Path to write the CSV to")
    args = ap.parse_args()

    records = parse_log(args.input_log)
    if not records:
        print(f"[WARN] No KPM records found in {args.input_log}", file=sys.stderr)

    with open(args.output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"[OK] Wrote {len(records)} records -> {args.output_csv}")


if __name__ == "__main__":
    main()
