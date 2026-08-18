#!/usr/bin/env python3
"""autonomy-stat: analyze a Claude Code agent's self-running time from a session jsonl.

usage:
    autonomy-stat.py stat <session-id|project-dir> <outfile.html>

<session-id|project-dir> accepts any of:
  - a session UUID       e.g. 66af0915-9b59-4b1e-88a3-ff312e0c2ed3
  - a full path to *.jsonl
  - a project-dir name   e.g. -home-user-myproject
                         (the latest session in that project is used)

Output: an HTML line chart, x-axis = time, y-axis = self-running time per turn.
Each point is one turn (from a human input until the agent stops).
"""

import sys
import os
import json
import glob
from datetime import datetime, timezone

PROJECTS_ROOT = os.path.expanduser("~/.claude/projects")

# If the agent goes silent (assistant gap) longer than this within a turn, the
# excess is treated as sleep/idle and is NOT counted as self-running time
# (tool-execution waits are handled separately).
IDLE_THRESHOLD_MS = 5 * 60 * 1000   # 5 min

# A single tool / background-agent wait longer than this is treated as an
# abandoned session (unattended approval prompt, orphaned background task whose
# notification only lands when the session is resumed days later) rather than
# real work: only the first TOOLWAIT_CAP_MS counts, the rest is idle.
# Observed data supports the cut: real builds/workflows top out around 2h,
# then there is a gap in the distribution before the abandonment cases.
TOOLWAIT_CAP_MS = 3 * 60 * 60 * 1000   # 3 h


# ---------------------------------------------------------------------------
# UI strings (only labels are localized; the analyzed data is never translated)
# ---------------------------------------------------------------------------
STRINGS = {
    "en": {
        "h1": "self-running time / turn",
        # stderr
        "info_latest": "[info] using latest session of project {arg}: {name}\n",
        "info_multi": "[info] multiple matches; using the latest:\n",
        "done": "[done] analyzed {n} turns -> {out}\n",
        "done2": ("        total self-running (incl) {incl:.0f} min / "
                  "(excl) {excl:.0f} min / longest (incl) {longest:.1f} min\n"),
        # meta block
        "m_turns": "turns",
        "m_total_incl": "total self-running (tool-wait incl)",
        "m_total_excl": "(tool-wait excl)",
        "m_toolwait": "of which tool-wait",
        "m_longest": "longest turn (incl)",
        "m_idle": "total between-turn idle",
        "m_min": "min",
        "m_excluded": ("excluded from self-running: /loop sleeps, "
                       "/compact history replays, unattended approval waits"),
        # JS labels
        "js": {
            "chartCycle": "continuous time",
            "chartBand": "agent running time",
            "chartRatio": "running-time share",
            "cA": "agent self-running",
            "cH": "human idle",
            "tTurn": "turn", "tStart": "start",
            "tIncl": "self-running (tool-wait incl)",
            "tExcl": "self-running (tool-wait excl)",
            "tWait": "tool-wait", "tSub": "subagent", "tWall": "wall",
            "tSleep": "sleep", "tExcluded": "excluded",
            "tMsgs": "assistant msgs", "tTools": "tool uses",
            "tIdle": "idle before", "tInput": "input",
            "hStart": "start", "hIncl": "self-running",
            "hExcl": "of which parent", "hWait": "of which non-parent",
            "hIdle": "idle after",
            "hInput": "prompt",
        },
    },
    "ja": {
        "h1": "自走時間 / ターン",
        "info_latest": "[info] プロジェクト {arg} の最新 session を採用: {name}\n",
        "info_multi": "[info] 複数一致。最新を採用:\n",
        "done": "[done] {n} ターンを解析 → {out}\n",
        "done2": ("        総自走(込) {incl:.0f} 分 / "
                  "(抜) {excl:.0f} 分 / 最長(込) {longest:.1f} 分\n"),
        "m_turns": "ターン数",
        "m_total_incl": "総自走(tool待ち込み)",
        "m_total_excl": "(tool待ち抜き)",
        "m_toolwait": "うち tool待ち",
        "m_longest": "最長ターン(込)",
        "m_idle": "ターン間の総待機(放置)",
        "m_min": "分",
        "m_excluded": "※ /loop スリープ・/compact 履歴リプレイ・承認待ち放置は自走から除外",
        "js": {
            "chartCycle": "連続時間",
            "chartBand": "エージェント稼働時間",
            "chartRatio": "稼働時間割合",
            "cA": "エージェント自走時間",
            "cH": "人間アイドル時間",
            "tTurn": "ターン", "tStart": "開始",
            "tIncl": "自走(tool待ち込み)",
            "tExcl": "自走(tool待ち抜き)",
            "tWait": "tool待ち", "tSub": "subagent", "tWall": "実経過(wall)",
            "tSleep": "内スリープ", "tExcluded": "除外",
            "tMsgs": "assistant応答", "tTools": "tool使用",
            "tIdle": "直前の待機", "tInput": "入力",
            "hStart": "開始時刻", "hIncl": "自走時間",
            "hExcl": "内訳(親)", "hWait": "内訳(親以外)",
            "hIdle": "直後待機",
            "hInput": "プロンプト",
        },
    },
}


# ---------------------------------------------------------------------------
# session resolution
# ---------------------------------------------------------------------------
def resolve_session(arg, lang="en"):
    """Resolve the argument to a session jsonl path."""
    s = STRINGS[lang]
    # 1) full path
    if arg.endswith(".jsonl") and os.path.isfile(arg):
        return arg
    # 2) project-dir name (-home-... form) -> latest session
    cand_dir = os.path.join(PROJECTS_ROOT, arg)
    if arg.startswith("-") and os.path.isdir(cand_dir):
        sessions = [
            p for p in glob.glob(os.path.join(cand_dir, "*.jsonl"))
            if not os.path.basename(p).startswith("agent-")
        ]
        if not sessions:
            raise SystemExit(f"no session jsonl in project {arg}")
        latest = max(sessions, key=os.path.getmtime)
        sys.stderr.write(s["info_latest"].format(arg=arg, name=os.path.basename(latest)))
        return latest
    # 3) UUID (or a prefix) -> search across all projects
    matches = []
    for path in glob.glob(os.path.join(PROJECTS_ROOT, "*", "*.jsonl")):
        base = os.path.basename(path)
        if base.startswith("agent-"):
            continue
        if base == f"{arg}.jsonl" or base.startswith(arg):
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        sys.stderr.write(s["info_multi"])
        for m in matches:
            sys.stderr.write(f"        {m}\n")
        return max(matches, key=os.path.getmtime)
    raise SystemExit(f"session not found: {arg}")


# ---------------------------------------------------------------------------
# jsonl parsing
# ---------------------------------------------------------------------------
def parse_ts(s):
    """ISO8601(Z) -> epoch milliseconds."""
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(s).timestamp() * 1000)
    except ValueError:
        return None


# Text starting with any of these is a harness injection, not human input.
INJECTED_MARKERS = (
    "<command-name>", "<command-message>", "<command-args>",
    "<local-command-stdout>", "<local-command-stderr>",
    "<task-notification>",       # background task completion notice
    "<system-reminder>",
    "<teammate-message",         # inter-session (multi-agent) message, raw
    "<cross-session-message",    # newer name for the same relay
    "Another Claude session sent a message:",  # relayed peer message
)
# Substrings that mark a harness/inter-agent injection anywhere in the text.
INJECTED_SUBSTRINGS = (
    "<teammate-message",         # peer relay (may carry a leading prefix)
    "<cross-session-message",
)
# Leading text of the summary auto-inserted on compaction continuation.
COMPACT_PREFIX = "This session is being continued from a previous conversation"


def is_genuine_user(entry):
    """True only for real human input (excludes tool results, meta, notifications, command output)."""
    if entry.get("type") != "user":
        return False
    if "toolUseResult" in entry:          # tool execution result
        return False
    if entry.get("isMeta"):               # auto-injected caveat etc.
        return False
    if entry.get("isSidechain"):          # input inside a subagent
        return False
    # `origin` is a dict in newer Claude Code logs. kind=="human" marks a real
    # human prompt; every other kind (task-notification, peer, ...) is injected.
    # Older logs have no `origin` at all, so absence is not disqualifying.
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") != "human":
        return False
    msg = entry.get("message", {})
    content = msg.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        # if it contains a tool_result, it is not human input
        if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return False
        text = " ".join(
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    else:
        return False
    stripped = text.lstrip()
    if stripped.startswith(INJECTED_MARKERS):
        return False
    if any(s in stripped for s in INJECTED_SUBSTRINGS):
        return False
    if stripped.startswith(COMPACT_PREFIX):   # compaction continuation summary
        return False
    return True


def user_text(entry):
    msg = entry.get("message", {})
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )
    return ""


def count_tool_uses(entry):
    msg = entry.get("message", {})
    content = msg.get("content", [])
    if not isinstance(content, list):
        return 0
    return sum(1 for c in content if isinstance(c, dict) and c.get("type") == "tool_use")


def subagent_ms(entry):
    """Return totalDurationMs if the tool result is a subagent (Task)."""
    tur = entry.get("toolUseResult")
    if isinstance(tur, dict):
        d = tur.get("totalDurationMs")
        if isinstance(d, (int, float)):
            return int(d)
    return 0


def is_task_notification(entry):
    """True if the entry is a background Workflow/Task completion notice.

    While a background agent runs, the parent transcript is silent; the only
    trace is this notification when it finishes.
    """
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") == "task-notification":
        return True
    msg = entry.get("message", {})
    content = msg.get("content")
    text = content if isinstance(content, str) else ""
    return text.lstrip().startswith("<task-notification>")


# If a timestamp jumps backward by more than this, treat the entry as a
# /compact-style history replay (old log re-logged with its original time).
REPLAY_TOLERANCE_MS = 60 * 1000   # 60 s


def drop_replayed(entries):
    """Remove history replayed by /compact, resume, etc.

    A session jsonl is normally near-chronological, but after compaction the
    conversation history is re-logged with its original (stale) timestamps.
    Entries that fall far behind a running monotonic clock are treated as
    replays and dropped (timestampless structural lines are kept).
    """
    out = []
    clock = None
    for e in entries:
        ts = parse_ts(e.get("timestamp"))
        if ts is None:
            out.append(e)
            continue
        if clock is not None and ts < clock - REPLAY_TOLERANCE_MS:
            continue                      # replay -> drop
        out.append(e)
        if clock is None or ts > clock:
            clock = ts
    return out


def parse_turns(path):
    """Read the jsonl and return a list of turns.

    A turn = consecutive human inputs (collapsed into one boundary) plus the
    agent activity that follows. Self-running time spans from the last human
    input to the last activity event of the turn.
    """
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    entries = drop_replayed(entries)

    turns = []
    i = 0
    n = len(entries)
    # skip until the first human input
    while i < n and not is_genuine_user(entries[i]):
        i += 1

    while i < n:
        # --- collapse consecutive human inputs (handles queued messages) ---
        prompts = []
        start_ts = None
        while i < n and is_genuine_user(entries[i]):
            ts = parse_ts(entries[i].get("timestamp"))
            if ts is not None:
                start_ts = ts          # use the last input's time
            prompts.append(user_text(entries[i]))
            i += 1

        # --- collect agent activity until the next human input ---
        # An "activity event" is an assistant message or a tool result. Only
        # these drive the turn; system / queue-operation / /command events
        # (which can occur after the agent stops) are ignored.
        # activity: (ts, kind) kind in {'assistant','tool_result'}
        activity = []
        n_assistant = 0
        n_tool = 0
        n_background = 0
        sub_ms = 0
        while i < n and not is_genuine_user(entries[i]):
            e = entries[i]
            etype = e.get("type")
            ts = parse_ts(e.get("timestamp"))
            if etype == "assistant":
                n_assistant += 1
                n_tool += count_tool_uses(e)
                if ts is not None:
                    activity.append((ts, "assistant"))
            elif etype == "user" and "toolUseResult" in e:
                sub_ms += subagent_ms(e)
                if ts is not None:
                    activity.append((ts, "tool_result"))
            elif etype == "user" and is_task_notification(e):
                # A background Workflow/Task finished here. The parent logs
                # nothing while it runs, so without this the whole background
                # run would look like an idle assistant gap. Treat it like a
                # tool result: the preceding gap was real (background) work.
                n_background += 1
                if ts is not None:
                    activity.append((ts, "tool_result"))
            i += 1

        if start_ts is None or not activity:
            continue

        # --- classify each inter-event gap into three buckets ---
        #  work     : assistant generation/thinking (within threshold). Always counted.
        #  toolwait : wait until a tool result (tool execution or approval wait).
        #  sleep    : assistant-gap excess over threshold (/loop sleep, idle). Excluded.
        # Two series are emitted:
        #  active_incl = work + toolwait   (tool-wait included)
        #  active_excl = work              (tool-wait excluded = pure model work)
        end_ts = activity[-1][0]
        work_ms = 0
        toolwait_ms = 0
        sleep_ms = 0
        prev_ts = start_ts
        for ts, kind in activity:
            gap = ts - prev_ts
            if gap < 0:
                gap = 0
            if kind == "tool_result":
                # tool execution / background agent run / approval wait
                if gap <= TOOLWAIT_CAP_MS:
                    toolwait_ms += gap
                else:
                    toolwait_ms += TOOLWAIT_CAP_MS     # plausible run time
                    sleep_ms += gap - TOOLWAIT_CAP_MS  # excess = abandoned
            elif gap <= IDLE_THRESHOLD_MS:
                work_ms += gap                         # normal generation/thinking
            else:
                work_ms += IDLE_THRESHOLD_MS           # cap counted as work
                sleep_ms += gap - IDLE_THRESHOLD_MS    # excess is sleep/idle
            prev_ts = ts

        prompt = next((p for p in prompts if p.strip()), "")
        turns.append({
            "start": start_ts,
            "end": end_ts,
            "active_incl_sec": round((work_ms + toolwait_ms) / 1000, 1),
            "active_excl_sec": round(work_ms / 1000, 1),
            "toolwait_sec": round(toolwait_ms / 1000, 1),
            "wall_sec": round((end_ts - start_ts) / 1000, 1),
            "intra_idle_sec": round(sleep_ms / 1000, 1),
            "subagent_sec": round(sub_ms / 1000, 1),
            "n_assistant": n_assistant,
            "n_tool": n_tool,
            "n_background": n_background,
            "prompt": prompt[:200],
        })

    # attach between-turn idle (the agent stopped, waiting for the human)
    for k in range(1, len(turns)):
        gap = (turns[k]["start"] - turns[k - 1]["end"]) / 1000
        turns[k]["idle_before_sec"] = round(gap, 1)
    if turns:
        turns[0]["idle_before_sec"] = 0.0
    # H_k: the wait that follows this turn (None for the last, still open)
    for k in range(len(turns)):
        turns[k]["idle_after_sec"] = (turns[k + 1]["idle_before_sec"]
                                      if k + 1 < len(turns) else None)
    return turns


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<title>Autonomy Statistics: __TITLE__</title>
<script src="vendor/plotly.min.js"
        onerror="this.onerror=null;this.src='https://cdn.plot.ly/plotly-2.35.2.min.js'"></script>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; color: #d4d4d4; background:#1a1a1a; }
  h1 { font-size: 18px; color:#e8e8e8; }
  .meta { color:#9a9a9a; font-size:13px; margin-bottom:16px; line-height:1.6; }
  .hint { color:#777; font-size:12px; margin-bottom:10px; }
  .chart { border:1px solid #3a3a3a; border-radius:6px; margin-bottom:14px; }
  table { border-collapse: collapse; margin-top:20px; font-size:13px; }
  th,td { border:1px solid #3a3a3a; padding:4px 8px; text-align:right; }
  th { background:#2c2c2c; color:#ddd; }
  td.prompt { text-align:left; max-width:420px; color:#b0b0b0;
              overflow-wrap:anywhere; word-break:break-word; }
</style>
</head>
<body>
<h1>Autonomy Statistics</h1>
<div class="hint">drag to zoom &middot; double-click to reset &middot; scroll to zoom</div>
<div id="cBand" class="chart"></div>
<div id="cRatio" class="chart"></div>
<div id="cCyc" class="chart"></div>
<div class="meta">__META__</div>
<table id="tbl"></table>
<script>
const DATA = __DATA__;
const L = __LABELS__;
const CY = __CYCLE__;
const BN = __BINS__;
const C_AGENT = '#4da3ff';  // agent self-running (same blue as the charts)
const C_IDLE  = '#d60000';  // human idle (same red as the charts)

function fmtTime(ms){ return new Date(ms).toLocaleString(); }
function fmtDur(sec){
  if (sec < 60) return sec.toFixed(1)+'s';
  const m = Math.floor(sec/60), s = Math.round(sec%60);
  if (m < 60) return m+'m'+s+'s';
  const h = Math.floor(m/60);
  return h+'h'+(m%60)+'m';
}
// shared time axis: labels every 3 h, gridlines once a day
const AX = (function(){
  const t0 = Math.min(...CY.map(c => c.t)), t1 = Math.max(...CY.map(c => c.t));
  const STEP = 3*3600*1000;
  const first = new Date(t0);
  first.setHours(Math.floor(first.getHours()/3)*3, 0, 0, 0);
  const XTV = [], XTT = [], DAYS = [];
  const p2 = n => String(n).padStart(2,'0');
  for (let t = first.getTime(); t <= t1 + STEP; t += STEP){
    const d = new Date(t);
    XTV.push(t);
    if (d.getHours() === 0){
      XTT.push(p2(d.getMonth()+1)+'/'+p2(d.getDate())+' '+p2(d.getHours())+':00');
      DAYS.push(t);
    } else {
      XTT.push(d.getHours()+':00');
    }
  }
  // exact full span so the three charts line up on load (no auto padding)
  const T0 = Math.min(...CY.map(c => c.t));
  const T1 = Math.max(
    Math.max(...CY.map(c => c.t + (c.A || 0)*60000 + (c.H || 0)*60000)),
    ...BN.map(b => b.t + 3*3600*1000));
  return {XTV: XTV, XTT: XTT, T0: T0, T1: T1,
          daySh: DAYS.map(t => ({type:'line', x0:t, x1:t, xref:'x',
                                 yref:'paper', y0:0, y1:1,
                                 line:{color:'#2c2c2c', width:1}})),
          axis: {type:'date', showgrid:false, linecolor:'#666', zeroline:false,
                 tickvals: XTV, ticktext: XTT, range: [T0, T1], autorange: false,
                 tickangle: -90, tickfont: {size: 9}}};
})();

// ---- per-cycle: x = t_k (prompt time), y = A_k (agent) and H_k (human idle)
(function drawCycle(){
  const xs = CY.map(c => new Date(c.t));
  // linear axis with a nice step chosen from the data
  const mx = Math.max(1, ...CY.map(c => c.A || 0), ...CY.map(c => c.H || 0));
  const CAND = [5,10,15,30,60,120,180,240,360,480,720,1440,2880,4320];
  let step = CAND[CAND.length-1];
  for (const c of CAND){ if (mx/c <= 6){ step = c; break; } }
  const top = Math.ceil(mx/step)*step;
  const YTV = [], YTT = [];
  for (let v = 0; v <= top+1; v += step){
    YTV.push(v);
    YTT.push(v === 0 ? '0'
           : (v % 1440 === 0 ? (v/1440)+'d'
           : (v % 60 === 0 ? (v/60)+'h' : v+'m')));
  }
  const traces = [
    {x: xs, y: CY.map(c => c.A), type:'scatter', mode:'lines+markers',
     name: L.cA, line:{color:'#4da3ff', width:1.2}, marker:{color:'#4da3ff', size:4},
     hovertemplate: '%{x}<br>'+L.cA+': %{y:.1f} min<extra></extra>'},
    {x: xs, y: CY.map(c => c.H), type:'scatter', mode:'lines+markers',
     name: L.cH, line:{color:'#d60000', width:1.2}, marker:{color:'#d60000', size:4},
     connectgaps: false,
     hovertemplate: '%{x}<br>'+L.cH+': %{y:.1f} min<extra></extra>'}
  ];
  const layout = {
    title: {text: L.chartCycle, font: {size: 13, color: '#ccc'}, x: 0.01, xanchor: 'left'},
    paper_bgcolor: '#1a1a1a', plot_bgcolor: '#222',
    font: {color: '#c0c0c0', size: 11},
    margin: {l: 72, r: 24, t: 62, b: 78},
    xaxis: Object.assign({}, AX.axis),
    // shapes default to the top layer; push them behind the traces here
    shapes: AX.daySh.map(o => Object.assign({}, o, {layer: 'below'})),
    yaxis: {tickvals: YTV, ticktext: YTT, range: [0, top], rangemode: 'tozero',
            gridcolor:'#333', linecolor:'#666', zeroline:false,
            layer: 'below traces'},
    dragmode: 'zoom', hovermode: 'closest', height: 400,
    legend: {orientation:'h', x:1, xanchor:'right', y:1.10, yanchor:'bottom',
             font:{size:11}, bgcolor:'rgba(0,0,0,0)'},
    hoverlabel: {bgcolor: 'rgba(10,10,10,.95)', bordercolor: '#444',
                 font: {color: '#eee', size: 12}}
  };
  Plotly.newPlot('cCyc', traces, layout,
                 {responsive: true, displaylogo: false, scrollZoom: true});
})();

// ---- occupancy band: equal-height bars, colour tells who owns each stretch
(function drawBand(){
  const MS = 60000;
  const agent = CY.filter(c => c.A > 0);
  const idle  = CY.filter(c => c.H != null && c.H > 0);
  const fmt = m => m < 60 ? m.toFixed(1)+'m'
                          : Math.floor(m/60)+'h'+Math.round(m%60)+'m';
  const bar = (base, dur, vals, color, name) => ({
    type: 'bar', orientation: 'h',
    y: base.map(() => ''), base: base, x: dur,
    marker: {color: color, line: {width: 0}},
    name: name, customdata: vals.map(fmt),
    hovertemplate: name + ': %{customdata}<extra></extra>'
  });
  // same series order as the other two charts: agent (blue) then human idle (red)
  const traces = [
    bar(agent.map(c => c.t), agent.map(c => c.A*MS), agent.map(c => c.A),
        '#4da3ff', L.cA),
    bar(idle.map(c => c.t + c.A*MS), idle.map(c => c.H*MS), idle.map(c => c.H),
        '#d60000', L.cH)
  ];
  const layout = {
    title: {text: L.chartBand, font: {size: 13, color: '#ccc'}, x: 0.01, xanchor: 'left'},
    paper_bgcolor: '#1a1a1a', plot_bgcolor: '#222',
    font: {color: '#c0c0c0', size: 11},
    margin: {l: 72, r: 24, t: 62, b: 78},
    xaxis: Object.assign({}, AX.axis),   // labels kept, no gridlines here
    yaxis: {showticklabels: false, showgrid: false, zeroline: false,
            linecolor: '#666', fixedrange: true},
    barmode: 'overlay', bargap: 0, showlegend: true,
    dragmode: 'zoom', hovermode: 'closest', height: 190,
    legend: {orientation:'h', x:1, xanchor:'right', y:1.10, yanchor:'bottom',
             font:{size:11}, bgcolor:'rgba(0,0,0,0)'},
    hoverlabel: {bgcolor: 'rgba(10,10,10,.95)', bordercolor: '#444',
                 font: {color: '#eee', size: 12}}
  };
  Plotly.newPlot('cBand', traces, layout,
                 {responsive: true, displaylogo: false, scrollZoom: true});
})();

// ---- share of the clock: stacked to 100 %, filled
(function drawRatio(){
  // aggregated into fixed 3 h bins, drawn as steps (each bin held to its end)
  const BIN = 3*3600*1000;
  const last = BN[BN.length-1];
  const xs = BN.map(b => new Date(b.t)).concat([new Date(last.t + BIN)]);
  const ys = key => BN.map(b => b[key]).concat([last[key]]);
  const traces = [
    {x: xs, y: ys('A'), type:'scatter', mode:'none', line:{shape:'hv'},
     stackgroup:'one', groupnorm:'percent', fillcolor:'#4da3ff',
     name: L.cA, hovertemplate: L.cA+': %{y:.1f}%<extra></extra>'},
    {x: xs, y: ys('H'), type:'scatter', mode:'none', line:{shape:'hv'},
     stackgroup:'one', fillcolor:'#d60000',
     name: L.cH, hovertemplate: L.cH+': %{y:.1f}%<extra></extra>'}
  ];
  const layout = {
    title: {text: L.chartRatio, font: {size: 13, color: '#ccc'}, x: 0.01, xanchor: 'left'},
    paper_bgcolor: '#1a1a1a', plot_bgcolor: '#222',
    font: {color: '#c0c0c0', size: 11},
    margin: {l: 72, r: 24, t: 62, b: 78},
    xaxis: Object.assign({}, AX.axis),
    shapes: AX.daySh.map(o => Object.assign({}, o)),
    yaxis: {range: [0, 100], ticksuffix: '%', gridcolor:'#333',
            linecolor:'#666', zeroline:false},
    dragmode: 'zoom', hovermode: 'x unified', height: 320,
    legend: {orientation:'h', x:1, xanchor:'right', y:1.10, yanchor:'bottom',
             font:{size:11}, bgcolor:'rgba(0,0,0,0)'},
    hoverlabel: {bgcolor: 'rgba(10,10,10,.95)', bordercolor: '#444',
                 font: {color: '#eee', size: 12}}
  };
  Plotly.newPlot('cRatio', traces, layout,
                 {responsive: true, displaylogo: false, scrollZoom: true});
})();

// ---- keep the three x axes in sync (zoom one, the others follow)
(function linkX(){
  const IDS = ['cCyc', 'cBand', 'cRatio'];
  let syncing = false;                 // guard: our own relayout must not recurse
  IDS.forEach(id => {
    const gd = document.getElementById(id);
    if (!gd || !gd.on) return;
    gd.on('plotly_relayout', ev => {
      if (syncing || !ev) return;
      let upd;
      if (ev['xaxis.range[0]'] !== undefined && ev['xaxis.range[1]'] !== undefined){
        upd = {'xaxis.range[0]': ev['xaxis.range[0]'],
               'xaxis.range[1]': ev['xaxis.range[1]']};
      } else if (ev['xaxis.autorange'] === true){
        upd = {'xaxis.autorange': true};
      } else {
        return;                        // legend clicks etc. are not x changes
      }
      syncing = true;
      Promise.all(IDS.filter(o => o !== id)
                     .map(o => Plotly.relayout(o, upd)))
             .then(() => { syncing = false; })
             .catch(() => { syncing = false; });
    });
  });
})();

// table
const tbl = document.getElementById('tbl');
let html = '<tr><th>#</th><th>'+L.hStart+'</th><th>'+L.hIncl+'</th><th>'+L.hExcl+'</th>'+
           '<th>'+L.hWait+'</th><th>'+L.hIdle+'</th><th>'+L.hInput+'</th></tr>';
DATA.forEach((d,i)=>{
  html += '<tr><td>'+(i+1)+'</td><td>'+fmtTime(d.start)+'</td>'+
    '<td style="color:'+C_AGENT+'">'+fmtDur(d.active_incl_sec)+'</td>'+
    '<td>'+fmtDur(d.active_excl_sec)+'</td>'+
    '<td>'+fmtDur(d.toolwait_sec)+'</td>'+
    '<td style="color:'+C_IDLE+'">'+
      (d.idle_after_sec == null ? '-' : fmtDur(d.idle_after_sec))+'</td>'+
    '<td class="prompt">'+escapeHtml(d.prompt)+'</td></tr>';
});
tbl.innerHTML = html;
function escapeHtml(s){ return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
</script>
</body>
</html>
"""


BIN_MS = 3 * 60 * 60 * 1000   # 3 h bins for the share chart


def bin_series(turns, bin_ms=BIN_MS):
    """Agent vs human-idle minutes per fixed 3 h bin.

    Each interval is split at the bin edges, so a long stretch contributes to
    every bin it covers. Bins align to 0:00/3:00/... local time (JST offset is
    a whole multiple of the bin size).
    """
    bins = {}

    def add(t0, t1, idx):
        while t0 < t1:
            b = (t0 // bin_ms) * bin_ms
            nxt = min(b + bin_ms, t1)
            bins.setdefault(b, [0.0, 0.0])[idx] += nxt - t0
            t0 = nxt

    for i, t in enumerate(turns):
        add(t["start"], t["end"], 0)
        if i + 1 < len(turns):
            add(t["end"], turns[i + 1]["start"], 1)
    return [{"t": b, "A": round(v[0] / 60000, 2), "H": round(v[1] / 60000, 2)}
            for b, v in sorted(bins.items())]


def cycle_series(turns):
    """Per cycle k: t_k = prompt time, A_k = a_k - t_k, H_k = h_k - a_k (minutes).

    a_k is when the agent went quiet (turn end); h_k is the next human prompt,
    so the last cycle has no H_k.
    """
    out = []
    for i, t in enumerate(turns):
        nxt = turns[i + 1]["start"] if i + 1 < len(turns) else None
        out.append({
            "t": t["start"],
            "A": round(t["wall_sec"] / 60, 2),
            "H": round((nxt - t["end"]) / 60000, 2) if nxt is not None else None,
        })
    return out


def write_html(turns, session_path, outfile, lang="en"):
    s = STRINGS[lang]
    u = s["m_min"]
    total_incl = sum(t["active_incl_sec"] for t in turns)
    total_excl = sum(t["active_excl_sec"] for t in turns)
    total_toolwait = sum(t["toolwait_sec"] for t in turns)
    total_idle = sum(t.get("idle_before_sec", 0) for t in turns)
    max_incl = max((t["active_incl_sec"] for t in turns), default=0)
    meta = (
        f"session: {os.path.basename(session_path)}<br>"
        f"{s['m_turns']}: {len(turns)} / "
        f"{s['m_total_incl']}: {total_incl/60:.0f} {u} / "
        f"{s['m_total_excl']}: {total_excl/60:.0f} {u} / "
        f"{s['m_toolwait']}: {total_toolwait/60:.0f} {u}<br>"
        f"{s['m_longest']}: {max_incl/60:.1f} {u} / "
        f"{s['m_idle']}: {total_idle/60:.0f} {u}<br>"
        f"<span style='color:#888'>{s['m_excluded']}</span>"
    )
    html = (HTML_TEMPLATE
            .replace("__LANG__", lang)
            .replace("__H1__", s["h1"])
            .replace("__TITLE__", os.path.basename(session_path))
            .replace("__META__", meta)
            .replace("__LABELS__", json.dumps(s["js"], ensure_ascii=False))
            .replace("__CYCLE__", json.dumps(cycle_series(turns)))
            .replace("__BINS__", json.dumps(bin_series(turns)))
            .replace("__DATA__", json.dumps(turns, ensure_ascii=False)))
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
def cmd_stat(argv):
    # parse --lang en|ja (default en), strip it out of positional args
    lang = "en"
    pos = []
    skip = -1
    for idx, tok in enumerate(argv):
        if idx == skip:
            continue
        if tok == "--lang":
            if idx + 1 >= len(argv):
                raise SystemExit("--lang requires a value (en|ja)")
            lang = argv[idx + 1]
            skip = idx + 1
        elif tok.startswith("--lang="):
            lang = tok.split("=", 1)[1]
        else:
            pos.append(tok)
    if lang not in STRINGS:
        raise SystemExit(f"unknown --lang {lang!r} (supported: {', '.join(STRINGS)})")
    if len(pos) < 2:
        raise SystemExit(
            "usage: autonomy-stat.py stat <session-id|project-dir> <outfile.html> [--lang en|ja]")
    session_arg, outfile = pos[0], pos[1]
    s = STRINGS[lang]
    path = resolve_session(session_arg, lang)
    turns = parse_turns(path)
    if not turns:
        raise SystemExit("no analyzable turns found")
    write_html(turns, path, outfile, lang)
    sys.stderr.write(s["done"].format(n=len(turns), out=outfile))
    sys.stderr.write(s["done2"].format(
        incl=sum(t["active_incl_sec"] for t in turns) / 60,
        excl=sum(t["active_excl_sec"] for t in turns) / 60,
        longest=max(t["active_incl_sec"] for t in turns) / 60,
    ))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "stat":
        cmd_stat(sys.argv[2:])
    else:
        raise SystemExit(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
