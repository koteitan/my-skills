#!/usr/bin/env python3
"""Report the 5-hour / weekly rate-limit state and an exhaustion forecast.

Source: ~/.claude/statusline-usage.log, appended by statusline-command.sh from
the server-side rate-limit fields Claude Code pipes into the statusline
(.rate_limits.five_hour / .seven_day). Each row:

    <epoch> <five%> <week%> <five_resets_at> <week_resets_at>   ("-" if absent)

Forecast: slope-extrapolate the samples of the current window (rows sharing the
latest resets_at) to 100%, wall-clock based. Only meaningful when 100% would be
reached before the window resets.
"""

import os
import sys
import time
from datetime import datetime

LOG = os.environ.get(
    "STATUSLINE_USAGE_LOG",
    os.path.expanduser("~/.claude/statusline-usage.log"),
)


def read_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 5:
                continue
            try:
                t = int(parts[0])
            except ValueError:
                continue
            rows.append((t, parts[1], parts[2], parts[3], parts[4]))
    return rows


def fmt(epoch):
    return datetime.fromtimestamp(epoch).strftime("%m/%d %H:%M")


def report(label, rows, pct_col, reset_col, now):
    samples = [r for r in rows if r[pct_col] != "-" and r[reset_col] != "-"]
    if not samples:
        print(f"{label}: no data in {LOG}")
        return

    last = samples[-1]
    pct = float(last[pct_col])
    reset = int(last[reset_col])

    # current window = rows sharing the latest resets_at
    window = [r for r in samples if r[reset_col] == last[reset_col]]
    t0, p0 = window[0][0], float(window[0][pct_col])

    eta = None
    if now > t0:
        slope = (pct - p0) / (now - t0)  # %/sec, wall-clock (idle included)
        if slope > 0:
            e = now + (100 - pct) / slope
            if e < reset:
                eta = e

    line = f"{label}: {pct:3.0f}% used, will reset at {fmt(reset)}"
    if eta is not None:
        line += f", limited at {fmt(eta)} in the current pace"
    else:
        line += ", not projected to hit the limit before the reset"
    print(line)


def main():
    if not os.path.exists(LOG):
        sys.exit(f"no usage log: {LOG}")
    rows = read_rows(LOG)
    if not rows:
        sys.exit(f"usage log is empty: {LOG}")

    now = int(time.time())
    report("5 hours limit", rows, 1, 3, now)
    report("weekly limit ", rows, 2, 4, now)


if __name__ == "__main__":
    main()
