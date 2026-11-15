# DESIGN.md — notulen

Direction from the owner (hadad, 2026-11-15): "saya pemakainya, terang hangat / mode dark available."
This is the soul of the design. `antislop` is the filter applied on top of it.

## What this is

A personal work notebook. One reader, the owner, opening it many times a day on a phone at a
desk, in a terminal, or in a meeting. Six kinds of entry: task, tutorial, command, SOP, workflow,
meeting notes. It is a tool, not a product page. Nobody is being persuaded of anything.

## Design Read

> Reading this as: a personal reference notebook for one technical owner, in a warm-paper
> editorial style, dial ENERGY 1 / RHYTHM 2 / MOTION 1.

## Dials

| Dial | Value | Why |
|---|---|---|
| ENERGY | 1 | Opened 20 times a day. A tool that greets you loudly is a tool you resent by Thursday. |
| RHYTHM | 2 | List and detail must feel different, because reading a list and reading one note are different jobs. Within a page the rhythm stays calm. |
| MOTION | 1 | Hover and focus only. Motion in a daily tool is friction, not delight. |

## Identity

**Warm paper, not white.** The surface is a cream paper tone, not `#fff`, because this is a
notebook and screens are already bright enough. Everything is ink on paper: one text colour,
one accent, no gradients anywhere.

**The margin rule.** One motif, repeated: a thin vertical rule on the left edge of the reading
column, the way a ruled notebook has a margin. It appears in the entry body and in the list
gutter. It is the only decoration in the whole interface. Reason: it is the one gesture that
says "notebook" without an illustration, an icon, or a texture.

**Serif for the voice, sans for the controls.** Titles and entry bodies read in a serif; every
control, label and meta line is sans. The split is the point: what you wrote is prose, what you
click is a tool.

## Palette

Two core colours plus one accent, per R-29. Neutrals do not count.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--paper` | `#FBF7F0` | `#17150F` | page surface, warm cream / warm near-black |
| `--ink` | `#2A2622` | `#EDE6DA` | body text |
| `--accent` | `#9C4A1E` | `#E08A5B` | rust. The single accent: links, focus ring, active filter, the margin rule |

Supporting neutrals (not part of the 3): `--ink-soft` for meta text, `--rule` for hairlines,
`--surface` for raised blocks (code, cards).

**Why rust and not blue.** Blue is the default of every tool that never chose a colour. Rust is
the colour of ink that has been on paper a while, and it survives both themes with the same
character. Contrast is checked in both themes at WCAG AA (see the gate report).

## Typography

No web fonts, no CDN, no build step. System stacks only, because this app must load instantly
on a phone with one bar of signal.

- **Prose**: `Charter, "Bitstream Charter", "Sitka Text", Cambria, Georgia, serif`. Reason: a
  notebook is read as prose; Charter and Georgia are the two serifs that are actually present on
  the machines this runs on, and both hold up at 16px on a phone.
- **UI**: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Reason: controls should look
  like the platform, not like the app, so they read as native affordances.
- **Code**: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`. Reason: commands are
  copied character by character; a proportional font is a bug here.

Scale: 16px body, 1.6 line height for prose, 1.45 for UI. Titles step 1.35rem on mobile,
1.6rem on desktop. Nothing below 0.8rem, ever.

## Layout

One column, max 68ch for reading. On desktop the column sits slightly left of centre with the
margin rule visible; on mobile it is full width with 16px gutters. No sidebar, no top-heavy
navigation: a notebook does not need a menu, it needs a search field and a way to add a page.

## What earns its place

Every element must answer "what does this do for someone looking up a command at 23:40".

- **Copy button on every code block.** The single most useful control in a command cheatsheet.
- **Pin.** Three or four entries are opened constantly; they belong at the top.
- **Tag filter.** Tags already existed in v1 and were dead weight without being clickable.
- **Search that ranks.** Title before tags before body.
- **Theme toggle.** Warm light by default, dark for the evening; follows the system until the
  owner chooses, then remembers the choice.

## What does not earn its place

No onboarding, no empty marketing copy, no illustrations, no icons beyond the two or three that
carry a real action, no statistics, no "recently viewed" carousel, no AI anything.

## Rules for whoever builds this

1. Every visual decision above has a one-line reason (R-31). A new decision needs its own line
   added here before it ships.
2. No em dash in UI copy (R-02). Use a comma, a colon, or parentheses.
3. Indonesian UI copy, because the owner reads Indonesian. Code and comments in English.
4. Both themes are first-class. A component that only looks right in one is unfinished.
