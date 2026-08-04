---
title: 'Style guide'
description: 'The writing rules every page on this site follows, each with a worked example.'
audience: [contributor]
deployment_mode: []
language: [any]
rift_component: docs
tier: 1
status: stable
---

# Style guide

This page is for anyone writing or reviewing a page on this site. Read it once before your first
page and skim it before each review; by the end you will know the fourteen rules that apply to
every page here and what each one looks like when followed and when broken.

Assume your reader is trying to get something working, usually under time pressure, often while
annoyed at whatever they are mocking. Every rule below exists to serve that person.

!!! note "About the examples on this page"
    These examples demonstrate the *shape* of each rule. They are not a CLI reference, and
    nothing here has been executed against the pinned engine. Rule 5 applies to the pages you
    write, not to this one: check every command against the real thing before you publish it.

---

## 1. Write in second person, present tense, active voice

Address the reader directly and describe what happens, not what can be caused to happen. Passive
constructions hide *who does what*, which is exactly the information a reader following
instructions needs.

✅ You create an imposter on port 4545, and Rift starts routing matching requests to it.
❌ An imposter can be created on port 4545, after which matching requests will be routed to it.

The tell is a form of "to be" plus a past participle ("is created", "will be routed", "can be
configured"). If you find one, ask who the actor is and put them back in the sentence.

## 2. Open every page with two sentences: who it is for, and what they will have working

The reader has landed here from a search result and needs to know within one breath whether this
is their page. Say who it is for and what they will have at the end — not what the page "covers".

✅ *This page is for developers running Rift in a JUnit 5 test suite. By the end you will have a
mock that starts with your test and shuts down with it, with no ports to manage.*

❌ *This page covers the various options available for integrating Rift with test frameworks and
discusses several approaches.*

The second version tells the reader nothing they can act on, and it takes longer to say it.

## 3. Title pages by task, not by feature

Readers search for what they are trying to do. They do not search for the name of the subsystem
that does it, because they do not know it yet — that is why they are reading.

| ✅ Task title | ❌ Feature title |
|---|---|
| Record real traffic into mocks | Proxy mode |
| Run the same mock in CI and on your laptop | Configuration profiles |
| Make a mock return different responses in sequence | Response cycling |

Feature names still belong in the page — in the body, once, where you explain the mechanism.

## 4. Lead with the runnable thing

Put the shortest command or snippet that does something near the top, then explain it. Lead with
a concept only where the concept is genuinely required to read the code.

✅

````markdown
Start Rift and check it is answering:

```bash
docker run -p 2525:2525 zainalpour/rift-proxy:latest
curl -s http://localhost:2525/imposters
```

An *imposter* is a mock server on a port; a *stub* is one rule inside it.
````

❌ A page that spends four paragraphs on the imposter/stub/predicate model before the reader has
seen anything run.

## 5. Every code sample runs as written

No `...`, no invented flags, no half-configuration. Every sample is executed against the pinned
version before the page merges. A placeholder is allowed only when it is unmistakably a
placeholder and the reader knows what to put there.

✅ `rift-verify --admin-url http://localhost:2525 --timeout 30`
✅ `curl -H "Authorization: Bearer $YOUR_TOKEN" http://localhost:4545/orders`
❌ `rift-verify --admin-url ... # plus any other options you need`

`$YOUR_TOKEN` is fine: nobody will paste it and expect it to work. `...` is not — it looks like
part of the command.

A sample that does not run is worse than no sample: the reader assumes their environment is
broken and starts debugging the wrong thing.

The enforcement for this rule is the code-sample smoke test described in
[Sync policy](sync-policy.md#build-time-gates): tag a block ` ```bash title="verified" ` and CI
runs it against the pinned engine version.

## 6. Use tables for anything comparative

Prose comparisons of more than two options are unreadable. The moment you write "whereas" for the
third time, you want a table.

✅

| Mode | Start-up | Isolation | Survives the test run |
|---|---|---|---|
| Embedded | function call | per-process | no |
| Container | seconds | per-container | yes |

❌ "Embedded mocks start with a function call and are isolated per process but do not survive the
test run, whereas containers take seconds to start and are isolated per container, whereas..."

## 7. Say when *not* to use something

Every mode, feature, and SDK page carries this. It is the fastest trust-builder in the document,
and it is what stops a page from reading as a sales pitch.

✅ *Don't run a cluster if a single node already sustains your load — it usually does, at
20–40k RPS. Clustering buys you HA and horizontal throughput, and costs you an operational
surface you otherwise would not have.*

❌ A page listing only what a feature is good at.

A reader who has been told honestly where something stops working believes you about where it
starts.

## 8. No superlatives in Reference or Concepts

"Blazing", "seamless", "effortless", and bare multipliers belong on the home page and on
comparison pages, where a linked benchmark backs them up. In a predicate reference they are noise
that pushes the actual signature further down the page.

✅ *`matches` compares the request field against a regular expression.*
❌ *`matches` gives you blazing-fast, incredibly flexible regex matching.*

## 9. Give every benchmark number its host and its method

A number without its harness, host, version, and date is not a measurement, it is a claim. Always
cite the conservative figure.

✅ *⟨N⟩ req/s sustained, single node, ⟨host spec⟩, `rift v0.16.0`, `hey -z 60s -c 100`, measured
⟨date⟩.* — every one of those five slots filled in from a real run.

❌ *Up to 250× faster than Mountebank.*

The angle brackets above are placeholders, not a format: substitute the measured values. Do not
copy a number from this page — there isn't one, deliberately.

**Only measured numbers from the core `rift` repository may be cited.** Figures that appear in
RiftCluster documents are design envelopes, not measurements — see the hard rule below.

## 10. Never document an unshipped feature in the neutral voice

If it does not ship, either leave it out or mark the page `status: planned` and put the feature in
a visually distinct admonition. Describing it in the same voice as working features is how a docs
site loses the reader's trust for everything else on it.

✅

````markdown
!!! warning "Planned — not yet shipped"
    Multi-tenant RBAC is designed but not implemented. Nothing in this section works today.
````

❌ *Rift supports per-tenant RBAC policies.* (…for a feature that exists only in an RFC.)

## 11. Deep-link to a specific page, never to a repo root

A link to a repository root makes the reader do the search you already did. Link the page that
answers the sentence you just wrote, and include the anchor when the page is long.

✅ `[the JUnit 5 extension](https://achird-labs.github.io/rift-java/junit5/#lifecycle)`
❌ `[the rift-java repo](https://github.com/achird-labs/rift-java)`

Deep links into per-repo sites are checked in CI, anchors included — see
[Sync policy](sync-policy.md).

## 12. Define each term once, in the glossary, and link it everywhere else

The glossary is the single definition site for Rift vocabulary. Everywhere else, link it. Two
pages that each define "flow state" will disagree within a release.

✅

```markdown
Requests are grouped into a [space](../concepts/glossary.md#space), which is the unit of isolation.
```

❌ A second, slightly different definition of "space" opening your page.

The glossary lands with the Concepts section; until then, define the term inline and move it to the
glossary in the same pull request that creates it.

## 13. Prefer deleting to qualifying

A hedged paragraph that nobody trusts is worse than no paragraph. If you cannot state something
plainly because you are not sure it is true, find out or cut it.

✅ *The link check runs against the built site, not the sources.*
❌ *The link check should generally run against the built site in most configurations, though
behaviour may vary depending on your setup.*

The second sentence costs the reader time and leaves them exactly as uncertain as before.

## 14. Use admonitions sparingly and consistently

!!! note "Not from epic #2 §14"
    Rules 1–13 come from epic #2 §14. This one was added here because rule 10 depends on
    admonitions carrying weight. Raise it on the epic if you disagree — don't quietly drop it.

An admonition is a signal, and signals stop working when everything is one. Use `!!! warning` for
something that will break or mislead, `!!! note` for a genuine aside, and
`!!! warning "Planned — not yet shipped"` for rule 10. If a page has more admonitions than
sections, they have become decoration.

✅ One warning on the page, on the thing that actually bites.
❌ Four consecutive tip boxes containing ordinary prose.

---

## The hard rule: document what ships, not what is designed

This one is not a style preference and it is not negotiable. It bites hardest on RiftCluster
pages, which is why it is stated here in the terms an author will meet it.

RiftCluster is at Phase 1. Its architecture guide, its RFCs, and its console prototype describe a
system **larger than the one that exists**. Copying from them uncritically is the easiest way for
this site to publish something false.

1. **Verify every claim against the code at the pinned commit, not against a chapter.** When a
   chapter and the code disagree, **the code wins.**
2. **Anything not yet shipped is omitted, or marked `status: planned`** and rendered in a distinct
   admonition (rule 10). It never appears in the neutral voice used for working features.
3. **No performance number from any RiftCluster document may appear on this site.** They are
   design envelopes rather than measurements. The only citable benchmarks are the core
   repository's measured ones, with the host and method rule 9 requires.
4. **Features from RFC-002 through RFC-006** — multi-tenancy and RBAC, spec-driven mocking, data
   sources, the web console, MCP — are out of scope. Do not write pages for them.

A docs site that documents unshipped features is worse than no docs at all, because it spends the
trust that makes everything else on the site useful.

## Naming

| Context | Use |
|---|---|
| Product name in prose | **RiftCluster** |
| Repository, `rift_component`, `sources.yml` id | `rift-cluster` |
| Binary and container image | `rift-cluster-server` |

Never "Rift Enterprise", "Rift-EE", "EE", "enterprise edition", or `rift-ee`. Clustering is not a
paid tier: RiftCluster is Apache-2.0, exactly like the core, so no page may carry "Enterprise",
"Pro", "contact sales", or any other commercial framing. The reason to run a cluster is high
availability and horizontal throughput — nothing else.

## Where the rules are enforced

| Rule | Enforced by |
|---|---|
| Front-matter schema and vocabularies | `scripts/validate_frontmatter.py`, in CI |
| Internal links resolve in the built site | `scripts/check-links.py`, in CI |
| Everything else on this page | Human review |

Adding a term to a closed vocabulary means changing `scripts/validate_frontmatter.py` and
[Contributing](contributing.md) in the same pull request. See
[How these docs work](how-these-docs-work.md) for which tier your page belongs to.
