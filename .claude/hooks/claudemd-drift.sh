#!/usr/bin/env bash
# Stop: CLAUDE.md is this project's real documentation — every architectural
# decision lives there. Say so once per distinct set of touched files when the
# code moved and the doc did not. Advisory only.
set -u

repo="${CLAUDE_PROJECT_DIR:-/home/thinkx/www/astro_bot}"
cd "$repo" || exit 0

code=$(git status --porcelain -- 'astro_bot/*.py')
[ -z "$code" ] && exit 0
git status --porcelain -- CLAUDE.md | grep -q . && exit 0

stamp="$repo/.git/claude-hooks/claudemd.stamp"
sig=$(printf '%s\n' "$code" | sha1sum | cut -d' ' -f1)
[ -f "$stamp" ] && [ "$(cat "$stamp")" = "$sig" ] && exit 0
mkdir -p "$(dirname "$stamp")" && printf '%s\n' "$sig" >"$stamp"

files=$(printf '%s\n' "$code" | awk '{print $NF}' | paste -sd' ')
jq -n --arg f "$files" '{
    systemMessage: ("Changed without touching CLAUDE.md: " + $f)
}'
