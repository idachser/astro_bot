---
name: plan-md
description: Work with PLAN.md — add an item, open or close a stage, retire something that was dropped, or report what is still open. Use for "занеси в план", "обнови план", "делай этап N", "что осталось в плане". Not for plan mode, which is a different thing entirely.
---

# PLAN.md

The running log of what this bot was going to become, stage by stage,
in Russian. It is not a task tracker: each stage explains **why** the
change was worth making, and the checkboxes are the smallest part of it.
Read the surrounding stages before writing into it — the file argues
with itself across stages (stage 11 defers to 9, 10 fixes what 7 set up)
and a new item has to fit that argument.

## The format, exactly

```markdown
## Этап 12. Короткое название

Абзац о том, зачем это нужно и что сейчас не так. Иногда с примером
в блоке кода — так короче, чем описывать словами.

- [ ] Пункт задачи; продолжение строки — с отступом в шесть пробелов,
      ширина строки около 72 символов.
- [x] Сделанный пункт. Галочка ставится, текст не переписывается.
- [x] (снято на этапе 10) Пункт, который решили не делать. Текст
      остаётся: план — это ещё и история решений.
- Пункт без чекбокса — это заметка или принятая цена, а не задача.
```

Rules that are easy to get wrong:

- **Nothing is deleted.** A dropped item gets `(снято на этапе N)` and
  keeps its text. A stage that turned out wrong gets a later stage
  explaining why, not an edit hiding it.
- **Numbering is continuous** — the next stage is 12. Stages sit in
  order, and `## Риски` stays last in the file.
- **Russian, and the same voice as the rest**: what changes, why it was
  worth it, what it costs. Identifiers in backticks.
- The title at the top still names the very first migration. Leave it;
  it dates the file rather than describing it.

## The four things asked of it

**"Занеси в план"** — a new item, or a new stage when the thing has its
own reason to exist. Put it in the stage it belongs to; if it touches
another stage's decision, say so in the text the way stage 11 does
("Учесть при выборе варианта этапа 9"). Planning is its own commit —
`plan the user-timezone weekly digest question`, `planned skyevents api
integration` — with no code in it.

**"Делай этап N"** — read the whole stage first, then check the code
before writing any: items are sometimes already true, and the plan does
not always know. Tick the boxes **in the same commit as the code that
earns them** (`weather footers with observing conditions on event
messages` ticked six). Never tick from the plan's own description.

**"Что осталось"** — `grep -n '^- \[ \]' PLAN.md`, then read each in its
stage. An open box is not always work waiting: some are deliberately
deferred (`lang=ru`, the visibility filter) and say so in their text.

**"Обнови план"** — reconcile with the code. The two drift: commits
`read events live from the skyevents api` and `switch event source to
the skyevents API` both shipped without touching PLAN.md. Right now
stage 11 is written and none of it is built — `templates.py`
`WEEK_DIGEST_MESSAGE` still walks the event list, not the seven days of
the window. Check before ticking; a tick that is not true in the code is
worse than an unticked box.

## What does not go here

Bugs and review findings go to `/code-review` and to commits, not into
PLAN.md — the file is about intended direction. Architecture that is
already true lives in CLAUDE.md instead: PLAN.md says what will be done
and why it was chosen, CLAUDE.md says how it works now and what must not
be broken.
