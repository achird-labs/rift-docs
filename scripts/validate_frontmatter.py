#!/usr/bin/env python3
"""Front-matter gate for the docs hub — the §6 contract in epic #2.

Every page in `docs/` carries typed front matter. It is the human's TOC metadata *and*
the sole input to the machine layer (#26) and the drift bot (#27), so a page that is
merely *plausible* here is not good enough: the vocabularies are closed sets, and the
component ids are checked against `data/sources.yml` rather than a second hardcoded
list. A `rift_component` this file accepted but `sources.yml` had never heard of would
silently drop the page out of drift detection — it would look watched and be watched by
nothing.

Usage:
    scripts/validate_frontmatter.py [docs-dir]   # default: docs/
    scripts/validate_frontmatter.py --self-test  # prove the checker rejects bad input
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED = (
    "title", "description", "audience", "deployment_mode",
    "language", "rift_component", "tier", "status",
)
# Present-or-absent, but see the iff-rule below.
OPTIONAL = ("upstream", "verified_against")
# MkDocs/Material page directives. Allowed so a page can opt out of chrome without
# widening the schema; they carry no meaning for the machine layer.
PASSTHROUGH = ("hide", "search", "icon", "tags", "template", "subtitle")

LIST_VOCAB = {
    "audience": {"developer", "operator", "evaluator", "contributor"},
    "deployment_mode": {"process", "container", "embedded", "cluster"},
    "language": {"rust", "java", "scala", "node", "go", "any"},
}
SCALAR_VOCAB = {
    "tier": {1, 2, 3},
    "status": {"stable", "beta", "planned"},
}
# `deployment_mode: []` is meaningful (§6: the page is mode-agnostic). The other two
# lists are not allowed to be empty — an audience-less page has no reader.
MAY_BE_EMPTY = {"deployment_mode"}

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# The hub itself. It is a legal `rift_component` (§6) but deliberately absent from
# sources.yml: it has no upstream to pin, so there is nothing for the drift bot to
# watch. It is correspondingly NOT a legal `verified_against` key — a page cannot be
# verified against the repo it lives in.
HUB_COMPONENT = "docs"


def load_sources() -> dict[str, str]:
    """{repo: id} from data/sources.yml — the closed world §6's vocabularies point at.

    Deliberately unguarded: a missing or malformed sources.yml raises and fails the job.
    Degrading to an empty world here would make every `rift_component` invalid (noisy)
    or, worse, every one valid (silent) — neither is a thing a gate may decide on its own.
    """
    path = REPO_ROOT / "data" / "sources.yml"
    sources = yaml.safe_load(path.read_text(encoding="utf-8"))["sources"]
    return {s["repo"]: s["id"] for s in sources}


def validate(path: Path, text: str, repo_to_id: dict[str, str]) -> list[str]:
    ids = set(repo_to_id.values())
    repos = set(repo_to_id)
    m = FRONT_MATTER.match(text)
    if not m:
        return ["no YAML front matter block"]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return [f"front matter is not valid YAML: {exc}"]
    if not isinstance(fm, dict):
        return ["front matter must be a mapping"]

    errors: list[str] = []

    known = set(REQUIRED) | set(OPTIONAL) | set(PASSTHROUGH)
    for key in sorted(set(fm) - known):
        errors.append(f"unknown key `{key}` (schema is closed; see epic #2 §6)")
    for key in REQUIRED:
        if key not in fm:
            errors.append(f"missing required key `{key}`")

    for key in ("title", "description"):
        if key in fm and (not isinstance(fm[key], str) or not fm[key].strip()):
            errors.append(f"`{key}` must be a non-empty string")

    for key, vocab in LIST_VOCAB.items():
        if key not in fm:
            continue
        value = fm[key]
        if not isinstance(value, list):
            errors.append(f"`{key}` must be a list, got {type(value).__name__}")
            continue
        if not value and key not in MAY_BE_EMPTY:
            errors.append(f"`{key}` must not be empty")
        for item in value:
            # Compare as a string, not by set membership: a nested list or mapping is
            # unhashable, and letting that raise would abort the whole sweep at the
            # first bad page instead of reporting it alongside the others.
            if not isinstance(item, str) or item not in vocab:
                errors.append(
                    f"`{key}` value {item!r} is outside the closed vocabulary "
                    f"{sorted(vocab)}")

    for key, vocab in SCALAR_VOCAB.items():
        if key not in fm:
            continue
        value = fm[key]
        # `True == 1` in Python, so `tier: true` would otherwise pass as tier 1.
        if isinstance(value, bool) or not isinstance(value, (int, str)) or value not in vocab:
            errors.append(
                f"`{key}` value {value!r} is outside the closed vocabulary "
                f"{sorted(vocab)}")

    components = ids | {HUB_COMPONENT}
    if "rift_component" in fm:
        component = fm["rift_component"]
        if not isinstance(component, str) or component not in components:
            errors.append(
                f"`rift_component` {component!r} is neither a source id in "
                f"data/sources.yml nor {HUB_COMPONENT!r}; expected one of "
                f"{sorted(components)}")

    # §6: `verified_against` is required whenever `upstream` is present — and is
    # meaningless without it. Either half alone is a drift-detection hole.
    has_upstream = "upstream" in fm
    has_verified = "verified_against" in fm
    if has_upstream and not has_verified:
        errors.append("`upstream` is present but `verified_against` is missing")
    if has_verified and not has_upstream:
        errors.append("`verified_against` is present but `upstream` is missing")

    # Which sources this page actually draws from, by source id — used below to check
    # that the pins name those same sources.
    upstream_ids: set[str] = set()

    if has_upstream:
        entries = fm["upstream"]
        if not isinstance(entries, list) or not entries:
            errors.append("`upstream` must be a non-empty list")
        else:
            for i, entry in enumerate(entries):
                where = f"`upstream[{i}]`"
                if not isinstance(entry, dict):
                    errors.append(f"{where} must be a mapping with `repo` and `paths`")
                    continue
                repo = entry.get("repo")
                if repo is None:
                    errors.append(f"{where} is missing `repo`")
                elif repo not in repos:
                    errors.append(
                        f"{where} repo {repo!r} is not in data/sources.yml")
                else:
                    upstream_ids.add(repo_to_id[repo])
                paths = entry.get("paths")
                if not isinstance(paths, list) or not paths:
                    # §6 calls this the load-bearing field: without per-page paths the
                    # drift bot degrades to a per-repo firehose and gets muted.
                    errors.append(f"{where} needs a non-empty `paths` list")
                elif any(not isinstance(p, str) or not p.strip() for p in paths):
                    errors.append(f"{where} `paths` must be non-empty strings")

    if has_verified:
        pins = fm["verified_against"]
        if not isinstance(pins, dict) or not pins:
            errors.append("`verified_against` must be a non-empty mapping")
        else:
            for key in sorted(set(pins) - ids):
                errors.append(
                    f"`verified_against` key {key!r} is not a source id in "
                    f"data/sources.yml")
            for key, value in pins.items():
                # A bare `no`/`off`/`1.2` in YAML is a bool/float, not a version. Pins
                # are compared as strings by the drift bot, so require one here.
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"`verified_against.{key}` must be a non-empty string naming a "
                        f"release or commit, got {value!r}")
            # Presence alone is not enough. A page that summarises `rift` but pins
            # `rift-go` looks verified and is watched by nothing: changes to the repo it
            # actually draws from never trip the drift bot.
            if upstream_ids:
                for missing in sorted(upstream_ids - set(pins)):
                    errors.append(
                        f"`upstream` draws from {missing!r} but `verified_against` "
                        f"does not pin it")
                for extra in sorted(set(pins) & ids - upstream_ids):
                    errors.append(
                        f"`verified_against` pins {extra!r}, which is not among this "
                        f"page's `upstream` repos")

    return errors


def check_tree(docs_dir: Path) -> int:
    repo_to_id = load_sources()
    pages = sorted(docs_dir.rglob("*.md"))
    if not pages:
        print(f"validate-frontmatter: no Markdown pages found under {docs_dir}",
              file=sys.stderr)
        return 1

    failures = 0
    for page in pages:
        errors = validate(page, page.read_text(encoding="utf-8"), repo_to_id)
        if errors:
            failures += 1
            rel = page.relative_to(docs_dir.parent) if docs_dir.parent in page.parents else page
            print(f"\n{rel}")
            for err in errors:
                print(f"    - {err}")

    if failures:
        print(f"\nvalidate-frontmatter: {failures} of {len(pages)} page(s) have invalid "
              f"front matter (schema: epic #2 §6).")
        return 1
    print(f"validate-frontmatter: OK — {len(pages)} page(s) match the §6 schema.")
    return 0


def self_test() -> int:
    """Prove the checker rejects the shapes it exists to reject."""
    repo_to_id = load_sources()
    good = (
        "---\n"
        "title: 'A page'\n"
        "description: 'Does a thing.'\n"
        "audience: [developer]\n"
        "deployment_mode: []\n"
        "language: [any]\n"
        "rift_component: docs\n"
        "tier: 1\n"
        "status: stable\n"
        "---\n\n# A page\n"
    )
    cases = {
        "no front matter": "# nothing\n",
        "missing key": good.replace("status: stable\n", ""),
        "closed vocabulary": good.replace("audience: [developer]", "audience: [wizard]"),
        "unknown component": good.replace("rift_component: docs", "rift_component: rift-ee"),
        "unknown key": good.replace("tier: 1", "tier: 1\nteir: 2"),
        "upstream without verified_against": good.replace(
            "---\n\n# A page",
            "upstream:\n  - repo: achird-labs/rift\n    paths: [docs/index.md]\n---\n\n# A page"),
        "verified_against without upstream": good.replace(
            "---\n\n# A page", "verified_against:\n  rift: v0.16.0\n---\n\n# A page"),
        "upstream repo not in sources.yml": good.replace(
            "---\n\n# A page",
            "upstream:\n  - repo: achird-labs/rift-ee\n    paths: [README.md]\n"
            "verified_against:\n  rift: v0.16.0\n---\n\n# A page"),
        "upstream without paths": good.replace(
            "---\n\n# A page",
            "upstream:\n  - repo: achird-labs/rift\nverified_against:\n"
            "  rift: v0.16.0\n---\n\n# A page"),
        "verified against the hub itself": good.replace(
            "---\n\n# A page",
            "upstream:\n  - repo: achird-labs/rift\n    paths: [docs/index.md]\n"
            "verified_against:\n  docs: v1\n---\n\n# A page"),
    }
    failed = False
    for why, text in cases.items():
        if not validate(Path("fixture.md"), text, repo_to_id):
            print(f"validate-frontmatter --self-test: FAILED — accepted {why}", file=sys.stderr)
            failed = True
    if validate(Path("fixture.md"), good, repo_to_id):
        print("validate-frontmatter --self-test: FAILED — rejected a valid page", file=sys.stderr)
        failed = True
    if failed:
        return 1
    print(f"validate-frontmatter --self-test: OK — rejects {len(cases)} bad shapes, "
          "accepts a valid page.")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--self-test":
        return self_test()
    docs_dir = Path(argv[0]) if argv else REPO_ROOT / "docs"
    if not docs_dir.is_dir():
        print(f"validate-frontmatter: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1
    return check_tree(docs_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
