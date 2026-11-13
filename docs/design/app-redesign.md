# App redesign: deep dive and plan

Status: plan for approval. No code yet. Audited 2026-11-13 on every screen of the app (light, 1440 × 900,
French), plus the code behind them (loading, motion, keyboard, data).

**Verdict: not approved.** The app is correct (it renders, aligns, uses the tokens) but not crafted.
Five root problems make it read as sparse, flat and slow even though it is technically fast.

---

## 1. The five root problems (blockers)

| # | Problem | Where it shows | Why it costs the user |
|---|---|---|---|
| 1 | **No focal point anywhere.** Page titles are 14 px, the size of a table row. Every screen is a header bar, then grey rows. | All pages | The eye has nowhere to land; nothing says "this is what matters here". |
| 2 | **Space is unplanned, not generous.** Lists stop after 4 rows and leave 650 px blank; settings use 770 px of 1200; the report's right half is empty under one rule; "new workflow" is one input centred in a void. | Workflows, runs, report, settings, new | Feels empty and unfinished, and pushes real content (recent runs, the "next" button) below the fold. |
| 3 | **Extraction is set up blind.** Fields are typed into a spreadsheet; the document is only seen in another tab, and never in the report. | Builder, report | The core job (get the right values out) has no feedback loop. |
| 4 | **The data isn't telling the truth or the story.** Runs "passed" with 0 fields; 14 rows all named "Factures fournisseurs"; "0 exécution · — · Jamais exécuté" says the same thing three times; English descriptions in a French UI. | Runs, workflows, report | The user can't tell items apart or trust a green mark. |
| 5 | **Nothing feels alive.** Motion is used in 4 components only; no list ever animates; no live counts; no keyboard navigation in lists (`j`, arrows and Esc do nothing); the only shortcut is ⌘K. | Everywhere | Fast in milliseconds, slow in feel: every action is a mouse trip with no response. |

---

## 2. Screen by screen

Severity: **B** blocker, **S** should-fix, **N** note.

### App chrome (sidebar, header)
| Sev | Today | Fix |
|---|---|---|
| B | Page header is 44 px with a 14 px title and nothing else; on the builder a "Brouillon" badge floats alone in the middle. | Header carries the page's context: breadcrumb at 13 px, title at 15 px semibold, status badge next to the title, page actions right, view options (filter, display) in the same bar. |
| B | Sidebar: 4 links, then 650 px of nothing. | Sidebar works: an "À examiner" link with a live count; a "Workflows" group listing pinned or recent workflows; a running indicator when runs are in progress; the workspace switcher and user at the bottom. |
| S | "+" next to the logo and "Nouveau workflow" in several headers: two creation buttons, no shortcut shown. | One create action everywhere: `C`, shown in tooltips and the palette. |
| S | Collapsed state, resizing and the sidebar hover peek don't exist. | Collapsible sidebar (`[`), width persisted. |

### Overview (dashboard)
| Sev | Today | Fix |
|---|---|---|
| B | Four equal blocks (to review, 3 KPIs, severity, chart, recent runs); nothing leads. | The page is a **work queue**: "À examiner" leads in a dense list with the failed rule written on each row. The week becomes one compact line of numbers above it. |
| B | Bar chart of 7 days, 140 px tall, grey, mostly empty; "Échecs par gravité" says "none" in a quarter of the width. | The chart becomes a 7-day strip of small bars inside the numbers line, coloured by outcome, and appears only when there's data. Severity is folded into the queue's filters. |
| S | "Aucune exécution en cours · Mis à jour maintenant" as a lonely line. | A live status pill in the header: idle, or "2 en cours" with a pulse, opening the running list. |
| S | Recent runs below the fold, duplicate of the runs page. | Removed from the overview; the runs page is one key away (`G` then `R`). |

### Workflows list
| Sev | Today | Fix |
|---|---|---|
| B | Status shown by an unexplained green dot or dashed circle. | A labelled state (Publié / Brouillon) on hover and in the filter, glyph explained once in the column. |
| B | "0 exécution", "—", "Jamais exécuté": three columns for one fact; "15 exécutions" wraps on two lines. | One "activity" column: a 7-day run sparkline (allowed here: it is the data, not decoration) with the count and pass rate; empty means "Jamais exécuté" once. |
| S | Description in grey after the name, mixed languages. | Name on one line; the documents it reads as small chips ("Constat amiable · Facture garage"), which is what tells workflows apart. |
| S | Checkbox column always visible. | Checkbox appears on hover or with `X`; a selection bar slides up from the bottom with actions. |
| N | 4 rows then empty page. | Fine for a list; the empty space is solved by density elsewhere and a proper empty state when there are none. |

### New workflow
| Sev | Today | Fix |
|---|---|---|
| B | A full page for one input, with a disabled "Publier" and "Enregistrer le brouillon" before anything exists. | A **create dialog** (`C`): name, optional template (Facture, Relevé, Constat, Contrat, Vierge), `⌘↵` to create. It opens straight into the extraction workbench with a sample drop zone. |

### Builder: Documents (becomes Extraction)
| Sev | Today | Fix |
|---|---|---|
| B | No document visible while defining fields. | The **extraction workbench**: sample pages on the left, fields with their extracted values on the right, "Extraire" re-runs the unsaved draft (details in section 4). |
| B | The same truncated placeholder ("De quoi s'agit-il ? Ex. l'identifiant…") in every row. | Empty descriptions show a short "Ajouter une description" in ink-4; the example lives in a tooltip on the column header. A missing value after extraction suggests writing one. |
| S | Three header layers (page title "Documents", lead, then each document's title). | Documents become tabs in a strip with their field counts; one title per screen. |
| S | "Liste" as a checkbox column. | List mode is part of the type picker ("Date", "Liste de dates"), as NuExtract writes it. |
| S | Type select with its chevron 200 px away from its text. | Compact type picker (a combobox with type groups and search), chevron next to the text, icon per type group. |
| S | "Suite : règles" at the bottom of a long page, below the fold. | Steps live in the header (Extraction, Règles, Publier) with completion glyphs; `⌘→` moves on. |

### Builder: Rules
| Sev | Today | Fix |
|---|---|---|
| S | Pickers truncate ("Constat amiable…"), "→ valeur" hangs at the end of the line. | Field pickers show the field name, with its document as a coloured A/B prefix; operator and value on the same line; nothing truncates under 1200 px. |
| S | The expression preview repeats the sentence above it in mono. | The preview shows the rule's **result on the samples** instead (passed or failed, with the values). |
| S | "Un document / Deux documents" switch in the top-right corner. | Chosen by picking the documents (one or two chips); no separate switch. |

### Builder: Test and publish (becomes Publish)
| Sev | Today | Fix |
|---|---|---|
| B | "Publier" exists twice (header and body); "Lancer le test" works with no file ("rules on empty values"). | Testing moves into Extraction and Rules. Publish shows: what changes since the last version, the API key, the code examples, a live test with the real key. |

### Runs list
| Sev | Today | Fix |
|---|---|---|
| B | 14 identical rows ("Factures fournisseurs"). | Each row says what's unique: run id short form, file names, source (API or test), duration, then status and time. |
| B | Runs "Réussie" with "0 champ". | A run with nothing extracted is never green: show a warning glyph, "Aucun champ extrait". (Backend outcome check to confirm.) |
| S | Status column floats in the middle with a 400 px gap before it. | Columns sized to their content, status glyph first, failed rule as text for failures. |
| S | "Workflow" filter looks like a word, not a control. | Filter bar of tokens (Workflow is, Statut is, Date in), added from a "Filtrer" menu or by typing `F`. |
| S | New runs don't appear until refresh. | Rows stream in at the top with a short highlight; running rows show progress inline. |

### Run report
| Sev | Today | Fix |
|---|---|---|
| B | The document is never shown. | Split view: pages on the left (zoom, page switcher), fields and rules on the right. Needs one backend endpoint (section 6). |
| B | Right column holds one rule card and 500 px of nothing; fields list is a tall card. | Rules on top as a compact result list (failures first, expanded), fields below grouped per document; the document fills the other half. |
| S | "1 règles sur 1 respectées · 4 champs · 20.6s · test" packed in grey, raw run id under the title. | A verdict header: big glyph and outcome, then a timing bar (queue, GPU start, extraction, rules) that explains the 20.6 s; run id in a copy chip. |
| S | "Intra-doc" jargon tag; descriptions in English. | "Dans un document" / "Entre deux documents"; descriptions shown as written by the user (the seed data is English: fix the seed). |
| S | No next actions. | Actions: open the workflow at this field, re-run, copy JSON, print, CSV; `←` `→` for previous and next run. |

### Settings
| Sev | Today | Fix |
|---|---|---|
| S | Read-only key/value cards at 770 px, half the page empty. | Two-column settings layout: section nav on the left (Modèle, Limites, Marque, Accès), content on the right. |
| S | "À la demande" next to an empty circle that reads as a radio button. | Model status as a proper badge (Éveillé, En veille, Injoignable) with the last check time and a "Réveiller" action. |
| S | Brand values as raw OKLCH strings. | A live preview of the brand (the site's brand switcher, read-only), values in a copy chip. |
| N | Long inference URL in mono. | Truncate the middle, copy on click. |

---

## 3. The system to fix it

### Density and layout (numbers)
- Rows: lists 36 px (Linear's density), settings rows 40 px, nav 28 px.
- Page padding: 24 px sides on lists (lists bleed edge to edge), 32 px on documents; no `max-width` on lists, 1080 px on reading pages.
- Vertical rhythm: 8 px inside a group, 24 px between groups, 40 px between page sections. No section starts with more than 32 px of empty space above it.
- Split views where the work is two-sided (extraction, report): resizable divider, sizes persisted.
- A detail panel (`Space` to peek) on lists, so a run or workflow opens on the right without leaving the list.

### Type
| Role | Size / weight | Use |
|---|---|---|
| Page title | 15 px / 590 | Header bar |
| Hero number or verdict | 24 px / 590, tracking −0.01em | One per screen, the focal point |
| Section title | 13 px / 590, ink | Group headers |
| Body / rows | 13 px / 400–510 | Everything else |
| Meta | 12 px / 400, ink-3, tabular | Counts, times, ids |
| Mono | 12 px | Field keys, values, code |

Three brightness steps for text in every row (ink, ink-2, ink-3); ink-4 for placeholders only.

### Surfaces and colour (livelier, still one accent)
- Keep the inverted-L chrome and the theme engine.
- Colour by **meaning**, used more: status glyphs everywhere a thing is judged; document chips get a stable hue each (A blue, B violet, from the theme), reused in rules and the report; the accent marks the current step and the selection.
- Status washes (pass, warn, fail) on rows that need attention, not only on glyphs.
- One depth strategy: hairlines at the theme's `line`, shadows only on overlays (menus, dialogs, the selection bar).

### Motion catalog (Motion, `reducedMotion="user"`)
| Moment | Motion | Timing |
|---|---|---|
| List rows enter (first load, new run) | fade + 4 px rise, 20 ms stagger, max 8 rows | 180 ms ease-out |
| New run arrives | row slides in at the top, accent wash fades out | 240 ms + 1.2 s wash |
| Status change (running → passed) | glyph morphs (spin → check), scale 0.8 → 1 | spring, bounce 0, 300 ms |
| Peek / detail panel | slides from the right 12 px + fade | 200 ms |
| Dialog | scale 0.96 → 1 + fade, from the trigger | 200 ms in, 120 ms out |
| Menus, popovers | scale 0.98 from trigger origin | 150 ms |
| Selection bar | rises from the bottom | spring 250 ms |
| Extracted value lands | value fades in, row flashes pass/warn wash | 160 ms + 800 ms wash |
| Tab / step change | shared underline glides (`layoutId`) | 200 ms |
| Numbers change | tick (digits roll) | 300 ms |
| Run timeline, GPU warm-up | kept, already done | — |
Never: animating on keyboard-repeated actions, page-level transitions, anything over 300 ms except washes.

### Speed (feel instant)
- **Keyboard map:** `J`/`K` or arrows to move, `↵` open, `Esc` back, `Space` peek, `X` select, `C` create, `F` filter, `/` search, `G` then `O`/`W`/`R`/`S` to go to a page, `⌘↵` save or run, `?` the shortcut sheet. Shortcuts shown in tooltips and menus.
- **Optimistic writes:** save draft, rename, archive, publish update the UI immediately (React Query `onMutate` with rollback).
- **Prefetch on intent:** hovering a row prefetches its detail; list → detail opens with data already in the cache.
- **Skeletons that match the final layout** (same row heights), shown only after 150 ms so fast loads never flash.
- **Live data:** the runs list and the overview poll while visible (or server-sent events later), and merge new rows without a reload.
- Budget: interaction feedback under 50 ms, navigation under 100 ms on a warm cache, no layout shift.

### States (every component)
Default, hover, active (press 0.97), focus-visible ring, disabled with a reason in a tooltip; loading, empty (one sentence, one action, a shortcut), error (what happened, what to do, retry). Audit list in the implementation checklist.

---

## 4. The extraction workbench

- **Create:** dialog, then the workbench opens with "Déposez un exemple" on the left.
- **Left: the sample.** Pages rendered (PDF via pdf.js, images as is), zoom and page switcher; several samples per document type, switchable, to check the schema generalises. Samples stay in the browser session for the draft (stored with the workflow later if wanted).
- **Right: fields with values.** Row: glyph, key, type, value. Click to expand description and type. `⌘↵` runs "Extraire" on the unsaved draft (the API already accepts a draft `definition` on test runs). Values land with the motion above; stale values (field edited since) dim with a "à réextraire" mark.
- **Guidance:** a missing value turns amber and suggests a description; a value with the wrong shape (date not parsed) says so.
- **Document tabs** with counts; `⌘1..9` to switch.
- **Rules step** reuses the samples: each rule shows passed/failed on them as you write it.
- **Publish step:** diff since last version, key, examples, live test.

## 5. What we take from Linear, and what we don't

Take: dense rows, inverted-L chrome, keyboard everything, peek panel, filter tokens, selection bar, optimistic writes, live updates, motion that confirms rather than decorates, display options per list, a sidebar that works.
Don't take: issue-tracker metaphors (cycles, priorities), Linear's purple, their exact components. The product's own character stays: the status glyph, the document as the centre of attention, the brand engine for each client.

## 6. Backend needs

| Change | For |
|---|---|
| `GET /v1/runs/{run_id}/documents/{document_id}/pages/{n}` (PNG at 170 DPI, same permission as reading the run) | Report split view |
| Run outcome: a run with no field extracted is not "passed" (check current logic) | Truthful lists |
| Timings per step on the run (queue, GPU start, extraction, rules) if not all stored | Timing bar |
| Optional: event stream of run status | Live lists without polling |

## 7. Order of work and done criteria

| Phase | Scope | Done when |
|---|---|---|
| 1 | Foundations: type roles, row density, header bar, sidebar with counts, motion presets, keyboard layer, optimistic mutation helper | Shortcut sheet works on every page; rows 36 px; tokens unchanged |
| 2 | Lists: runs, workflows, overview as work queue, filters, selection bar, peek panel, live rows | No two runs look identical; new runs appear without reload |
| 3 | Extraction workbench, create dialog | A workflow goes from name to first extracted values without leaving the screen |
| 4 | Rules on samples, Publish step | Every rule shows its result on the samples |
| 5 | Report split view (+ backend page endpoint), timing bar | A reviewer checks every value against the page on one screen |
| 6 | Settings, empty and error states, final pass, marketing site screenshots | Every component passes the states checklist |

Each phase: lint, types, unit tests, a browser check in light, dark and phone width, then a commit.
