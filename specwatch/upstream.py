#!/usr/bin/env python3
"""specwatch/upstream.py — is anything NEWER than our pins published upstream?

`pull.py` answers "do the pinned artefacts still reproduce?". It cannot answer
"has upstream released something we have not pinned?", and for one source that
question has no good API: OpenPeppol published BIS Billing 3.0.21 (May 2026) on
docs.peppol.eu WITHOUT tagging GitHub, so a tags-API check said "nothing new"
for five months while the mandatory release was live. This script checks the
signals that are actually authoritative, per source:

  peppol-bis-billing   the LIVE .sch files on docs.peppol.eu (bytes vs lock.json,
                       plus the "Last update:" header for a human-readable name)
  en16931-artefacts    GitHub releases/latest tag vs the pinned ref
  xrechnung-schematron KoSIT GitLab tags vs the pinned ref (newest vX.Y.Z)
  pint-aunz-billing    sha256 of the unversioned zip vs the pinned hash
  iso-schematron-skeleton  not checked (a 2020 compiler; bump by hand if ever)

Prints a markdown report (ASCII only — Windows consoles) and exits 1 on any
drift so CI can open an issue. Network-only; writes nothing. Apache-2.0.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PEPPOL_FILES = "https://docs.peppol.eu/poacc/billing/3.0/files/"
PEPPOL_NOTES = "https://docs.peppol.eu/poacc/billing/3.0/release-notes/"
KOSIT_TAGS = ("https://projekte.kosit.org/api/v4/projects/"
              "xrechnung%2Fxrechnung-schematron/repository/tags?per_page=20")


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "faktorei-specwatch"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {tok}")
    return urllib.request.urlopen(req, timeout=60).read()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def vtuple(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", tag))


def check_peppol(src: dict, lock: dict) -> list[str]:
    """Compare the live docs.peppol.eu artefacts against what we vendored."""
    out = []
    for rel in ("rules/sch/PEPPOL-EN16931-UBL.sch", "rules/sch/CEN-EN16931-UBL.sch"):
        name = rel.rsplit("/", 1)[-1]
        live = get(PEPPOL_FILES + name)
        pinned = lock.get(f"peppol-bis-billing/{rel}")
        head = live[:800].decode("utf-8", "replace")
        m = re.search(r"Last update:\s*([^\n<]+?)\s*\.?\s*(?:-->|\n)", head)
        label = m.group(1).strip() if m else "(no 'Last update' header)"
        if pinned is None:
            out.append(f"- peppol-bis-billing/{rel}: NOT IN lock.json (run pull.py)")
        elif sha(live) != pinned:
            out.append(f"- peppol-bis-billing/{rel}: live file differs from the pin "
                       f"(live header: '{label}'; pinned ref {src['ref'][:12]}). "
                       f"Read {PEPPOL_NOTES} and re-pin.")
    return out


def check_github_releases(name: str, src: dict) -> list[str]:
    data = json.loads(get(f"https://api.github.com/repos/{src['repo']}/releases/latest"))
    latest = data.get("tag_name", "")
    if latest and latest != src["ref"] and vtuple(latest) > vtuple(src["ref"]):
        return [f"- {name}: latest release {latest} ({data.get('published_at', '')[:10]}) "
                f"> pinned {src['ref']}"]
    return []


def check_kosit(name: str, src: dict) -> list[str]:
    tags = json.loads(get(KOSIT_TAGS))
    stable = sorted((t["name"] for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t["name"])),
                    key=vtuple)
    if stable and vtuple(stable[-1]) > vtuple(src["ref"]):
        when = next((t["commit"]["committed_date"][:10] for t in tags if t["name"] == stable[-1]), "")
        return [f"- {name}: newest tag {stable[-1]} ({when}) > pinned {src['ref']}"]
    return []


def check_zip_hash(name: str, src: dict) -> list[str]:
    actual = sha(get(src["url"]))
    if actual != src["sha256"]:
        return [f"- {name}: {src['url']} republished (sha256 {actual[:12]}... != pinned "
                f"{src['sha256'][:12]}...). Review the diff, then bump sha256."]
    return []


def main() -> int:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "lock.json").read_text(encoding="utf-8"))
    drift: list[str] = []
    errors: list[str] = []
    checks = {
        "peppol-bis-billing": lambda s: check_peppol(s, lock),
        "en16931-artefacts": lambda s: check_github_releases("en16931-artefacts", s),
        "xrechnung-schematron": lambda s: check_kosit("xrechnung-schematron", s),
        "pint-aunz-billing": lambda s: check_zip_hash("pint-aunz-billing", s),
    }
    for name, src in cfg["sources"].items():
        fn = checks.get(name)
        if fn is None:
            continue
        try:
            drift += fn(src)
        except Exception as e:  # a dead endpoint is a finding too, not a pass
            errors.append(f"- {name}: check failed: {type(e).__name__}: {e}")

    print(f"# specwatch upstream check (cycle {cfg.get('cycle')})")
    print()
    if drift:
        print("## Drift - upstream has published something newer than the pin")
        print(*drift, sep="\n")
    else:
        print("No drift: every checked source matches its pin.")
    if errors:
        print()
        print("## Checks that could not run")
        print(*errors, sep="\n")
    print()
    print("Next step on drift: the pre-tag verification drill (bump the pin + cycle, "
          "pull.py, validate.py --all, tag).")
    return 1 if (drift or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
