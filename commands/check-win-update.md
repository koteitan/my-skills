---
description: Check pending Windows Updates and report known issues from X
---

# check-win-update

Check pending Windows Updates on this Windows PC, look up issue reports for each KB on X (Twitter) developer API, and report findings to the chat.

## Workflow

### 1. Get pending Windows Updates

Run the following PowerShell command from WSL2 via `powershell.exe` to query the Windows Update COM API (`Microsoft.Update.Session`):

```bash
powershell.exe -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; \$session = New-Object -ComObject Microsoft.Update.Session; \$searcher = \$session.CreateUpdateSearcher(); \$result = \$searcher.Search('IsInstalled=0 and IsHidden=0'); \$result.Updates | ForEach-Object { [PSCustomObject]@{ Title = \$_.Title; KB = (\$_.KBArticleIDs | ForEach-Object { \"KB\$_\" }) -join ','; SizeMB = [math]::Round(\$_.MaxDownloadSize / 1MB, 1); Downloaded = \$_.IsDownloaded } } | Format-Table -AutoSize"
```

Notes:
- Admin rights are NOT required for searching (only for actual installation).
- The query `IsInstalled=0 and IsHidden=0` filters to "not installed and not hidden". Use `IsInstalled=1` to get installed history instead.
- The `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` part prevents mojibake on Japanese titles.

Parse the output to get a list of `{ Title, KB, SizeMB, Downloaded }` for each pending update.

### 2. Search X (Twitter) for issue reports

For each KB number obtained:
- Search the X developer API for posts mentioning the KB (e.g., `KB5034441`, `KB2267602`).
- Look for keywords indicating issues: `不具合`, `問題`, `bug`, `issue`, `broken`, `failed`, `bsod`, `crash`, etc.
- Collect the most relevant recent posts (top ~5 per KB).

If the X API credentials are not configured, ask the user to provide them or skip this step with a note.

### 3. Report to chat

Output a Markdown report containing:
- A table of pending updates (Title / KB / Size / Downloaded).
- For each KB, a short summary of issue reports found on X (number of relevant posts, representative quotes with dates and links).
- A recommendation: "safe to install" / "wait, multiple issue reports" / "no signal".

### Reference / future enhancement

For periodic checks, the user can run this command on a schedule via `/schedule` (e.g., weekly).
