# Repody UI 2.0: strategy

A complete rewrite of the web UI. Nothing in the current `components/` or `app/(app)` pages is a
reference for the new design. What stays is the data layer (`lib/api`, `lib/types`, hooks, i18n
plumbing), because it is not UI.

The skills in `.claude/skills/` are the working rules for every session that touches the UI:

| Skill | Source | Used for |
|---|---|---|
| `interface-design` | Dammyjay93 (MIT) | Direction, hierarchy, tokens, states for product UI. Decisions saved in `.interface-design/system.md` |
| `frontend-design` | Anthropic (Apache 2.0) | Typography, anti-template rules, UI writing |
| `better-ui` | Jakub Krehel (MIT) | Exact polish values: radius, shadows, icons, enter/exit |
| `emil-design-eng`, `choreograph` | Emil Kowalski (MIT) | When and how to animate, sequencing |
| `review-animations` | Emil Kowalski (MIT) | Strict motion review before a phase ships |
| `design-review`, `design-deslop` | Dammyjay93 (MIT) | Craft review and AI-slop removal before a phase ships |
| `design:ux-copy`, `design:accessibility-review` | installed plugin | Interface copy, WCAG 2.2 AA audit |

## 1. Who it is for, what they do

The person: a back-office, finance or compliance operator who receives invoices, statements and
forms all day and must decide quickly whether each one is right. A second person, the integrator,
sets up workflows once and wires the API.

The jobs, in order of frequency:

1. **Review** a run: is it passed, what failed, which value is wrong, with the document next to it.
2. **Watch** runs come in: what needs attention now.
3. **Build** a workflow: document types, fields, rules, test with a real file, publish, copy the API call.
4. **Administer**: branding, processing settings, keys.

The interface should feel like a well-kept audit file: calm, exact, dense where the work is, with
every judgement visible. Not a marketing dashboard.

## 2. Design direction: the Linear way of building product UI

The style follows the principles Linear published for its own interface ("How we redesigned the
Linear UI", 2024; "A calmer interface for a product in motion", March 2026), applied to our product
with our own brand. We take the method, not their logo, name or lavender.

**Principles.**

- **Don't compete for attention you haven't earned.** The content area (the run, the workflow) is
  the brightest, sharpest thing on screen. Navigation is a few notches dimmer and recedes once the
  user has arrived. Icons are few, small (14–16px), monochrome, never on coloured tiles.
- **Structure should be felt, not seen.** Few separators, soft low-contrast borders, grouping by
  space and by a quiet surface step rather than by boxes.
- **Hierarchy through brightness, not size.** One UI size (13px) carries most of the interface;
  four ink levels (primary, secondary, tertiary, quaternary) do the ranking.
- **Almost no colour.** Neutral greys, slightly warm. One accent for the primary action, focus,
  selection and the active item. Status colours only where a decision is needed.
- **Dense and aligned.** 28px navigation rows, 32px controls, 36–40px list rows. Labels, icons and
  buttons aligned on both axes.
- **Keyboard first.** ⌘K for everything; shortcuts shown in menus and tooltips.
- **Instant.** Frequent interactions do not animate; motion is reserved for opening, confirming and
  the live run timeline.

**Chrome: the inverted L.** A sidebar on the left and a page header across the top frame the content.
The content sits on its own raised panel with a soft edge; the sidebar shares the canvas colour.

```
┌────────────┬──────────────────────────────────────────────┐
│ ▢ Brand  ⌄ │ Runs  /  Invoice audit           Filter  ⋯   │  header 44px
│ ⌕ Search ⌘K├──────────────────────────────────────────────┤
│            │ ● FAC-2024-001   Invoice audit    Passed  2m │  rows 40px
│ Review     │ ○ FAC-2024-002   Invoice audit    Running    │
│ Runs       │ ✕ STMT-0391      Bank statement   Failed  1h │
│ Workflows  │                                              │
│            │                                              │
│ Settings   │                                              │
│ ◯ Mehdi    │                                              │
└────────────┴──────────────────────────────────────────────┘
  sidebar 232px, dimmer       content panel, brightest
```

**Status glyphs.** Every judged thing (run, rule, field, run step) gets a small 14px status glyph
from one family, in a fixed column: a ring while waiting, a partial ring while running, a filled
circle with a check when passed, a warning mark, a cross when failed. This is where colour lives.

**Type.** Inter Variable with the `cv01` and `ss03` features, optical sizing on (the Display cut
at heading sizes). Weights 400, 510 and 590. Scale: 11 / 12 / 13 (UI base) / 15 / 20 / 24, headings
with slight negative tracking. `tabular-nums` on every number. A brand may change the family.

**Depth.** Surfaces step up in lightness (canvas, panel, raised, overlay); borders are translucent
ink; shadows only under menus, popovers and dialogs. Radius 6px on controls, 8px on panels, 12px on
dialogs.

## 3. White-label theming

Each client gets their own deployment, so a brand is per deployment, not per request.

**The brand is data**, with the same three colour inputs Linear uses for its themes:

```
productName, logo (light, dark), mark/favicon,
base (the neutral, any hue: warm, cool or tinted), accent (one colour),
contrast (30 to 100), radius (0 to 12), font, default mode (light | dark | system)
```

It lives in the database, edited in Settings → Branding by a platform admin with a live preview.
First boot reads defaults from environment variables. Logos go to object storage.

**The engine.** From base, accent and contrast, the server derives every token in OKLCH (the
perceptual successor of the LCH space Linear uses): surface elevations, the four ink levels,
borders, accent steps, focus ring, chart series, for light and dark, and checks contrast: text on
the accent turns black or white to stay at WCAG AA, and an accent too light for links is darkened
for text use only. The result is CSS variables written into `<html>` at server render, so there is
no flash of the default brand. Colour maths uses `culori`.

**The contract.** Components only read semantic tokens, never raw colours:

```
--canvas --surface --surface-raised --overlay --field
--ink --ink-secondary --ink-tertiary --ink-disabled
--line --line-strong --focus
--accent --accent-ink --on-accent --accent-wash
--pass --warn --fail --info  (each with -wash and -ink)
--radius-sm/md/lg  --control-h  --pad
--font-sans --font-display
--duration-instant/fast/base/slow  --ease-out --ease-in-out
```

Tailwind 4 maps them in `@theme`, so `bg-surface text-ink border-line` is the only way to colour
anything. A lint rule bans raw palette classes (`bg-gray-*`, hex values) in components.

**Proof.** Two sample brands (the default and one deliberately different: warm neutrals, square
corners, a green accent, another font) ship in the dev-only design page, and visual checks run
against both.

**The sign-in page is Keycloak's**, the first screen a client's users see. It gets the same brand
through a Keycloakify theme that reads the same tokens.

## 4. Libraries

| Need | Choice | Why |
|---|---|---|
| Components | shadcn/ui (copied in, restyled to the token contract) on Radix primitives | Accessible behaviour solved; the code is ours to restyle; its CSS-variable model is what white-label needs. Current docs checked before Phase 1 |
| Animation | **Motion** (`motion/react`, already installed) | The React standard: springs, layout, `AnimatePresence`, `MotionConfig reducedMotion="user"` |
| Animation recipes | transitions.dev as a reference only | It is a gallery of copy-paste CSS recipes, not a library; its Pro recipes are paid. Its free recipes and its motion-token idea inform ours |
| Tables, long lists | TanStack Table + TanStack Virtual | Sorting, filtering and thousands of rows |
| Command palette | cmdk | Jump anywhere, run any action from the keyboard |
| Toasts, mobile sheets | Sonner, Vaul | Proven, accessible |
| Charts | Recharts, coloured from tokens | Already used; small charts only |
| Colour maths | culori | OKLCH scales and contrast for client accents |
| Theme mode | next-themes | Light, dark, system, no flash |

## 5. Motion principles

From `emil-design-eng`, `better-ui` and `choreograph`:

- Frequent actions are instant: typing, row hover, tab switches, the command palette.
- Feedback for actions: button press scales to 0.96 in 150ms; menus and popovers 150–200ms from
  their trigger; dialogs 200–250ms; exits shorter than entrances.
- Curves: `cubic-bezier(0.23, 1, 0.32, 1)` for entering, never `ease-in`; springs with bounce 0.
- Only `transform` and `opacity` (and `filter` for blur), never `transition: all`.
- One expressive moment per screen, earned: the run timeline and GPU warm-up, a verdict revealed
  when a run finishes, a workflow published.
- `prefers-reduced-motion`: movement drops, opacity cross-fades stay. Motion is never the only cue.
- Motion tokens in CSS, so every duration and curve has one source.

## 6. Information architecture

```
┌──────────┬───────────────────────────────────────────────┐
│ Logo     │  Page title                     ⌘K   Theme  Me │
│          ├───────────────────────────────────────────────┤
│ Review   │                                               │
│ Runs     │   (page)                                      │
│ Workflows│                                               │
│          │                                               │
│ Settings │                                               │
└──────────┴───────────────────────────────────────────────┘
```

- **Review** (home): the queue of runs that need a person, oldest first, with the counts of
  today's runs, pass rate and model status underneath.
- **Runs**: every run, filterable by workflow, verdict, source (API or test) and date.
- **Run report**: three panes. The fields ledger in the centre (tick margin, value, rule notes in
  the margin), the document page on the right, rules on the left. `J`/`K` moves between flagged
  items. Share, print, export.
- **Workflows**: list, then the builder: steps on the left (Documents and fields, Rules, Test,
  Publish), the working area in the centre, a test panel that stays open on the right. Autosave,
  "draft" and "published" always visible.
- **Settings**: Branding, Processing, API access.
- ⌘K everywhere: go to any workflow or run, create a workflow, switch theme.
- Every list and page has its loading, empty and error states, each telling the user what to do next.

## 7. Phases

Each phase ships on its own: tests, lint, `design-review`, `review-animations` and `design-deslop`
pass before the commit, and the old code it replaces is deleted in the same commit.

1. **Foundations.** Token contract, theme engine, brand record (API, database, server render),
   fonts, motion tokens, the base components with all their states, and a dev-only design page
   showing them in both sample brands, light and dark. `.interface-design/system.md` saved.
2. **Shell.** Navigation, header, ⌘K, theme switch, sign-out, error and unauthorized pages.
3. **Runs and the run report.** The highest-value screens for a demo.
4. **Workflow builder.** Documents, fields, rules, test, publish, API panel.
5. **Review home.**
6. **Settings → Branding** with live preview.
7. **Keycloak sign-in theme** (Keycloakify).
8. **Quality pass.** Accessibility audit (axe and `design:accessibility-review`), phone widths,
   worst-case data (long names, empty lists, 99-page documents), French copy, e2e smoke updated.
