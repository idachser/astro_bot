#!/usr/bin/env bash
# Notification / Stop / TaskCompleted: desktop notification, so a finished
# background review is not waited on by hand.
set -u

payload=$(cat)
event=$(printf '%s' "$payload" | jq -r '.hook_event_name // "Claude Code"')
body=$(printf '%s' "$payload" | jq -r '.message // .summary // empty')

case "$event" in
    Stop) title="Claude Code — ход завершён" ;;
    TaskCompleted) title="Claude Code — фоновая задача готова" ;;
    *) title="Claude Code" ;;
esac

notify-send --app-name="Claude Code" --expire-time=8000 "$title" "${body:-astro_bot}" 2>/dev/null
exit 0
