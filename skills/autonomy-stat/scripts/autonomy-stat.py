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
            "chartExcl": "self-running time / turn (tool-wait excluded)",
            "chartIncl": "self-running time / turn (tool-wait included)",
            "tTurn": "turn", "tStart": "start",
            "tIncl": "self-running (tool-wait incl)",
            "tExcl": "self-running (tool-wait excl)",
            "tWait": "tool-wait", "tSub": "subagent", "tWall": "wall",
            "tSleep": "sleep", "tExcluded": "excluded",
            "tMsgs": "assistant msgs", "tTools": "tool uses",
            "tIdle": "idle before", "tInput": "input",
            "hStart": "start", "hIncl": "self-run (incl)",
            "hExcl": "self-run (excl)", "hWait": "tool-wait", "hWall": "wall",
            "hMsgs": "msgs", "hTools": "tools", "hIdle": "idle before",
            "hInput": "input (head)",
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
            "chartExcl": "自走時間 / ターン(tool待ち抜き)",
            "chartIncl": "自走時間 / ターン(tool待ち込み)",
            "tTurn": "ターン", "tStart": "開始",
            "tIncl": "自走(tool待ち込み)",
            "tExcl": "自走(tool待ち抜き)",
            "tWait": "tool待ち", "tSub": "subagent", "tWall": "実経過(wall)",
            "tSleep": "内スリープ", "tExcluded": "除外",
            "tMsgs": "assistant応答", "tTools": "tool使用",
            "tIdle": "直前の待機", "tInput": "入力",
            "hStart": "開始時刻", "hIncl": "自走(込)",
            "hExcl": "自走(抜)", "hWait": "tool待ち", "hWall": "実経過",
            "hMsgs": "応答", "hTools": "tool", "hIdle": "直前待機",
            "hInput": "入力(先頭)",
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
    "Another Claude session sent a message:",  # relayed teammate message
)
# Substrings that mark a harness/inter-agent injection anywhere in the text.
INJECTED_SUBSTRINGS = (
    "<teammate-message",         # teammate relay (may carry a leading prefix)
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
    # origin as a dict (kind=task-notification etc.) is a harness injection
    origin = entry.get("origin")
    if isinstance(origin, dict):
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
                toolwait_ms += gap                     # tool execution / approval wait
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
            "prompt": prompt[:200],
        })

    # attach between-turn idle (the agent stopped, waiting for the human)
    for k in range(1, len(turns)):
        gap = (turns[k]["start"] - turns[k - 1]["end"]) / 1000
        turns[k]["idle_before_sec"] = round(gap, 1)
    if turns:
        turns[0]["idle_before_sec"] = 0.0
    return turns


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<title>autonomy-stat: __TITLE__</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; color: #d4d4d4; background:#1a1a1a; }
  h1 { font-size: 18px; color:#e8e8e8; }
  .meta { color:#9a9a9a; font-size:13px; margin-bottom:16px; line-height:1.6; }
  canvas { background:#222; border:1px solid #3a3a3a; border-radius:6px; display:block; margin-bottom:14px; }
  #tip { position:fixed; pointer-events:none; background:rgba(10,10,10,.95); color:#eee;
         border:1px solid #444; font-size:12px; padding:8px 10px; border-radius:5px;
         display:none; max-width:360px; line-height:1.5; white-space:pre-wrap; z-index:10; }
  table { border-collapse: collapse; margin-top:20px; font-size:13px; }
  th,td { border:1px solid #3a3a3a; padding:4px 8px; text-align:right; }
  th { background:#2c2c2c; color:#ddd; }
  td.prompt { text-align:left; max-width:420px; color:#b0b0b0; }
</style>
</head>
<body>
<h1>autonomy-stat &mdash; __H1__</h1>
<div class="meta">__META__</div>
<canvas id="cTop" width="1040" height="320"></canvas>
<canvas id="cBot" width="1040" height="320"></canvas>
<div id="tip"></div>
<table id="tbl"></table>
<script>
const DATA = __DATA__;
const L = __LABELS__;
const HOUR = 3600, DAY_MS = 86400000;
const C_INCL = '#ff9f40';   // tool-wait included
const C_EXCL = '#4da3ff';   // tool-wait excluded
const xs = DATA.map(d => d.start);
const xmin = Math.min(...xs), xmax = Math.max(...xs);
const xspan = (xmax - xmin) || 1;
const tip = document.getElementById('tip');

function fmtTime(ms){ return new Date(ms).toLocaleString(); }
function fmtDur(sec){
  if (sec < 60) return sec.toFixed(1)+'s';
  const m = Math.floor(sec/60), s = Math.round(sec%60);
  if (m < 60) return m+'m'+s+'s';
  const h = Math.floor(m/60);
  return h+'h'+(m%60)+'m';
}
// axis ticks: pick a "nice" step that fits the data
const STEPS = [60,120,300,600,900,1800,3600,7200,10800,21600,43200,86400];
function niceStep(maxv){
  for (const s of STEPS){ if (maxv/s <= 6) return s; }
  return STEPS[STEPS.length-1];
}
function fmtTick(sec){
  if (sec % 3600 === 0) return (sec/3600)+'h';
  if (sec % 60 === 0)   return (sec/60)+'m';
  return sec+'s';
}

function tipText(d, idx){
  return L.tTurn+' #'+(idx+1)+'\\n'+
    L.tStart+': '+fmtTime(d.start)+'\\n'+
    L.tIncl+': '+fmtDur(d.active_incl_sec)+'\\n'+
    L.tExcl+': '+fmtDur(d.active_excl_sec)+'\\n'+
    L.tWait+': '+fmtDur(d.toolwait_sec)+
    (d.subagent_sec>0 ? ' ('+L.tSub+' '+fmtDur(d.subagent_sec)+')' : '')+'\\n'+
    L.tWall+': '+fmtDur(d.wall_sec)+
    (d.intra_idle_sec>0 ? ' ('+L.tSleep+' '+fmtDur(d.intra_idle_sec)+' '+L.tExcluded+')' : '')+'\\n'+
    L.tMsgs+': '+d.n_assistant+' / '+L.tTools+': '+d.n_tool+'\\n'+
    L.tIdle+': '+fmtDur(d.idle_before_sec)+'\\n'+
    L.tInput+': '+d.prompt;
}

function makeChart(id, accessor, color, label){
  const cv = document.getElementById(id), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const M = {l:70, r:30, t:28, b:46};
  const plotW = W-M.l-M.r, plotH = H-M.t-M.b;
  const dataMax = Math.max(0, ...DATA.map(accessor));
  const step = niceStep(Math.max(dataMax, 1));
  const ymax = Math.max(step, Math.ceil(dataMax/step)*step);
  const X = t => M.l + (t-xmin)/xspan * plotW;
  const Y = v => M.t + plotH - (v/ymax) * plotH;

  ctx.clearRect(0,0,W,H);
  // y grid (nice step)
  ctx.fillStyle='#9a9a9a'; ctx.font='11px sans-serif';
  ctx.textAlign='right'; ctx.textBaseline='middle';
  for (let v=0; v<=ymax+1; v+=step){
    const y=Y(v); ctx.strokeStyle='#333';
    ctx.beginPath(); ctx.moveTo(M.l,y); ctx.lineTo(W-M.r,y); ctx.stroke();
    ctx.fillText(fmtTick(v), M.l-8, y);
  }
  // x grid (per day)
  ctx.textAlign='center'; ctx.textBaseline='top';
  const d0=new Date(xmin); d0.setHours(0,0,0,0);
  for (let t=d0.getTime(); t<=xmax+DAY_MS; t+=DAY_MS){
    if (t<xmin) continue;
    const x=X(t); ctx.strokeStyle='#2c2c2c';
    ctx.beginPath(); ctx.moveTo(x,M.t); ctx.lineTo(x,M.t+plotH); ctx.stroke();
    const d=new Date(t); ctx.fillStyle='#9a9a9a';
    ctx.fillText((d.getMonth()+1)+'/'+d.getDate(), x, M.t+plotH+6);
  }
  // axes
  ctx.strokeStyle='#666'; ctx.beginPath();
  ctx.moveTo(M.l,M.t); ctx.lineTo(M.l,M.t+plotH); ctx.lineTo(W-M.r,M.t+plotH); ctx.stroke();
  // title
  ctx.fillStyle=color; ctx.font='13px sans-serif';
  ctx.textAlign='left'; ctx.textBaseline='middle';
  ctx.fillText(label, M.l+12, M.t+8);
  // line + points
  ctx.strokeStyle=color; ctx.lineWidth=1.5; ctx.beginPath();
  DATA.forEach((d,i)=>{ const x=X(d.start), y=Y(accessor(d));
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
  ctx.stroke();
  DATA.forEach(d=>{
    ctx.beginPath(); ctx.arc(X(d.start), Y(accessor(d)), 3, 0, 7);
    ctx.fillStyle=color; ctx.fill();
    ctx.strokeStyle='#1a1a1a'; ctx.lineWidth=1; ctx.stroke();
  });
  // hover
  cv.addEventListener('mousemove', ev=>{
    const r=cv.getBoundingClientRect();
    const mx=ev.clientX-r.left, my=ev.clientY-r.top;
    let best=-1, bd=1e9;
    DATA.forEach((d,i)=>{ const dx=X(d.start)-mx, dy=Y(accessor(d))-my;
      const dist=dx*dx+dy*dy; if(dist<bd){bd=dist;best=i;} });
    if(best>=0 && bd<400){
      tip.style.display='block';
      tip.style.left=(ev.clientX+14)+'px'; tip.style.top=(ev.clientY+14)+'px';
      tip.textContent=tipText(DATA[best], best);
    } else tip.style.display='none';
  });
  cv.addEventListener('mouseleave', ()=> tip.style.display='none');
}

// top = tool-wait excluded (blue), bottom = tool-wait included (orange). Independent scales.
makeChart('cTop', d=>d.active_excl_sec, C_EXCL, L.chartExcl);
makeChart('cBot', d=>d.active_incl_sec, C_INCL, L.chartIncl);

// table
const tbl = document.getElementById('tbl');
let html = '<tr><th>#</th><th>'+L.hStart+'</th><th>'+L.hIncl+'</th><th>'+L.hExcl+'</th><th>'+L.hWait+'</th>'+
           '<th>'+L.hWall+'</th><th>'+L.hMsgs+'</th><th>'+L.hTools+'</th><th>'+L.hIdle+'</th><th>'+L.hInput+'</th></tr>';
DATA.forEach((d,i)=>{
  html += '<tr><td>'+(i+1)+'</td><td>'+fmtTime(d.start)+'</td>'+
    '<td style="color:'+C_INCL+'">'+fmtDur(d.active_incl_sec)+'</td>'+
    '<td style="color:'+C_EXCL+'">'+fmtDur(d.active_excl_sec)+'</td>'+
    '<td>'+fmtDur(d.toolwait_sec)+'</td>'+
    '<td>'+fmtDur(d.wall_sec)+'</td>'+
    '<td>'+d.n_assistant+'</td><td>'+d.n_tool+'</td>'+
    '<td>'+fmtDur(d.idle_before_sec)+'</td>'+
    '<td class="prompt">'+escapeHtml(d.prompt)+'</td></tr>';
});
tbl.innerHTML = html;
function escapeHtml(s){ return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
</script>
</body>
</html>
"""


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
