---
name: deploy
description: Ship main to production — show what is going out, push, watch the CI/CD run to the end, and triage a red one. Use when asked to push, deploy or ship, and when asked whether the last deploy landed.
---

# Deploying astro_bot

A push to `main` **is** the deploy. `.github/workflows/ci-cd.yml` runs
flake8 and pytest, and only then SSHes to the server to
`git pull --ff-only && docker compose up -d --build && docker image
prune -f`. The deploy job is gated on `refs/heads/main` and a push
event, so pull requests and feature branches run the tests and stop
there. `concurrency: production` queues a second deploy rather than
running two at once.

## Before the push

1. `git status --porcelain` — uncommitted work does not ship. If the
   tree is dirty, say what is uncommitted instead of pushing around it.
2. `git log --oneline origin/main..HEAD` — show the user what is about
   to go out, always, even for a single commit. If it contains commits
   they have not seen this session, stop and ask before pushing.
3. Check the branch. From anything but `main` the push runs tests and
   deploys nothing; that is a fine thing to do, but say which one it is.

The `pre-push` hook runs flake8 and pytest and denies a red push. Do
not route around it (`--no-verify` is not the tool here anyway — the
hook is on the Bash call, not on git). A red gate means the deploy would
have failed in CI a minute later.

## Push and watch

```bash
git push origin main
```

Then find the run for the commit just pushed and follow it — matching on
the SHA, because the newest run on `main` can still be somebody else's:

```bash
SHA=$(git rev-parse HEAD)
ID=$(gh run list --workflow ci-cd.yml --branch main --limit 20 \
     --json databaseId,headSha --jq \
     ".[] | select(.headSha == \"$SHA\") | .databaseId" | head -1)
gh run watch "$ID" --compact --exit-status
```

The run appears a few seconds after the push; if the id comes back
empty, wait and ask again rather than watching the previous run. A
green run takes about half a minute.

## When it is red

```bash
gh run view "$ID" --log-failed
```

- **Lint or tests red** — CI ran the same gate the hook ran locally, so
  a disagreement is the interesting part: `uv sync --frozen` against a
  stale `uv.lock`, or a test leaning on local time or timezone data.
- **Deploy step red** — not the code. SSH secrets, the server's disk, or
  `git pull --ff-only` refusing because the checkout on the box
  diverged from origin. Nothing here can be fixed by pushing again.
- `gh run rerun "$ID" --failed` retries only the failed jobs, which is
  right for a flaky SSH step and wrong for a real test failure.

## What green proves, and what it does not

Green means the SSH script exited 0: the server pulled and
`docker compose up -d --build` returned. It does **not** mean the bot is
answering. The container can come up and crash-loop, and
`restart: unless-stopped` will keep restarting it — which is exactly why
logging goes to a rotating file under the mounted `./data/` as well as
to stdout, since `docker logs astro-bot` only survives until the next
deploy recreates the container.

There is no SSH access to the server from this repository — the key
lives in GitHub secrets — so confirming the bot itself is out of scope
for this skill. Report "CI green, deploy step succeeded", not "the bot
is running".

## Deploying near the Saturday digest

Safe by design, and worth stating rather than avoiding. The broadcast
fires at `DIGEST_HOUR_UTC` (09:00 UTC) on Saturdays. A redeploy recreates
the container, but the slot marker lives in the mounted `./data/` and
survives it, so a restart after a broadcast stays quiet; a restart that
spans the slot catches up on startup within `DIGEST_CATCHUP_HOURS`.
Never hand-run a digest to "make up" for a deploy — that is the path
that mails every user a second copy.
