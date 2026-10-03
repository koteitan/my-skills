[English](README-en.md) | [Japanese](README.md)

# use-fandom

A skill for reading and editing pages and files on Fandom (MediaWiki) sites.

Main uses:
- Creating or updating blog posts and user pages
- Uploading image files
- Reading existing pages

The API base is `https://<wiki>.fandom.com/<lang>/api.php` (e.g. `https://googology.fandom.com/ja/api.php`).

## Creating a bot password

1. Log in to Fandom with your own account.
2. Open `Special:BotPasswords` (e.g. `https://googology.fandom.com/ja/wiki/Special:BotPasswords`).
3. Choose a bot name and create one (e.g. `edit-bot`). The actual login ID is `username@botname` (e.g. `Koteitan@edit-bot`).
4. Keep grants minimal:
   - **Basic rights**
   - **Edit existing pages**
   - **Create, edit, and move pages**
   - **Upload new files** (if uploading images)
   
   Add **Upload, replace, and move files** only when you need to replace existing images. Nothing else — delete / block / protect make leaks far more damaging.
5. Leave **Allowed pages for editing** blank. Restricting it can block file pages and stop uploads.
6. Leave **IP ranges** blank.
7. The password shown right after creation is displayed **only once**. Save it immediately.

## Giving credentials to the agent

### Recommended: environment variables

In the shell that launches Claude Code:

```sh
export FANDOM_BOT_USER='Koteitan@edit-bot'
export FANDOM_BOT_PASSWORD='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

For persistence, put them in `~/.bashrc` (and make sure its permissions are tight, e.g. `chmod 600`).

**Note**: environment variables are readable by other processes of the same user via `/proc/<pid>/environ`. They are not categorically safer than a chmod-600 file.

### Alternative: file

```sh
cat > ~/.fandom-bot <<'EOF'
FANDOM_BOT_USER=Koteitan@edit-bot
FANDOM_BOT_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
chmod 600 ~/.fandom-bot
```

## Sanity check

```sh
curl -s --max-time 20 'https://googology.fandom.com/ja/api.php?action=query&meta=userinfo&format=json' \
  --cookie-jar /tmp/fandom-cookies.txt \
  --cookie /tmp/fandom-cookies.txt
```

When not logged in it returns an anonymous `{"id":0,"name":"<IP>"}`.

See `SKILL.md` for the agent-side procedures.
