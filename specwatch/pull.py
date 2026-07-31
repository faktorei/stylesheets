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


def fetch_repo_zip(repo: str, ref: str, host: str | None = None) -> zipfile.ZipFile:
    if host:
        # GitLab archive endpoint — same URL shape for branches and tags.
        project = repo.rsplit("/", 1)[-1]
        url = f"https://{host}/{repo}/-/archive/{ref}/{project}-{ref}.zip"
        data = urllib.request.urlopen(url, timeout=120).read()
        return zipfile.ZipFile(io.BytesIO(data))
    url = f"https://codeload.github.com/{repo}/zip/refs/heads/{ref}"
    try:
        data = urllib.request.urlopen(url, timeout=120).read()
    except Exception:
        url = f"https://codeload.github.com/{repo}/zip/refs/tags/{ref}"
        data = urllib.request.urlopen(url, timeout=120).read()
    return zipfile.ZipFile(io.BytesIO(data))


def main() -> None:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text())
    old = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    new: dict[str, str] = {}

    for name, src in cfg["sources"].items():
        print(f"[specwatch] {name}: {src['repo']}@{src['ref']}")
        zf = fetch_repo_zip(src["repo"], src["ref"], src.get("host"))
        prefix = zf.namelist()[0]
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
