#!/usr/bin/env python3
"""Package only the public TOML metadata required for local Emerald ROM import.

Read the paths directly from desktop_game_content.c so release packaging cannot
silently drift from the runtime importer's manifest/catalog inventory. A user's
ROM, extracted bytes, save files, and .rpack files are never included.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import sys

SOURCE = Path("src/platform/desktop_game_content.c")
ARRAY = re.compile(
    r"static const char\s*\*const\s+sImport(Manifests|Catalogs)"
    r"\[[^]]+\]\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
STRING = re.compile(r'"([^"]+)"')
ALLOWED = (
    "resources/extraction/emerald/bpee01/",
    "resources/catalogs/emerald/",
)


def metadata_paths(source: str) -> list[Path]:
    matches = ARRAY.findall(source)
    if len(matches) != 2 or {name for name, _ in matches} != {"Manifests", "Catalogs"}:
        raise ValueError("could not find both game-content metadata inventories")
    paths = []
    for name, body in matches:
        values = STRING.findall(body)
        if not values:
            raise ValueError(f"{name} metadata inventory is empty")
        for value in values:
            path = Path(value)
            if (not value.endswith(".toml")
                or not value.startswith(ALLOWED)
                or path.is_absolute()
                or ".." in path.parts):
                raise ValueError(f"unsafe or unexpected metadata path: {value}")
            paths.append(path)
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate metadata path")
    return paths


def copy_metadata(repo: Path, stage: Path) -> int:
    paths = metadata_paths((repo / SOURCE).read_text(encoding="utf-8"))
    for rel in paths:
        src = repo / rel
        if not src.is_file() or src.is_symlink():
            raise FileNotFoundError(f"required release import metadata missing: {rel}")
        dst = stage / rel
        dst.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        dst.chmod(0o644)
    print(f"Packaged {len(paths)} ROM-import manifest/catalog TOML files")
    return len(paths)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("stage", type=Path)
    args = parser.parse_args()
    try:
        copied = copy_metadata(args.repository.resolve(), args.stage.resolve())
        if copied < 2:
            raise ValueError("metadata inventory unexpectedly empty")
    except (OSError, ValueError) as exc:
        print(f"release metadata packaging failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
