#!/bin/bash
# statusLine command for Claude Code
# Line 1: host:dir
# Line 2: <m>ctx:[bar] pc 5h:[bar]>ETA w:[bar]>ETA <model> <effort>
#
# <m> is a short model tag in the leftmost column, so the current model is
# readable without scanning to the end of the line:
#   "o5 " opus-5   / "s5 " sonnet-5   / "f5 " fable-5
#   "o51 " opus-5.1 / "s51 " sonnet-5.1 / "f51 " fable-5.1
#   "" anything else
# A "[1m]"/"[2m]" context-size suffix on the id is ignored, so the 1M variant
# gets the same tag as the plain model.
# Unknown models contribute nothing at all (not even a space), so the line
# simply starts at "ctx:".
#
# pc is the upstream prompt-cache countdown. While the cache is warm a request
# re-sends almost nothing; when it expires the whole conversation is re-sent and
# prompt_cache.recache_tokens_if_cold input tokens are paid again. So:
#   green  "pc:47m"     warm, more than $PC_WARN minutes left
#   orange "pc:6m"      warm, $PC_WARN minutes or less -- the rebuild is near
#   red    "pc:cold 103k"  already cold; 103k is what the next request re-sends
#   absent prompt_cache -> nothing shown (no requests made yet)
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

# One jq for the whole payload. The status line is re-run on a timer, not only
# when the user speaks, so a process per field would be a process per field on
# every tick. Order matters: dir is the only free-text value, so it goes last,
# where a newline inside a directory name can only truncate itself instead of
# shifting every field after it.
mapfile -t F < <(jq -r '
  [ (.model.id                              // ""),
    (.effort.level                          // ""),
    (.context_window.used_percentage        // ""),
    (.rate_limits.five_hour.used_percentage // ""),
    (.rate_limits.seven_day.used_percentage // ""),
    (.rate_limits.five_hour.resets_at       // ""),
    (.rate_limits.seven_day.resets_at       // ""),
    # warm is a real boolean, and the // operator swallows false as well as
    # null, so ask for it explicitly: that keeps a cold cache distinguishable
    # from no prompt_cache at all.
    (.prompt_cache.warm | if . == null then "" else tostring end),
    (.prompt_cache.expires_at               // ""),
    (.prompt_cache.recache_tokens_if_cold   // ""),
    (.workspace.current_dir // .cwd         // "")
  ] | .[] | tostring' <<<"$input" 2>/dev/null)

model_id=${F[0]}
effort=${F[1]}
ctx=${F[2]}
five=${F[3]}
week=${F[4]}
fr=${F[5]}
wr=${F[6]}
pc_warm=${F[7]}
pc_exp=${F[8]}
pc_cold=${F[9]}
dir=${F[10]}
[ -z "$dir" ] && dir=$(pwd)

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

# ---------------------------------------------------------------- prompt cache
PC_WARN=10                        # minutes left at which pc turns orange

fmt_tok() {                       # 102885 -> "103k"
  local t="$1"
  if   (( t >= 1000000 )); then printf '%dM' $(( (t + 500000) / 1000000 ))
  elif (( t >= 1000    )); then printf '%dk' $(( (t + 500) / 1000 ))
  else                          printf '%d'  "$t"
  fi
}

pc_disp=""
if [ -n "$pc_warm" ]; then
  if [ "$pc_warm" = "true" ] && [[ $pc_exp =~ ^[0-9]+$ ]] && (( pc_exp > now )); then
    mins=$(( (pc_exp - now + 59) / 60 ))     # round up: "1m" until it really goes
    if (( mins > PC_WARN )); then pc_col=32; else pc_col=33; fi
    pc_disp=$(printf ' \033[01;%dmpc:%dm\033[00m' "$pc_col" "$mins")
  elif [[ $pc_cold =~ ^[0-9]+$ ]] && (( pc_cold > 0 )); then
    pc_disp=$(printf ' \033[01;31mpc:cold %s\033[00m' "$(fmt_tok "$pc_cold")")
  else
    pc_disp=$(printf ' \033[01;31mpc:cold\033[00m')
  fi
fi

ctx_bar=$(render_bar "$ctx")
five_bar=$(render_bar "$five")
week_bar=$(render_bar "$week")

# The reset time (blue) is always shown when available -- i.e. when you get the
# quota back. When a window is also forecast to hit 100% before it resets, the
# exhaustion time (red) is prepended -- i.e. when you run out.
eta_disp() {                      # eta_disp <eta_epoch> <reset_epoch>
  local eta="$1" reset="$2"
  [ -z "$reset" ] && return
  if [ -n "$eta" ]; then
    printf ' \033[01;31m%s\033[00m \033[01;34m%s\033[00m' \
      "$(fmt_eta "$eta")" "$(fmt_eta "$reset")"
  else
    printf ' \033[01;34m%s\033[00m' "$(fmt_eta "$reset")"
  fi
}

five_eta_disp=$(eta_disp "$(forecast 2 4 "$five" "$fr")" "$fr")
week_eta_disp=$(eta_disp "$(forecast 3 5 "$week" "$wr")" "$wr")

model_display=""
[ -n "$model_id" ] && model_display=$(printf '\033[01;36m%s\033[00m' "$model_id")

# Leftmost short tag. Point releases get their own tag (claude-fable-5-1 ->
# "f51") and must be listed before the base "-5-*" patterns, which would
# otherwise swallow them. The dated variants (claude-opus-5-20260101) are
# matched too, so the tag does not silently vanish if the id gains a date.
# The 1M-context variant appends a "[1m]" suffix to the id, so this session's
# id is "claude-opus-5[1m]", which matches none of the patterns below. Claude
# Code itself strips /\[(1|2)m\]$/i before every id comparison, so do the same
# here: cut everything from the first "[" onward.
model_base=${model_id%%"["*}

model_short=""
case "$model_base" in
  claude-opus-5-1|claude-opus-5-1-*)     model_short='o51' ;;
  claude-sonnet-5-1|claude-sonnet-5-1-*) model_short='s51' ;;
  claude-fable-5-1|claude-fable-5-1-*)   model_short='f51' ;;
  claude-opus-5|claude-opus-5-*)         model_short='o5'  ;;
  claude-sonnet-5|claude-sonnet-5-*)     model_short='s5'  ;;
  claude-fable-5|claude-fable-5-*)       model_short='f5'  ;;
esac
model_short_display=""
[ -n "$model_short" ] && \
  model_short_display=$(printf '\033[01;36m%s\033[00m ' "$model_short")

effort_display=""
[ -n "$effort" ] && effort_display=$(printf ' \033[01;35m%s\033[00m' "$effort")

printf '\033[01;34m%s\033[00m:\033[01;33m%s\033[00m\n' "$host" "$dir"
printf '%sctx:[%s]%s 5h:[%s]%s w:[%s]%s %s%s' \
  "$model_short_display" \
  "$ctx_bar" "$pc_disp" "$five_bar" "$five_eta_disp" "$week_bar" "$week_eta_disp" \
  "$model_display" "$effort_display"
