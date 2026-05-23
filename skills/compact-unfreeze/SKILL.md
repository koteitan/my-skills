---
name: compact-unfreeze
description: Before the user runs /compact from the remote client, arm a one-shot Monitor so its firing flushes the post-compact frozen remote input queue
---

# compact-unfreeze

Claude Code's official `/compact` has an intermittent bug: running it from the remote client can freeze the next remote input until the loop is woken (it doesn't happen every time). This skill works around it.

1. `ToolSearch("select:Monitor")` to load the Monitor tool.
2. `Monitor(persistent: false, timeout_ms: 300000, command: "sleep 240; echo fired")` — then tell the user to run `/compact`.
3. When it fires, reply with one line (no tools needed); that flushes the frozen queue.
