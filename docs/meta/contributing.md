---
title: 'Contributing'
description: 'Add a page to this site: the front-matter contract field by field, and how to run every gate locally.'
audience: [contributor]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Contributing

This page is for anyone adding or editing a page on this site. By the end you will have the site
building locally, know every front-matter field and the exact values each one accepts, and be able
to run the same gates CI runs before you open a pull request.

Read [How these docs work](how-these-docs-work.md) first if you are not sure which tier your page
belongs to — the tier decides which fields you owe.

## Build it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

`mkdocs serve` gives you live reload on <http://127.0.0.1:8000/>. Before opening a pull request,
run the gates exactly as CI does:

```bash
python scripts/validate_frontmatter.py --self-test   # the gate still gates
python scripts/check-links.py --self-test
python scripts/validate_frontmatter.py               # every page's front matter
mkdocs build --strict                                # nav, references, anchors
python scripts/check-links.py site                   # links in the BUILT site
```

The link check needs `mkdocs build` to have run first — it reads `site/`, not `docs/`. A missing or
empty build directory fails loudly rather than reporting that zero pages had zero broken links. It
cannot detect a *stale* build, though, so run `mkdocs build` before it rather than trusting
yesterday's `site/`.

## Add a page

1. Create the file under the right section of `docs/`.
2. Add the front-matter block below.
3. **Add it to `nav:` in `mkdocs.yml`.** A page that is not in the navigation fails
   `mkdocs build --strict`, because an unreachable page is not a published page.
4. Run the gates above.

## The front-matter contract

Every page carries this block. It is the site's table-of-contents metadata *and* the sole input to
the machine-readable layer and the drift bot, so it is validated in CI: a missing or invalid field
fails the build.

```yaml
---
title: Run a Rift cluster
description: Stand up a self-hosted, highly-available Rift cluster and know what it guarantees.
audience: [operator]
deployment_mode: [cluster]
language: [any]
rift_component: rift-cluster
tier: 2
status: stable
upstream:
  - repo: achird-labs/rift-cluster
    paths:
      - docs/architecture/02-topology.md
verified_against:
  rift-cluster: 4911edc
---
```

### Required fields

| Field | Type | Accepts |
|---|---|---|
| `title` | string | Non-empty. Titled by task, not by feature — see the [style guide](style-guide.md). |
| `description` | string | Non-empty. One sentence; it is what the machine layer publishes for this page. |
| `audience` | list | One or more of `developer`, `operator`, `evaluator`, `contributor`. Must not be empty. |
| `deployment_mode` | list | Any of `process`, `container`, `embedded`, `cluster`. **May be empty** (`[]`) when the page is mode-agnostic. |
| `language` | list | One or more of `rust`, `java`, `scala`, `node`, `go`, `any`. Must not be empty. |
| `rift_component` | string | `rift`, `rift-cluster`, `rift-node`, `rift-java`, `rift-scala`, `rift-go`, or `docs`. |
| `tier` | integer | `1`, `2`, or `3`. See [How these docs work](how-these-docs-work.md). |
| `status` | string | `stable`, `beta`, or `planned`. |

These vocabularies are **closed sets**. Adding a term means editing
`scripts/validate_frontmatter.py` and this table in the same pull request — otherwise the prose and
the enforcement disagree, and only one of them is real.

`rift_component` takes its values from the `id` fields in `data/sources.yml`, plus `docs`. Use
`docs` for pages this site owns outright: the hub has no upstream to pin, which is exactly why
`docs` is a valid component and is *not* a valid `verified_against` key.

`status: planned` is not decoration. A page describing something that does not ship yet must carry
it, and must put the unshipped part in a distinct admonition — see the hard rule in the
[style guide](style-guide.md#the-hard-rule-document-what-ships-not-what-is-designed).

### Optional fields — but only as a pair

| Field | Type | Accepts |
|---|---|---|
| `upstream` | list | Entries of `{repo, paths}`. `repo` must appear in `data/sources.yml`; `paths` must be a non-empty list of file paths. |
| `verified_against` | mapping | Source `id` → the release or commit the page was checked against, **as a quoted string**. |

**`verified_against` must be present if and only if `upstream` is present.** Neither half means
anything alone, and the validator rejects either one on its own. The keys must also name the same
sources `upstream` draws from — pinning `rift-go` on a page that summarises `rift` looks verified
and is watched by nothing.

!!! warning "Quote the pin"
    The validator requires a non-empty **string**. An all-digit short SHA (`4911111`) or a
    `1.2`-style release parses as a number in YAML and is rejected. Write `rift: "4911111"`.
    A SHA containing a letter survives unquoted, which is exactly why this bites intermittently.

Most tier-1 pages have neither, but a tier-1 page that does summarise upstream files declares both.
Tier-2 pages always have both. See [Sync policy](sync-policy.md) for the obligation a pin creates.

### Fields the theme may add

`hide`, `search`, `icon`, `tags`, `template`, and `subtitle` are passed through for MkDocs Material
page directives. Everything else is rejected: the schema is closed at the top level, so a typo like
`teir: 2` is a build failure rather than a field silently ignored.

## Writing the page

Follow the [style guide](style-guide.md) — all fourteen rules, plus the hard rule about
documenting only what ships. The two that get missed most often:

- Open with two sentences saying who the page is for and what they will have working.
- Say when *not* to use the thing.

## Opening the pull request

- One logical change per pull request.
- Conventional-commit subject line, imperative mood: `docs: add the cluster operations page`.
- If you touched anything upstream summarises, bump `verified_against` in the same pull request.
- If you added a vocabulary term, the validator change belongs in the same pull request as this
  table.

CI runs the gates listed above on every pull request and again before the site deploys. A red gate
is a blocked merge, not a warning.
