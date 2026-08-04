---
title: 'How these docs work'
description: 'The three content tiers, what each one owns, and why a page that grows past its tier is a bug.'
audience: [contributor]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# How these docs work

This page is for anyone adding a page to this site or wondering why an existing one stops where it
does. By the end you will know which of the three tiers your page belongs to, what that tier
permits, and why the boundaries are enforced rather than suggested.

Rift is six repositories, each with its own documentation site. This site is the front door to all
of them. The difficult part is not writing pages — it is making sure they are still true in six
months, and every rule below follows from that.

## What this site owns, and what it does not

This hub **complements** the per-repository sites; it does not absorb them.

| This site owns | Each SDK site owns |
|---|---|
| Concepts and the mental model | Its own API surface |
| The decision guide: which shape of Rift do you want | Its language's full reference |
| Deployment and operations | Its release notes |
| Cross-language guides | Its own examples |

If a page here is a copy of a page there, it is wrong. Every page that summarises an upstream
surface deep-links to it and stops.

## The three tiers

**Every page declares exactly one tier in its front matter.** The tier determines how the page is
written and how it is kept honest. This is the mechanism that makes "single source of truth" and
"don't blindly inline upstream" compatible instead of contradictory.

### Tier 1 — owned here, canonical here

Cross-cutting content with no natural home in any single repository. It is about *concepts and
decisions*, not APIs, so upstream code changes rarely invalidate it.

**Covers:** `Start`, `Concepts`, `Compare`, `Guides`, `run/index.md`, `embed/index.md`, `Meta`.

**Rules:** written fresh, at full depth. Most tier-1 pages have no upstream at all and so omit
`upstream:` — but a tier-1 page that *does* summarise upstream files declares them like any other,
and owes a `verified_against` for them. This is where the hub earns its existence: a tier-1 page
that just links elsewhere is a wasted page.

### Tier 2 — summary here, depth upstream

Per-SDK and per-feature landing pages. Each gives **install → a 20-line hello world → a capability
table → "going deeper" links**, and then *stops*.

**Covers:** `Embed/*` language pages, `Run/*`, the narrative `Reference/*` pages.

**Rules, non-negotiable:**

- **Hard cap: 400 lines.** If a page wants to be longer, the extra belongs upstream.
- Every code sample must be runnable as written and must have been executed against the pinned
  version.
- Never restate a full API surface. Link the SDK site for that.
- End with a **Going deeper** block linking upstream.
- Declare `upstream:` and `verified_against:` in the front matter.

#### Why 400 lines, specifically

The number matters less than the ceiling existing. A short page that links out stays correct
because it repeats almost nothing; a long page that duplicates an upstream API surface goes stale
the moment upstream changes, and nobody notices, because the page still *reads* fine. The cap is
the cheapest available proxy for "this page has started duplicating instead of summarising".

When you hit the cap, the fix is never to trim wording. It is to find the part that belongs
upstream and link to it instead.

### Tier 3 — generated, never hand-edited

Anything that is a matrix over versions, features, or SDKs. Hand-maintaining these guarantees
silent drift, because the update is always someone's second task.

**Covers:** `reference/feature-matrix.md`, `reference/compatibility.md`, and every release-version
mention.

**Rules:** produced by a generator from `data/sources.yml` plus upstream release metadata. CI fails
if the committed output differs from a fresh run. These files carry a
`<!-- GENERATED — do not edit -->` header. If you edit one by hand, CI will revert your work by
failing the build, which is the intended outcome.

### The rule that ties the three together

> **If a fact appears in two places, one of them must be generated.**

That is the whole design. Everything above is a consequence of it.

## How a reader moves through the site

The navigation is organised by what a reader is trying to do, not by which repository the answer
lives in:

| Section | The reader's question |
|---|---|
| **Start** | What is this, and which shape of it do I want? |
| **Concepts** | How does Rift think about mocking? |
| **Run** | I want a server. How do I operate one? |
| **Embed** | I want a library in my language. |
| **Guides** | How do I do *X* — across languages? |
| **Reference** | What exactly does this field accept? |
| **Compare** | Should I use this instead of what I have? |

A section is added to the navigation only when its pages exist. There are no placeholder pages on
this site: an empty page that promises content is a broken promise with a URL.

## What CI enforces

| Gate | What it checks |
|---|---|
| `scripts/validate_frontmatter.py` | The front-matter schema and its closed vocabularies |
| `mkdocs build --strict` | Broken internal references, pages missing from the navigation |
| `scripts/check-links.py` | Every internal link resolves **in the built site** |

The link check runs against the built output rather than the sources on purpose. A link and a file
layout can each be perfectly well-formed and still not meet — that failure mode is invisible until
the site is built, and it is how 156 dead links once shipped upstream.

## Where to go next

- [Contributing](contributing.md) — the front-matter contract, field by field, and how to add a page.
- [Style guide](style-guide.md) — how to write the prose itself.
- [Sync policy](sync-policy.md) — how tier-2 pages are kept true as upstream moves.
