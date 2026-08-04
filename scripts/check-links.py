#!/usr/bin/env python3
"""Docs internal-link gate — ported from `rift/scripts/verify-docs-links.sh`.

Resolves every internal link in the *built* site the way GitHub Pages actually serves it,
and fails if any of them would 404.

Checking the **sources** does not catch this class of bug, and that is the whole reason
this runs against `site/`. Upstream, the engine's docs shipped with 156 dead
cross-references: the generator emitted `features/spaces.html` while every hand-written
link pointed at `features/spaces/`. Both halves are individually well-formed — the bug
exists only in the *relationship* between the authored URL and the file layout the
generator produced, which is invisible until the site is built. The theme's own
navigation is generated from the page objects, so it stayed correct and the site looked
navigable; only links a human wrote were broken.

Pages' resolution rules, which this reproduces:
  - `/path/`      -> requires `path/index.html`
  - `/path`       -> `path`, `path.html`, or `path/index.html` (the last via a 301)
  - `/path.html`  -> requires that exact file

Scope: internal links only. External URLs are not fetched (flaky, and the nightly
external-link gate in #27 owns them), and `#fragment` targets are not resolved — this
catches dead *pages*, not dead anchors.

Usage:
    scripts/check-links.py [site-dir]     # check a built site (default: site/)
    scripts/check-links.py --self-test    # prove the checker flags the known layout
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.I)
SITE_URL = re.compile(r"^site_url:\s*(\S+)", re.M)

# Attributes that point at a resource we can resolve on disk. `meta` is not optional
# decoration: the legacy-URL stubs in `docs/posts/*.html` carry their real target in
# `<meta http-equiv="refresh">`, so leaving it out would let the one artifact whose
# entire job is URL preservation rot without tripping this gate.
LINK_ATTRS = {"a": "href", "link": "href", "img": "src", "script": "src",
              "iframe": "src", "source": "src", "embed": "src"}
META_REFRESH = re.compile(r"^\s*\d+\s*;\s*url=(.+)$", re.I)


def site_url() -> tuple[str, str]:
    """(origin, baseurl) from `site_url` — how Pages actually serves this site."""
    match = SITE_URL.search((REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    if not match:
        print("check-links: warning — no `site_url:` in mkdocs.yml; absolute links "
              "cannot be resolved against a baseurl.", file=sys.stderr)
        return "", ""
    parsed = urlparse(match.group(1).strip("'\""))
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
    return origin, parsed.path.rstrip("/")


class Links(HTMLParser):
    """Collect link targets. Regex over HTML misses attribute-quoting edge cases."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        attr = LINK_ATTRS.get(tag)
        if attr and values.get(attr):
            self.found.append(values[attr])
        if tag == "meta" and (values.get("http-equiv") or "").lower() == "refresh":
            match = META_REFRESH.match(values.get("content") or "")
            if match:
                self.found.append(match.group(1).strip("'\" "))


def resolves(site: Path, path: str) -> bool:
    """Does `path` (site-root-relative, baseurl already stripped) resolve on Pages?"""
    # `normpath`, not `resolve()`: Pages collapses `..` lexically and never follows
    # symlinks, so resolving them first would report a false 404 for a symlinked
    # directory that serves perfectly well.
    target = Path(os.path.normpath(site / path.lstrip("/")))
    # A link that escapes the site root can never resolve.
    if target != site and site not in target.parents:
        return False
    if path.endswith("/"):
        # A trailing slash is served *only* by a directory index. This is the failure
        # mode above: `features/spaces.html` exists but `features/spaces/` is a 404.
        return (target / "index.html").is_file()
    return (
        target.is_file()
        or target.with_name(target.name + ".html").is_file()
        or (target / "index.html").is_file()
    )


def check_site(site_dir: Path, baseurl: str, origin: str = "") -> int:
    site = site_dir.resolve()
    if not site.is_dir():
        print(f"check-links: site dir not found: {site}\n"
              f"Build it first: mkdocs build --strict", file=sys.stderr)
        return 1

    # Internal means this origin AND this baseurl. On GitHub Pages every sibling project
    # shares the origin — `https://achird-labs.github.io/rift/` is the engine's site, not
    # ours — so matching on origin alone would report every deep link into a per-repo site
    # as a broken internal link.
    site_prefix = f"{origin}{baseurl}" if origin else ""

    broken: list[tuple[str, str, str]] = []
    pages = 0
    for page in sorted(site.rglob("*.html")):
        pages += 1
        # The URL this file is served at, so relative links resolve from the right place.
        page_url = "/" + page.relative_to(site).as_posix()

        parser = Links()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            # Fail closed: a page this gate cannot read is a page it cannot clear.
            broken.append((page_url, f"<undecodable: {exc}>", "unreadable"))
            continue

        for href in parser.found:
            href = href.strip()
            if not href or href.startswith("#"):
                continue
            # A link written as a full URL against this site's own base is internal, and
            # skipping it as "external" would exempt exactly the links most likely to be
            # hand-written and wrong.
            if site_prefix and (href == site_prefix
                                or href.startswith(site_prefix + "/")):
                href = baseurl + href[len(site_prefix):] or "/"
            elif EXTERNAL.match(href):
                continue
            target = href.split("#")[0].split("?")[0]
            if not target:
                continue
            if target.startswith("/"):
                # Absolute: written with the baseurl, which is not part of the layout.
                if baseurl:
                    if target == baseurl:
                        target = "/"
                    elif target.startswith(baseurl + "/"):
                        target = target[len(baseurl):]
                    else:
                        # An absolute link that omits the baseurl cannot resolve once
                        # deployed, however well it works from a local `site/` root.
                        broken.append((page_url, href, "outside baseurl"))
                        continue
            else:
                # Relative: the browser resolves it against the *served* URL, so the
                # baseurl cancels out on both sides and `page_url` (already
                # site-root-relative) is the correct base. Stripping a baseurl here
                # would be wrong — there is none to strip.
                target = urljoin(page_url, target)
            if not resolves(site, unquote(target)):
                broken.append((page_url, href, "404"))

    if broken:
        print(f"check-links: {len(broken)} broken internal link(s) across {pages} page(s):\n")
        for page_url, href, why in sorted(set(broken)):
            print(f"  {page_url}\n      -> {href}  [{why}]")
        print("\nA trailing-slash link needs a directory index. If these are all `/foo/`")
        print("links whose files are `foo.html`, `use_directory_urls` is off in mkdocs.yml.")
        return 1

    if not pages:
        # Fail closed. "0 pages, no broken links" is the shape this gate takes when it
        # has been pointed at the wrong directory, and it is indistinguishable from
        # success in a CI log.
        print(f"check-links: no HTML pages found under {site} — nothing was checked.\n"
              f"This is a failure, not a pass: build the site first "
              f"(mkdocs build --strict) and point this at the build output.",
              file=sys.stderr)
        return 1

    print(f"check-links: OK — every internal link across {pages} page(s) resolves.")
    return 0


def self_test() -> int:
    """Prove the checker flags the known-broken layout and accepts a correct one."""
    ORIGIN = "https://achird-labs.github.io"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # The exact upstream layout: the page is built as `features/spaces.html`, the
        # link points at `features/spaces/`. Live, that is a 404.
        broken = tmp / "broken"
        (broken / "features").mkdir(parents=True)
        (broken / "index.html").write_text('<a href="/rift-docs/features/spaces/">spaces</a>')
        (broken / "features" / "spaces.html").write_text("spaces")

        # The same link served by a directory index, plus the two relative-link shapes
        # the docs actually use: a relative link carries no baseurl, so resolving it as
        # though it did reports a false 404.
        fixed = tmp / "fixed"
        (fixed / "features" / "spaces").mkdir(parents=True)
        (fixed / "performance").mkdir(parents=True)
        (fixed / "index.html").write_text(
            '<a href="/rift-docs/features/spaces/">abs</a><a href="performance/">rel</a>')
        (fixed / "features" / "spaces" / "index.html").write_text(
            '<a href="../../performance/">up</a>')
        # A deep link into a sibling project on the same Pages origin. It is external —
        # flagging it would break every page that links out to a per-repo SDK site.
        (fixed / "siblings.html").write_text(
            '<a href="https://achird-labs.github.io/rift/features/">engine</a>'
            '<a href="https://achird-labs.github.io/rift-docs/performance/">self</a>')
        (fixed / "performance" / "index.html").write_text("perf")

        # A meta-refresh stub pointing at a page that is not there — the shape a rotted
        # legacy redirect takes.
        meta = tmp / "meta"
        meta.mkdir()
        (meta / "index.html").write_text(
            '<meta http-equiv="refresh" content="0; url=../articles/gone/">')

        # An internal link written as a full same-origin URL.
        origin_link = tmp / "origin"
        origin_link.mkdir()
        (origin_link / "index.html").write_text(
            '<a href="https://achird-labs.github.io/rift-docs/nope/">n</a>')

        # An existing but empty site dir: nothing to check is not the same as nothing wrong.
        empty = tmp / "empty"
        empty.mkdir()

        must_fail = {
            "the known-broken flat-file/trailing-slash layout": broken,
            "a dead meta-refresh target": meta,
            "a broken same-origin absolute link": origin_link,
            "an empty site directory": empty,
        }
        for why, fixture in must_fail.items():
            if check_site(fixture, "/rift-docs", ORIGIN) == 0:
                print(f"check-links --self-test: FAILED — passed {why}.", file=sys.stderr)
                return 1
        if check_site(fixed, "/rift-docs", ORIGIN) != 0:
            print("check-links --self-test: FAILED — rejected a correctly-built site.",
                  file=sys.stderr)
            return 1

    print(f"check-links --self-test: OK — flags {len(must_fail)} broken shapes, "
          "accepts a correctly-built site.")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--self-test":
        return self_test()
    site_dir = Path(argv[0]) if argv else REPO_ROOT / "site"
    origin, baseurl = site_url()
    return check_site(site_dir, baseurl, origin)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
