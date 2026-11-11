#!/usr/bin/env python3
"""Build ROM-only reconstruction provenance for the native desktop importer.

The output is a bounded index of ROM offsets and lengths, NOT game content.
At runtime the importer constructs text bundles and G/H module payloads from
the user's hash-verified Emerald ROM and checks each manifest SHA-256.
No .bin assets, ROM bytes, saves or completed resource packs are distributed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import tomllib

BASE = Path("resources/extraction/emerald/bpee01")
FAMILIES = ("text", "script/modules", "battle/modules")
MAGIC = b"EMRPROV1"
ROM_SIZE = 16777216


def toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def checked_segments(segments, size: int, kind: int, path: str):
    header = 8 + 4 * len(segments) if kind == 1 else 0
    if not segments or len(segments) > 65535 or header > size:
        raise ValueError(f"{path}: invalid segment count/header")
    cursor = header
    for rom_offset, payload_offset, length in segments:
        if (not 0 <= rom_offset < ROM_SIZE
            or not 0 < length <= ROM_SIZE - rom_offset
            or payload_offset != cursor
            or length > size - cursor):
            raise ValueError(f"{path}: segment gap/overlap/out-of-bounds at {cursor}")
        cursor += length
    if cursor != size:
        raise ValueError(f"{path}: {cursor} reconstructed bytes != {size}")


def make_index(root: Path) -> bytes:
    base = root / BASE
    sources = {}
    manifests = {}
    for family in FAMILIES:
        manifest = toml(base / family / "manifest.production.toml")
        for item in manifest["records"]:
            if item.get("bundle"):
                source = item["source_artifact"]
                if source in manifests:
                    raise ValueError(f"duplicate source artifact {source}")
                if item["source_encoding"] != "raw":
                    raise ValueError(f"{source}: not raw")
                manifests[source] = item

    text_meta = toml(base / "text/bundles.generated.toml")
    for bundle in text_meta["bundles"]:
        source = str(BASE / "text/bundles" /
                     (bundle["id"].removeprefix("emerald:text/") + ".bin"))
        if source not in manifests:
            raise ValueError(f"unlisted text bundle {source}")
        labels = sorted(bundle["labels"], key=lambda item: item["canonical"])
        cursor = 8 + 4 * len(labels)
        spans = []
        for label in labels:
            spans.append((label["rom_offset"], cursor, label["size"]))
            cursor += label["size"]
        if cursor != bundle["blob_size"]:
            raise ValueError(f"{source}: wrong text bundle size")
        sources[source] = (1, spans, cursor)

    for source, item in manifests.items():
        if source in sources:
            continue
        if not (source.startswith(str(BASE / "script/modules/data/"))
                or source.startswith(str(BASE / "battle/modules/data/"))):
            raise ValueError(f"unknown bundle source {source}")
        path = Path(source)
        meta_path = Path(source.replace("/data/", "/meta/")).with_suffix(".toml")
        meta = toml(root / meta_path)
        if meta["module_key"] != item["id"]:
            raise ValueError(f"{source}: module identity disagreement")
        spans = [(seg["original_gba_start"] - 0x08000000,
                  seg["payload_offset"], seg["byte_count"])
                 for seg in meta["segments"]]
        sources[source] = (2, sorted(spans, key=lambda row: row[1]),
                           item["encoded_length"])

    if set(sources) != set(manifests):
        raise ValueError("not all bundle resources have ROM provenance")

    output = bytearray(MAGIC + struct.pack("<I", len(sources)))
    for path in sorted(sources):
        kind, spans, size = sources[path]
        item = manifests[path]
        if item["encoded_length"] != size or item["decoded_length"] != size:
            raise ValueError(f"{path}: size disagrees with manifest")
        checked_segments(spans, size, kind, path)
        name = path.encode("ascii")
        if len(name) > 1023 or b"\\0" in name or ".." in Path(path).parts:
            raise ValueError(f"invalid source path: {path}")
        # Verify the existing developer artifact without distributing it.
        # The runtime will reproduce and independently SHA-check from the ROM.
        original = root / path
        if not original.is_file() or original.stat().st_size != size:
            raise ValueError(f"development artifact unavailable or wrong size: {path}")
        with original.open("rb") as file:
            digest = hashlib.file_digest(file, "sha256").hexdigest()
        if digest != item["source_encoded_sha256"]:
            raise ValueError(f"artifact digest disagrees: {path}")
        output += struct.pack("<HBHI", len(name), kind, len(spans), size)
        output += name + bytes((0,))
        for rom_offset, payload_offset, length in spans:
            output += struct.pack("<III", rom_offset, payload_offset, length)
    print(f"ROM-only provenance: {len(sources)} bundles, {len(output)} metadata bytes")
    return bytes(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        data = make_index(args.repository.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
    except (OSError, ValueError, KeyError, TypeError) as e:
        sys.exit(f"ROM provenance generation FAILED: {e}")


if __name__ == "__main__":
    main()
