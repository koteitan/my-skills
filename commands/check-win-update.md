---
description: Check pending Windows Updates and report known issues from X and Web search
---

# check-win-update

Check pending Windows Updates on this Windows PC, look up issue reports for each KB, and report findings to the chat.

Issue lookup **always** runs Web search. When `CHECK_WIN_UPDATE_CLIENT_ID` is also configured, the X (Twitter) developer API is queried in addition to (not instead of) Web search, and findings from both sources are merged.

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

### 2. Look up issue reports for each KB

Always run **Web search** (section 2b). **Additionally**, if `CHECK_WIN_UPDATE_CLIENT_ID` is set AND `~/.config/check-win-update/token.json` exists, also run the **X API** path (section 2a) and merge the findings. Do NOT prompt the user to set up the X API when it is missing — just skip 2a silently and note in the report that only Web search was used.

#### 2a. X (Twitter) API path (optional, runs when configured)

For each KB number obtained, query `https://api.twitter.com/2/tweets/search/recent` with:

- Query: just the KB number (e.g., `KB5034441 lang:ja -is:retweet`). Do **NOT** pre-filter by issue keywords; X's full-text search misses common Japanese complaint phrases ("起動しない", "固まる", "重い", etc.) when AND'd with a narrow keyword list.
- `max_results=20`, `tweet.fields=created_at,public_metrics`.
- Auth: `Authorization: Bearer <access_token>` from `~/.config/check-win-update/token.json`.

If the access token is expired (HTTP 401), refresh it using the saved `refresh_token` against `https://api.twitter.com/2/oauth2/token` with `grant_type=refresh_token` and `client_id=$CHECK_WIN_UPDATE_CLIENT_ID`, then save the new token back.

After fetching, **read each tweet** and classify it as one of:
- `informational` — news / announcement / "I installed it" without symptoms
- `issue` — concrete failure ("Win+F11 が反応しない", "固まる", "BSOD", etc.)
- `unrelated` — coincidental KB mention

Only the `issue` ones count toward the recommendation.

#### 2b. Web search (always)

Use the WebSearch tool with queries such as:

- `KB<number> 不具合` (Japanese)
- `KB<number> issue OR bug OR broken site:reddit.com OR site:bleepingcomputer.com OR site:windowslatest.com`
- `site:support.microsoft.com KB<number>` (official "Known issues" section)

Read the top results and summarize the same way (informational / issue / unrelated).

### 3. Report to chat

Output a Markdown report containing:

- A table of pending updates (Title / KB / Size / Downloaded).
- For each KB:
  - Sources used (`Web search`, plus `X API` if configured)
  - Count of `issue` findings (combined; mark each quote with its source)
  - 2–3 representative quotes per source (date / link / short excerpt)
- A per-KB recommendation derived from the merged `issue` count: `safe to install` / `wait, multiple issue reports` / `no signal`.
- A bottom note if X API was skipped: `Note: X API not configured — Web search only`.

### Reference / future enhancement

For periodic checks, the user can run this command on a schedule via `/schedule` (e.g., weekly).

### Auth setup (one-time, optional)

If the user wants the X API path, the one-time setup is:

1. Register an app on https://developer.x.com (Native App / Public client, OAuth 2.0, Read scope is enough; Pay-Per-Use Credits enabled). Set Callback URI to `http://localhost:8765/callback` and Website URL to any public URL.
2. Export the Client ID: `export CHECK_WIN_UPDATE_CLIENT_ID="..."` in `~/.bashrc`.
3. Run the OAuth 2.0 PKCE flow once (verifier/challenge → browser authorize → paste back the redirected URL → token exchange) and save the resulting tokens to `~/.config/check-win-update/token.json` with `chmod 600`. Subsequent runs use the saved refresh token.
