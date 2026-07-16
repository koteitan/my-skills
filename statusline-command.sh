#!/bin/bash
# statusLine command for Claude Code
# Line 1: host:dir
# Line 2: ctx:[bar] 5h:[bar]>ETA w:[bar]>ETA <model> <effort>
#
# Each [bar] is a 10-char gauge:
#   filled cell : fg=dark  color, bg=light color
#   empty  cell : fg=light color, bg=dark  color
#   hue: <80% green, 80..<100% orange, 100% red
#   text "xxx%": <50% written from leftmost empty cell,
#                >=50% written ending at rightmost filled cell
#   absent rate_limits -> gray empty bar, no text
#
# ETA (exhaustion forecast, wall-clock based):
#   Samples are appended to $USAGE_LOG. Within one window (identified by its
#   resets_at), slope = (pct_now - pct_first) / (t_now - t_first) in %/sec,
#   measured against wall-clock time (idle time included, by design).
#   ETA = now + (100 - pct_now) / slope.
#   Shown only when the window would hit 100% BEFORE it resets — otherwise the
#   reset wins and there is nothing to warn about. Needs pct to have moved at
#   least 1 step since the first sample of the window (source resolution is 1%),
#   so early in a window there is no ETA -- which is also when plenty remains.

USAGE_LOG=${STATUSLINE_USAGE_LOG:-/home/koteitan/.claude/statusline-usage.log}

input=$(cat)
now=$(date +%s)

host=$(hostname -s)
dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
[ -z "$dir" ] && dir=$(pwd)

model_id=$(echo "$input" | jq -r '.model.id // empty')
effort=$(echo  "$input" | jq -r '.effort.level // empty')

ctx=$(echo  "$input" | jq -r '.context_window.used_percentage        // empty')
five=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
fr=$(echo   "$input" | jq -r '.rate_limits.five_hour.resets_at       // empty')
wr=$(echo   "$input" | jq -r '.rate_limits.seven_day.resets_at       // empty')

# ---------------------------------------------------------------- sample log
# Format: <epoch> <five%> <week%> <five_resets_at> <week_resets_at>, "-" if absent
log_sample() {
  [ -z "$five$week" ] && return   # nothing worth recording
  local line last last_t last_rest
  line="$now ${five:--} ${week:--} ${fr:--} ${wr:--}"
  # throttle: skip if the readings are unchanged and the last one is recent
  if [ -f "$USAGE_LOG" ]; then
    last=$(tail -1 "$USAGE_LOG" 2>/dev/null)
    last_t=${last%% *}
    last_rest=${last#* }
    if [ "$last_rest" = "${line#* }" ] && [ -n "$last_t" ] \
       && (( now - last_t < 300 )); then
      return
    fi
  fi
  printf '%s\n' "$line" >> "$USAGE_LOG"
  # keep the file bounded (a 7-day window needs at most a few thousand rows)
  local n
  n=$(wc -l < "$USAGE_LOG" 2>/dev/null || echo 0)
  if (( n > 5000 )); then
    tail -2000 "$USAGE_LOG" > "$USAGE_LOG.tmp" && mv "$USAGE_LOG.tmp" "$USAGE_LOG"
  fi
}
log_sample

# ---------------------------------------------------------------- forecast
# forecast <pct_col> <reset_col> <cur_pct> <cur_reset> -> epoch of 100%, or empty
forecast() {
  local pc="$1" rc="$2" cur_pct="$3" cur_reset="$4"
  [ -z "$cur_pct" ] || [ -z "$cur_reset" ] && return
  [ -f "$USAGE_LOG" ] || return
  awk -v now="$now" -v cp="$cur_pct" -v cr="$cur_reset" -v pc="$pc" -v rc="$rc" '
    # first sample belonging to the current window (same resets_at)
    $rc == cr && $pc != "-" && t0 == "" { t0 = $1; p0 = $pc }
    END {
      if (t0 == "" || now <= t0) exit
      slope = (cp - p0) / (now - t0)     # %/sec, wall-clock
      if (slope <= 0) exit               # not moving yet -> no forecast
      eta = now + (100 - cp) / slope
      if (eta >= cr) exit                # window resets first -> nothing to warn
      printf "%d", eta
    }' "$USAGE_LOG"
}

# fmt_eta <epoch> -> "HH:MM" today, else "M/D HH:MM"
fmt_eta() {
  local e="$1"
  [ -z "$e" ] && return
  if [ "$(date -d "@$now" +%F)" = "$(date -d "@$e" +%F)" ]; then
    date -d "@$e" +'%H:%M'
  else
    date -d "@$e" +'%-m/%-d %H:%M'
  fi
}

# ---------------------------------------------------------------- rendering
# Render a 10-char colored gauge for a percentage (integer/float) or empty.
render_bar() {
  local val="$1"
  local width=10
  local out="" i

  # absent -> gray empty bar, no text
  if [ -z "$val" ]; then
    for ((i=0; i<width; i++)); do
      out+=$(printf '\033[38;5;245;48;5;236m ')
    done
    printf '%s\033[0m' "$out"
    return
  fi

  local p
  p=$(printf '%.0f' "$val")
  [ "$p" -lt 0 ]   && p=0
  [ "$p" -gt 100 ] && p=100

  # hue: dark / light 256-color codes
  local dark light
  if   [ "$p" -lt 80 ];  then dark=22;  light=120   # green
  elif [ "$p" -lt 100 ]; then dark=94;  light=215   # orange
  else                        dark=88;  light=210   # red
  fi

  local filled=$(( p / 10 ))   # floor: only 100% fills all 10

  local text="${p}%"               # integer percent (source resolution is 1)
  local L=${#text}
  local start
  if [ "$p" -lt 50 ]; then
    start=$(( width - L ))         # end at rightmost empty cell
  else
    start=0                        # start at leftmost filled cell
  fi
  (( start < 0 ))          && start=0
  (( start + L > width ))  && start=$(( width - L ))

  local ch fg bg
  for ((i=0; i<width; i++)); do
    ch=' '
    if (( i >= start && i < start + L )); then
      ch=${text:$((i - start)):1}
    fi
    if (( i < filled )); then
      fg=$dark;  bg=$light
    else
      fg=$light; bg=$dark
    fi
    out+=$(printf '\033[38;5;%d;48;5;%dm%s' "$fg" "$bg" "$ch")
  done
  printf '%s\033[0m' "$out"
}

ctx_bar=$(render_bar "$ctx")
five_bar=$(render_bar "$five")
week_bar=$(render_bar "$week")

# When a window is forecast to hit 100% before it resets, show the exhaustion
# time (red) followed by the reset time (blue) -- i.e. when you run out, and
# when you get it back. Otherwise the reset wins and nothing needs saying.
eta_disp() {                      # eta_disp <eta_epoch> <reset_epoch>
  local eta="$1" reset="$2"
  [ -z "$eta" ] && return
  printf ' \033[01;31m%s\033[00m \033[01;34m%s\033[00m' \
    "$(fmt_eta "$eta")" "$(fmt_eta "$reset")"
}

five_eta_disp=$(eta_disp "$(forecast 2 4 "$five" "$fr")" "$fr")
week_eta_disp=$(eta_disp "$(forecast 3 5 "$week" "$wr")" "$wr")

model_display=""
[ -n "$model_id" ] && model_display=$(printf '\033[01;36m%s\033[00m' "$model_id")

effort_display=""
[ -n "$effort" ] && effort_display=$(printf ' \033[01;35m%s\033[00m' "$effort")

printf '\033[01;34m%s\033[00m:\033[01;33m%s\033[00m\n' "$host" "$dir"
printf 'ctx:[%s] 5h:[%s]%s w:[%s]%s %s%s' \
  "$ctx_bar" "$five_bar" "$five_eta_disp" "$week_bar" "$week_eta_disp" \
  "$model_display" "$effort_display"
