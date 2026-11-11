#!/usr/bin/env python3
"""Reject desktop release archives missing required ROM-import metadata."""
from __future__ import annotations

import argparse
from pathlib import Path
import tarfile
import zipfile

from package_import_metadata import SOURCE, metadata_paths


def check(repo: Path, archive: Path) -> None:
    required = {p.as_posix() for p in metadata_paths((repo / SOURCE).read_text(encoding="utf-8"))}
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            members = [m.filename for m in bundle.infolist() if not m.is_dir()]
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as bundle:
            members = [m.name for m in bundle.getmembers() if m.isfile()]
    else:
        raise ValueError("unsupported release format")
    found = set()
    for member in members:
        parts = member.split("/", 1)
        if len(parts) == 2:
            found.add(parts[1])
    missing = sorted(required - found)
    if missing:
        raise ValueError("missing import metadata: " + ", ".join(missing))
    forbidden = [name for name in members if name.lower().endswith((".gba", ".sav", ".rpack", ".state"))]
    if forbidden:
        raise ValueError("unexpected copyrighted/gameplay content in archive")
    print(f"PASS: {archive.name} contains all {len(required)} import metadata files; no ROM/save/pack")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    check(args.repo.resolve(), args.archive.resolve())
