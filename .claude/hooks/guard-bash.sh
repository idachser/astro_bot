#!/usr/bin/env bash
# PreToolUse(Bash): three deterministic denials.
#   1. writes into ../skyevents  - that repo has its own agent, this one reads it at most
#   2. reading .env              - it holds the live TELEGRAM_BOT_TOKEN
#   3. bare `python` / `pip`     - neither exists outside the uv venv
set -u

cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

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

sky="/home/thinkx/www/skyevents"
if [[ $cmd == *"$sky"* ]]; then
    write_verb='(^|[|;&(]|[[:space:]])(rm|mv|cp|touch|mkdir|tee|dd|chmod|chown|truncate|patch|sed[[:space:]]+-i)[[:space:]]'
    git_write="git[[:space:]]+-C[[:space:]]+[\"']?$sky[^[:space:]]*[[:space:]]+(add|commit|checkout|switch|reset|restore|rm|mv|push|merge|rebase|apply|clean|stash)"
    if [[ $cmd =~ $write_verb ]] || [[ $cmd =~ \>[[:space:]]*[\"\']?$sky ]] || [[ $cmd =~ $git_write ]]; then
        deny "skyevents is a separate repo with its own agent — this session only reads it. Do not write to $sky from here."
    fi
fi

env_re='(^|[^[:alnum:]_.-])\.env([^[:alnum:]_.-]|$)'
if [[ $cmd =~ $env_re ]]; then
    read_verb='(^|[|;&(]|[[:space:]])(cat|bat|less|more|head|tail|grep|egrep|fgrep|rg|ag|awk|sed|cut|nl|xxd|od|strings|base64|cp|scp|rsync|tee|source|\.)[[:space:]]'
    if [[ $cmd =~ $read_verb ]] || [[ $cmd =~ git[[:space:]]+add ]]; then
        deny ".env holds the live TELEGRAM_BOT_TOKEN and NASA key — never read it into the transcript or stage it. Read config.py for the variable names instead."
    fi
fi

probe=${cmd//uv run python/}
probe=${probe//uv run pip/}
probe=${probe//uv pip/}
probe=${probe//python3 -m pip/}
py_re='(^|[|;&(]|[[:space:]])python[[:space:]]'
pip_re='(^|[|;&(]|[[:space:]])pip[[:space:]]'
if [[ $probe =~ $py_re ]] && [[ ! $probe =~ python3 ]]; then
    deny "There is no bare 'python' on this machine (exit 127). Use 'uv run python'."
fi
if [[ $probe =~ $pip_re ]]; then
    deny "Use 'uv add <pkg>' for dependencies, or 'uv run pip' — bare pip is outside the venv."
fi

exit 0
