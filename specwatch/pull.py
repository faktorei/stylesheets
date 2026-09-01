#!/usr/bin/env python3
"""specwatch/pull.py — fetch pinned upstream artefacts into vendor/.

Starter implementation: pulls the listed paths from GitHub at the pinned ref
via the raw/codeload endpoints, records sha256 hashes into lock.json, and (if
a previous lock exists) prints which artefacts changed. Growing this into the
full pipeline — Schematron rule-level diffing, code-list regeneration from
genericode, human-readable change reports — is the Phase 0/ongoing track.
"""
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import yaml  # pip install pyyaml

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
LOCK = ROOT / "lock.json"


def fetch_bytes(src: dict) -> bytes:
    """Fetch a source's zip. Three modes: a literal `url:`, a GitLab `host:`
    archive, or (default) GitHub codeload at a pinned ref."""
    if src.get("url"):
        # Unversioned artefact published at a fixed URL — pinned by sha256
        # rather than by ref (see the note in sources.yaml).
        return urllib.request.urlopen(src["url"], timeout=120).read()
    repo, ref = src["repo"], src["ref"]
    if src.get("host"):
        # GitLab archive endpoint — same URL shape for branches and tags.
        project = repo.rsplit("/", 1)[-1]
        url = f"https://{src['host']}/{repo}/-/archive/{ref}/{project}-{ref}.zip"
        return urllib.request.urlopen(url, timeout=120).read()
    url = f"https://codeload.github.com/{repo}/zip/refs/heads/{ref}"
    try:
        return urllib.request.urlopen(url, timeout=120).read()
    except Exception:
        url = f"https://codeload.github.com/{repo}/zip/refs/tags/{ref}"
        return urllib.request.urlopen(url, timeout=120).read()


def archive_prefix(zf: zipfile.ZipFile) -> str:
    """The wrapper directory to strip from member names, or "" if there is none.

    GitHub/GitLab archives nest everything under a single `repo-ref/` directory.
    A plain artefact zip may not: PINT A-NZ has three top-level dirs and no
    wrapper, so assuming namelist()[0] is the prefix would slice the front off
    every path. Strip only when there really is exactly one top-level entry.
    """
    tops = {name.split("/", 1)[0] for name in zf.namelist()}
    if len(tops) != 1:
        return ""
    top = tops.pop()
    # A lone top-level FILE is not a wrapper directory.
    if not any(n.startswith(top + "/") for n in zf.namelist()):
        return ""
    return top + "/"


def source_label(name: str, src: dict) -> str:
    if src.get("url"):
        # ASCII only: this prints to a cp1252 console on Windows dev boxes,
        # where a non-encodable char raises UnicodeEncodeError and kills the pull.
        return f"{name}: {src['url']} @sha256:{src['sha256'][:12]}..."
    return f"{name}: {src['repo']}@{src['ref']}"


def main() -> None:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text())
    old = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    new: dict[str, str] = {}

    for name, src in cfg["sources"].items():
        print(f"[specwatch] {source_label(name, src)}")
        data = fetch_bytes(src)

        # A source pinned by content hash rather than by ref: refuse to vendor
        # anything but the reviewed bytes. A mismatch means upstream republished
        # an unversioned artefact — that is a deliberate review, not a silent
        # re-vendor, so fail hard (CI included).
        expected = src.get("sha256")
        if expected:
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected:
                sys.exit(
                    f"[specwatch] {name}: PIN MISMATCH\n"
                    f"  expected sha256 {expected}  (sources.yaml)\n"
                    f"  actual   sha256 {actual}  (fetched)\n"
                    f"  Upstream republished an unversioned artefact. Review the\n"
                    f"  diff, then bump `sha256` for {name} in specwatch/sources.yaml."
                )

        zf = zipfile.ZipFile(io.BytesIO(data))
        prefix = archive_prefix(zf)
        for member in zf.namelist():
            rel = member[len(prefix):]
            if not rel or member.endswith("/"):
                continue
            if any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in src["paths"]):
                out = VENDOR / name / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                content = zf.read(member)
                out.write_bytes(content)
                new[f"{name}/{rel}"] = hashlib.sha256(content).hexdigest()

    changed = [k for k in new if old.get(k) not in (None, new[k])]
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    LOCK.write_text(json.dumps(new, indent=2, sort_keys=True))
    print(f"[specwatch] {len(new)} artefacts vendored; "
          f"{len(changed)} changed, {len(added)} added, {len(removed)} removed")
    if changed:
        print("  changed:", *changed[:20], sep="\n    ")
    sys.exit(0)


if __name__ == "__main__":
    main()
