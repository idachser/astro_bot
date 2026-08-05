---
name: probe
description: Check how the bot behaves in a specific scenario — a day near a timezone boundary, a rendered message, a digest slot after a restart — without waiting for Saturday or touching the live services. Use before changing timezone, day-window, digest-scheduler or template code, and whenever a claim about behaviour needs proving rather than reasoning about.
---

# Probing a scenario

A probe is a throwaway script that runs the real code against fake
surroundings. It answers "what does it actually do on 29 February in
Kiritimati" in seconds, where reading the code answers it maybe.

It is **not** a test and does not replace one. See "After the probe".

## The one rule that makes stubs work

Every module here imports its collaborators by name:

```python
from astro_bot.services.events import get_events_on_day
```

so the handler holds its **own** reference. Patching
`astro_bot.services.events.get_events_on_day` after that import changes
nothing the handler can see. Always patch the attribute on the module
**under test** — which is why every helper in `tests/harness.py` takes
that module as its first argument.

## The five stand-ins

They live in `tests/harness.py`, are used by the test suite, and import
from the repo root:

```python
from tests.harness import (
    FakeBot,          # Telegram; FakeBot(refuse=True) blocks every send
    event_row,        # one (dt_utc, summary, description, url) row
    frozen_now,       # freeze datetime.now() inside a module
    make_user,        # the dict /start hands to add_user
    serving_events,   # canned events + a record of what was asked
    serving_profile,  # a user profile without a database
    users_db,         # a fresh users table at a temp path
    utc,              # an aware UTC instant
)
```

Skeleton — run from the repo root, never from `tests/`:

```bash
uv run python - <<'PY'
from datetime import date
from tests.harness import event_row, serving_events, serving_profile
from astro_bot.handlers import get_specific_date_event as day_message

with serving_events(day_message, [event_row("2026-07-03T23:30:00+00:00")],
                    attr="get_events_on_day"):
    with serving_profile(day_message, tz="Pacific/Kiritimati"):
        day, msg = day_message.get_day_message(42, lambda today: today)
print(day)
print(msg)
PY
```

For the scheduler, freeze the clock instead:

```python
from astro_bot.handlers import autosend_events as ae
from tests.harness import frozen_now, utc

with frozen_now(ae, utc(2026, 8, 8, 9, 1)):    # Saturday, 09:01 UTC
    print(ae.missed_digest_slot(ae.datetime.now(ae.timezone.utc)))
```

`frozen_now` subclasses datetime and rebinds the module's name. Do not
invent another form: assigning to `datetime.now` raises (the type is
immutable), and a bare object with a `now` breaks every other use of
the name in that module. A probe whose clock stub is subtly wrong
reports green on broken code, which is worse than no probe.

## What is worth probing

- **Day windows.** A local day is a UTC interval spanning two dates, or
  three across a DST shift. Probe the extremes: `Pacific/Kiritimati`
  (UTC+14), `Etc/GMT+12`, a DST weekend, 31 December, 29 February.
- **Rendering.** Empty `url` must render bold, not a broken `<a href>`;
  midnight UTC means date-only; event text needs escaping.
- **Digest slots.** Restart before / at / just after the slot, inside
  and outside the catch-up window, with and without a marker on record,
  and with a window that runs past midnight into Sunday.
- **Outage versus quiet sky.** `None` from the events layer must reach
  the user as "try later", `[]` as "no events". Probe both; they are
  one keystroke apart in a stub and opposite in meaning.

## Keep the probe offline

Fake the events, the profile and the bot. A probe must not call the
live skyevents service, Open-Meteo or Telegram, and must not open the
real database — `users_db(str(tmp / "probe.db"))` or the `db=` override
every service function takes. The running bot holds the production file
open, and `.env` holds a live token.

## After the probe

- **Found a bug** → the scenario becomes a pytest case in `tests/`,
  in the same words the probe asked it. Fix after the test is red.
- **Confirmed a subtlety** that surprised you → also a test. Seven
  sessions of this project re-derived the same day-window and digest
  questions from scratch because the answers stayed in the chat.
- **Answered a passing curiosity** → throw it away.

Probes go in the scratchpad, never in the repository. Nothing under
`tests/` should be a script — that directory is for cases pytest runs.
