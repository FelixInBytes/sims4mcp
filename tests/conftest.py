from __future__ import annotations

import struct
from pathlib import Path

import lz4.block
import pytest


def make_dbpf_v2(
    resources: list[tuple[int, bytes]],
    compress: bool = False,
) -> bytes:
    """Build a synthetic DBPF v2 file from resource type-id → raw content pairs.

    Returns the full file bytes that ``DBPFReader`` can parse.
    """
    # Each index entry: type_id(4) + group_id(4) + instance_hi(4) + instance_lo(4) + size(4) + flags(4)
    entry_fmt = "<IIIIII"
    entry_len = struct.calcsize(entry_fmt)  # 24

    index_entries = b""
    data_blocks = b""
    data_offset = 0

    for type_id, content in resources:
        compressed = content
        flags = 0  # COMPRESS_NONE
        if compress:
            compressed = b"\x01\x00\x00\x00" + lz4.block.compress(content)
            flags = 1  # COMPRESS_LZ4

        instance_hi = type_id >> 32
        instance_lo = type_id & 0xFFFFFFFF

        entry = struct.pack(
            entry_fmt,
            type_id,
            0,              # group_id
            instance_hi,
            instance_lo,
            len(compressed),
            flags,
        )
        index_entries += entry
        data_blocks += compressed

    index_count = len(resources)
    index_size = len(index_entries)
    index_offset = 16 + 24  # header + v2 fields
    # reserved area starts at offset 32, is 32 bytes
    # index starts at offset 64 (16 + 24 + 32 reserved)
    index_offset = 64

    # Build header
    # magic(4) + major(2) + minor(2) + unused(4) + index_count(4)
    header = struct.pack("<IHHII", struct.unpack("<I", b"DBPF")[0], 2, 0, 0, index_count)
    # v2 fields: index_size(4) + index_compressed(4) + index_offset(8)
    v2_fields = struct.pack("<IIQ", index_size, 0, index_offset)
    # reserved (32 bytes)
    reserved = b"\x00" * 32

    # Assemble
    result = bytearray()
    result.extend(header)
    result.extend(v2_fields)
    result.extend(reserved)
    result.extend(index_entries)
    result.extend(data_blocks)

    return bytes(result)


def make_household_blob(
    hh_id: int,
    name: str,
    funds: float = 1000.0,
    sim_ids: list[int] | None = None,
) -> bytes:
    """Build a synthetic household resource blob.

    Strings use the Sims 4 convention: length prefix (code-unit count)
    followed by exactly ``length * 2`` bytes of UTF-16LE data (no null terminator).
    """
    sim_ids = sim_ids or []
    buf = bytearray()
    buf.extend(b"HNam")
    buf.extend(struct.pack("<I", 1))  # version
    buf.extend(struct.pack("<Q", hh_id))
    name_utf16 = name.encode("utf-16-le")
    buf.extend(struct.pack("<I", len(name)))
    buf.extend(name_utf16)
    buf.extend(b"\x00" * 4)  # skip
    buf.extend(struct.pack("<d", funds))
    buf.extend(struct.pack("<I", len(sim_ids)))
    for sid in sim_ids:
        buf.extend(struct.pack("<Q", sid))
    return bytes(buf)


def make_sim_description_blob(
    sim_id: int,
    first_name: str,
    last_name: str,
    gender: int = 0,
    age: int = 5,
) -> bytes:
    """Build a synthetic Sim description resource blob."""
    buf = bytearray()
    buf.extend(b"SNam")
    buf.extend(struct.pack("<I", 1))  # version
    buf.extend(struct.pack("<Q", sim_id))

    fn_utf16 = first_name.encode("utf-16-le")
    buf.extend(struct.pack("<I", len(first_name)))
    buf.extend(fn_utf16)

    ln_utf16 = last_name.encode("utf-16-le")
    buf.extend(struct.pack("<I", len(last_name)))
    buf.extend(ln_utf16)

    buf.extend(b"\x00" * 16)  # skip ahead to gender/age
    buf.extend(struct.pack("<B", gender))
    buf.extend(struct.pack("<B", age))
    return bytes(buf)


@pytest.fixture
def minimal_save(tmp_path: Path) -> Path:
    """Create a minimal DBPF save file with one household + one sim."""
    sim_id = 1001
    hh_id = 2001

    hh_blob = make_household_blob(hh_id, "Test Family", 5000.0, [sim_id])
    sim_blob = make_sim_description_blob(sim_id, "Jane", "Doe", gender=1, age=5)

    raw = make_dbpf_v2(
        [
            (0x9D763827, hh_blob),  # TAG_HOUSEHOLD
            (0x02459A1C, sim_blob),  # TAG_SIM_DESCRIPTION
        ]
    )
    path = tmp_path / "test_save.save"
    path.write_bytes(raw)
    return path
