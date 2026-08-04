---
title: 'Sync policy & drift budget'
description: 'How pages that summarise upstream repositories are kept true, and what happens when they go stale.'
audience: [contributor]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Sync policy & drift budget

This page is for anyone maintaining a page that summarises an upstream repository, and for anyone
wondering why a page is showing a "last verified" stamp. By the end you will know how this site
tracks the six upstream repositories, what obligation a `verified_against` pin creates, and when a
page is declared stale.

Nothing described here copies content. Every mechanism below exists to tell a human *what to look
at*, and none of them edit a page.

## `data/sources.yml` — the pinned world

`data/sources.yml` records each source repository and the exact revision this site's pages were
last reconciled against. It pins all six: `rift`, `rift-cluster`, `rift-node`, `rift-java`,
`rift-scala`, and `rift-go`.

```yaml
- id: rift
  repo: achird-labs/rift
  site: https://achird-labs.github.io/rift/
  pinned: { release: v0.16.0, commit: 1e400ba…, date: 2026-07-30 }
  watch: [docs/, README.md, CHANGELOG.md]
```

- `watch` lists the paths whose changes could invalidate a page here.
- `pinned` is the revision the reconciliation was done against.
- `rift-cluster` additionally carries `private: true` and `site: null` while its repository is
  private.

This file is not a passive record. `scripts/validate_frontmatter.py` reads it as the closed world
for `rift_component` (plus the hub's own `docs`, which has no upstream to pin), for every
`upstream[].repo`, and for every `verified_against` key — so a page cannot claim an upstream that
this file has never heard of.

> **Bump `pinned` only in a pull request that also updates the affected pages'
> `verified_against`.** A bumped pin with unchanged pages asserts a reconciliation that nobody did,
> and it resets the staleness clock on work that was never performed.

## `verified_against` — the per-page pin

A tier-2 page declares both which upstream files it summarises and which revision it was checked
against:

```yaml
upstream:
  - repo: achird-labs/rift-cluster
    paths:
      - docs/architecture/02-topology.md
      - docs/architecture/10-operations.md
verified_against:
  rift-cluster: 4911edc
```

`upstream.paths` is the load-bearing field. It is what turns *"someone changed
`docs/architecture/10-operations.md` upstream"* into *"therefore `run/cluster.md` needs a human
look"*. Without per-page paths, drift detection degrades into a per-repository firehose and gets
muted within a month.

Be specific. List the actual files a page summarises, and include source paths — a CLI definition
module, for instance — wherever a page documents behaviour that is defined in code rather than in
prose.

The validator enforces two cross-field rules here — the pairing rule and the key-matching rule.
Both are specified in [Contributing](contributing.md#optional-fields-but-only-as-a-pair); the point
for this page is *why* they exist. Presence alone would let a page look verified while being
watched by nothing, which is worse than a page that is openly unverified: it consumes the drift
budget without ever spending it.

## Drift detection

A scheduled job runs weekly, and on demand. For each source it diffs the `watch` paths from
`pinned.commit` to `HEAD`, then joins the changed upstream paths against every page's
`upstream.paths`.

It maintains **one** issue — created once and updated in place, never one per run — titled:

> `Docs drift: N upstream changes affect M hub pages`

The body groups by hub page, not by repository, because the unit of work is a page:

```md
### `run/cluster.md`   (verified against rift-cluster 4911edc)
3 upstream commits touch its sources:
- rift-cluster `docs/architecture/10-operations.md` — a1b2c3d "Add rolling-upgrade runbook"
- rift-cluster `deploy/k8s/`                        — d4e5f6a "Bump StatefulSet probes"
→ review, then bump `verified_against.rift-cluster` in the same PR.
```

While `rift-cluster` is private, the job needs a token with read access to it. If that token is
unavailable the job **skips that source with a logged warning** — it does not fail the workflow,
and it does not silently pass. A skipped source that reports success is a source nobody is
watching.

## The staleness budget

A page is **stale** when its `verified_against` trails the current release by **more than one
minor version**, or by **more than 90 days**, whichever comes first.

| State | What happens |
|---|---|
| Within budget | Nothing. The page carries its verified-against stamp. |
| Stale | The drift issue is labelled `stale-docs`, and the page renders a visible "Last verified against `vX.Y.Z`" admonition. |

The visible stamp is deliberate. Readers deserve to know how fresh a page is, and a silently stale
page is worse than a visibly dated one: it spends trust it has not earned. The stamp is also the
cheapest possible pressure to keep pins current, because it is the author's own page that wears it.

Being stale is not a build failure. Blocking every unrelated pull request on an unreconciled page
would only teach people to bump pins without reading, which is the exact outcome the budget exists
to prevent.

## Build-time gates

These run on every pull request:

1. **Front-matter validation** — the schema and its closed vocabularies, plus the two
   `verified_against` rules above.
2. **Internal link check** — against the **built** site, not the sources.
3. **Generated-file freshness** — regenerate the tier-3 files and fail on any diff.
4. **Tier-2 length cap** — fail any `tier: 2` page over 400 lines.
5. **Code-sample smoke test** — every fenced block tagged ` ```bash title="verified" ` runs in CI
   against the pinned engine version. This is the enforcement behind style rule 5, so tag the
   blocks you want checked; an untagged block is trusted, and trust is what goes stale.

And nightly, as a hard gate:

6. **External link check** — every deep link into a per-repository site resolves, anchors included.
   Upstream heading renames are the most common way these rot. It runs nightly rather than
   per-pull-request because network flake should not block a merge, and it is a hard gate rather
   than a warning because a rotted deep link is invisible to everyone except the reader who
   follows it.

Gates 1 and 2 are in place today. Gates 3–6 arrive with the issues that introduce the content they
govern.

## When you change an upstream repository

If you have just changed something a page here summarises:

1. Find the affected pages — search the `upstream.paths` values for the file you touched.
2. Update those pages.
3. Bump their `verified_against`, and `data/sources.yml` if you are moving the pin, in the same
   pull request.

Doing it in one pull request is the whole discipline. Split across two, the second one does not
happen.

## Related

- [Contributing](contributing.md) — the front-matter fields, in full.
- [How these docs work](how-these-docs-work.md) — which tier owes a `verified_against` at all.
