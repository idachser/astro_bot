#!/usr/bin/env bash
# Stop (async, asyncRewake): run the suite in the background when python files
# changed. Exit 2 wakes Claude with the failures. The stamp keeps a clean tree
# from re-running the same 12 seconds on every turn; a failing run writes no
# stamp, so it retries until it is green.
set -u

repo="${CLAUDE_PROJECT_DIR:-/home/thinkx/www/astro_bot}"
cd "$repo" || exit 0

changed=$(git status --porcelain -- '*.py')
[ -z "$changed" ] && exit 0

stamp="$repo/.git/claude-hooks/pytest.stamp"
sig=$( { printf '%s\n' "$changed"; git diff HEAD -- '*.py'; } | sha1sum | cut -d' ' -f1)
[ -f "$stamp" ] && [ "$(cat "$stamp")" = "$sig" ] && exit 0

out=$(uv run pytest -q 2>&1)
if [ $? -eq 0 ]; then
    mkdir -p "$(dirname "$stamp")" && printf '%s\n' "$sig" >"$stamp"
    exit 0
fi

printf 'pytest failed:\n%s\n' "$(printf '%s\n' "$out" | tail -40)" >&2
exit 2
