#!/usr/bin/env bash
# PreToolUse(Bash): a push to main is a production deploy — CI rebuilds the
# container over SSH. Run the same gate CI runs, locally, and refuse the push
# if it is red. Reuses the Stop-hook stamp so a suite that just passed on an
# unchanged tree is not run twice.
set -u

cmd=$(jq -r '.tool_input.command // empty')
push_re='(^|[|;&(]|[[:space:]])git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push'
[[ $cmd =~ $push_re ]] || exit 0

repo="${CLAUDE_PROJECT_DIR:-/home/thinkx/www/astro_bot}"
cd "$repo" || exit 0

deny() {
    jq -n --arg r "$1" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $r
        }
    }'
    exit 0
}

lint=$(uv run flake8 astro_bot tests 2>&1) || deny "flake8 fails, and CI gates the deploy on it. Fix first:
$lint"

stamp="$repo/.git/claude-hooks/pytest.stamp"
sig=$( { git status --porcelain -- '*.py'; git diff HEAD -- '*.py'; } | sha1sum | cut -d' ' -f1)
if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$sig" ]; then
    out=$(uv run pytest -q 2>&1) || deny "pytest fails, and CI gates the deploy on it. Fix first:
$(printf '%s\n' "$out" | tail -30)"
    mkdir -p "$(dirname "$stamp")" && printf '%s\n' "$sig" >"$stamp"
fi

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$branch" = "main" ]; then
    jq -n '{systemMessage: "Push to main: CI will rebuild and redeploy the bot container on the server. flake8 + pytest are green locally."}'
fi
exit 0
