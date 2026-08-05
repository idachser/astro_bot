#!/usr/bin/env bash
# PostToolUse(Edit|Write): flake8 on the one file that just changed (~0.2s).
# Exit 2 hands the violations back to Claude instead of leaving them for
# the pre-commit run.
set -u

repo="${CLAUDE_PROJECT_DIR:-/home/thinkx/www/astro_bot}"
file=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')

case "$file" in
    "$repo"/astro_bot/*.py | "$repo"/tests/*.py) ;;
    *) exit 0 ;;
esac

cd "$repo" || exit 0
out=$(uv run flake8 "$file" 2>&1) && exit 0

printf 'flake8:\n%s\n' "$out" >&2
exit 2
