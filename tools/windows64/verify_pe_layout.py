#!/usr/bin/env python3
"""Verify structural PE x64 loader invariants after cross-compilation.

The GNU objdump '-f' check can report 'pei-x86-64' even for an executable
whose sections violate Windows PE image alignment requirements. This check
catches that failure before publishing a Windows release.
"""
import pathlib
import struct
import sys


def read_u16(image: bytes, offset: int) -> int:
    return struct.unpack_from("<H", image, offset)[0]


def read_u32(image: bytes, offset: int) -> int:
    return struct.unpack_from("<I", image, offset)[0]


def verify_pe(path: pathlib.Path) -> None:
    image = path.read_bytes()
    if len(image) < 0x100 or image[:2] != b"MZ":
        raise ValueError("not a DOS/PE executable")
    pe = read_u32(image, 0x3C)
    if pe + 24 > len(image) or image[pe:pe + 4] != b"PE\\0\\0":
        raise ValueError("missing PE signature")
    if read_u16(image, pe + 4) != 0x8664:
        raise ValueError("not a Windows AMD64 executable")
    section_count = read_u16(image, pe + 6)
    optional_size = read_u16(image, pe + 20)
    optional = pe + 24
    if optional + optional_size > len(image) or read_u16(image, optional) != 0x20B:
        raise ValueError("not a valid PE32+ optional header")
    section_alignment = read_u32(image, optional + 32)
    file_alignment = read_u32(image, optional + 36)
    image_size = read_u32(image, optional + 56)
    if section_alignment < 0x200 or (section_alignment & (section_alignment - 1)):
        raise ValueError("invalid SectionAlignment")
    if file_alignment < 0x200 or (file_alignment & (file_alignment - 1)):
        raise ValueError("invalid FileAlignment")
    table = optional + optional_size
    if not 0 < section_count <= 96 or table + 40 * section_count > len(image):
        raise ValueError("invalid PE section table")
    occupied = []
    for i in range(section_count):
        offset = table + i * 40
        name = image[offset:offset + 8].rstrip(b"\\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", image, offset + 8
        )
        if virtual_address % section_alignment:
            raise ValueError(
                f"section {name!r} RVA {virtual_address:#x} is not aligned "
                f"to {section_alignment:#x}"
            )
        if raw_size:
            if raw_offset % file_alignment:
                raise ValueError(f"section {name!r} raw offset is not aligned")
            if raw_offset + raw_size > len(image):
                raise ValueError(f"section {name!r} extends past the end of file")
        span = max(virtual_size, raw_size)
        if span:
            occupied.append(
                (virtual_address, virtual_address + ((span + section_alignment - 1)
                                                    // section_alignment) * section_alignment, name)
            )
    occupied.sort()
    for previous, current in zip(occupied, occupied[1:]):
        if previous[1] > current[0]:
            raise ValueError(
                f"PE sections {previous[2]!r} and {current[2]!r} overlap"
            )
    if occupied and occupied[-1][1] > image_size:
        raise ValueError("SizeOfImage does not cover all sections")
    print(
        f"PASS: {path} is PE32+ AMD64; {section_count} sections aligned "
        f"to {section_alignment:#x}; SizeOfImage={image_size:#x}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} FILE.exe")
    try:
        verify_pe(pathlib.Path(sys.argv[1]))
    except (OSError, ValueError, struct.error) as exc:
        sys.exit(f"FAIL: invalid Windows executable: {exc}")
