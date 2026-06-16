"""Sims 4 save file (.save) parser.

Save files use the DBPF v2 container format.  Each index entry points to a
compressed resource (typically LZ4).  This module extracts and decompresses
resources, then walks well-known resource-type IDs to build structured models.

References:
  - https://github.com/cynical-orange/sims4-tools
  - https://modthesims.info/wiki.php?title=Sims_4:Save_File_Format
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass

import lz4.block
from pathlib import Path

from sims4mcp.models import (
    SaveFile,
    Household,
    HouseholdFunds,
    Sim,
    SimAge,
    SimGender,
    Moodlet,
    Career,
    Skill,
    Relationship,
)

# DBPF constants
DBPF_MAGIC = struct.unpack("<I", b"DBPF")[0]  # 0x46425044 on little-endian
DBPF_HEADER_FMT = "<IHHII"
DBPF_HEADER_LEN = struct.calcsize(DBPF_HEADER_FMT)  # 16

# Well-known resource type IDs (from reverse engineering / sims4-tools)
TAG_SIM_DESCRIPTION = 0x02459A1C
TAG_HOUSEHOLD = 0x9D763827
TAG_SIM_TRAITS = 0xB148A7BB
TAG_CAREER = 0xB6A8C83E
TAG_SKILLS = 0xD3C2BDE0
TAG_OBJECTIVE = 0xEB6917A3
TAG_INVENTORY = 0xE9E34EEB
TAG_WORLD = 0xDFE4CE3A

# Compression type constants (from resource index flags)
COMPRESS_NONE = 0
COMPRESS_LZ4 = 1
COMPRESS_ZLIB = 2


@dataclass
class IndexEntry:
    type_id: int
    group_id: int
    instance_id: int
    offset: int
    size: int
    compressed_size: int
    compression: int


class DBPFReader:
    """Reads a Sims 4 DBPF v2 save file, decompressing resources on demand."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data = path.read_bytes()
        self._entries: list[IndexEntry] = []
        self._parse_header()

    def _parse_header(self) -> None:
        data = self._data
        magic, major, minor, _unused, index_count = struct.unpack_from(
            DBPF_HEADER_FMT, data, 0
        )
        if magic != DBPF_MAGIC:
            raise ValueError(f"Not a DBPF file (magic: 0x{magic:08X})")
        if major < 2:
            raise ValueError(f"Unsupported DBPF version {major}.{minor}; need v2")

        # DBPF v2 header layout (offset = 16 after the fixed header fields):
        #   index_size : uint32
        #   index_compressed : uint32   (0 = uncompressed, 1 = LZ4)
        #   index_offset : uint64
        #   reserved : 32 bytes
        index_size, index_compressed, index_offset = struct.unpack_from(
            "<IIQ", data, DBPF_HEADER_LEN
        )

        raw_index = data[index_offset : index_offset + index_size]
        if index_compressed == COMPRESS_LZ4:
            # LZ4 frame format
            raw_index = lz4.block.decompress(
                raw_index[4:], uncompressed_size=index_size * 4
            )

        self._parse_index(raw_index, index_count)

    def _parse_index(self, raw: bytes, count: int) -> None:
        """Parse index entries (each 20 bytes in v2)."""
        entry_fmt = "<IIQHH"  # type_id, group_id, instance_lo, instance_hi, flags, size_compressed
        entry_len = struct.calcsize(entry_fmt)  # 20
        for i in range(count):
            offset = i * entry_len
            if offset + entry_len > len(raw):
                break
            (type_id,
             group_id,
             instance_lo,
             instance_hi,
             flags,
             compressed_size) = struct.unpack_from(entry_fmt, raw, offset)
            compression = flags & 0xF
            instance_id = (instance_hi << 32) | instance_lo
            self._entries.append(
                IndexEntry(
                    type_id=type_id,
                    group_id=group_id,
                    instance_id=instance_id,
                    offset=0,
                    size=0,
                    compressed_size=compressed_size,
                    compression=compression,
                )
            )

    def get_resource(self, type_id: int) -> bytes | None:
        """Find the first resource of *type_id*, decompress and return it."""
        for entry in self._entries:
            if entry.type_id == type_id:
                return self._decompress_entry(entry)
        return None

    def get_resources(self, type_id: int) -> list[bytes]:
        """Return all resources matching *type_id*."""
        out = []
        for entry in self._entries:
            if entry.type_id == type_id:
                out.append(self._decompress_entry(entry))
        return out

    def _decompress_entry(self, entry: IndexEntry) -> bytes:
        """Read and decompress a single index entry."""
        data_len = entry.compressed_size
        raw = self._data

        # Find the actual data offset — after the index we need to scan.
        # In practice the data follows the index, but we reconstruct it from
        # a running offset.  For safety, use a heuristic: start reading after
        # the index area.
        # === simplified: assume resources follow the index sequentially ===
        # A real parser would store offsets during index parsing.  For the
        # scaffold we approximate by reading the bytes at the expected region.
        # The proper approach is to parse the HOFF (hole-offset) table — but
        # for POC purposes we locate resources by scanning past the header +
        # index.
        idx_end = (
            DBPF_HEADER_LEN
            + 24  # remaining v2 header fields
            + len(self._entries) * 20
        )
        # Try to find the resource at its expected location (size-based heuristic)
        buf = raw[idx_end:]
        if entry.offset and entry.offset < len(raw):
            buf = raw[entry.offset:]

        compressed = buf[:data_len]
        if entry.compression == COMPRESS_LZ4 and data_len > 4:
            try:
                return lz4.block.decompress(compressed[4:])
            except Exception:
                pass
        elif entry.compression == COMPRESS_NONE:
            return compressed
        return compressed  # fallback: return as-is


class SaveFileParser:
    """Parses a Sims 4 save into structured Python objects."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._dbpf = DBPFReader(path)

    def parse(self) -> SaveFile:
        households: dict[int, Household] = {}
        sims: dict[int, Sim] = {}

        self._parse_households(households, sims)
        self._parse_sim_details(sims)
        self._assign_sims_to_households(households, sims)

        return SaveFile(
            path=self.path,
            name=self.path.stem,
            households=list(households.values()),
        )

    def _parse_households(
        self, households: dict[int, Household], sims: dict[int, Sim]
    ) -> None:
        for blob in self._dbpf.get_resources(TAG_HOUSEHOLD):
            try:
                self._read_household_blob(blob, households, sims)
            except Exception:
                continue

    def _read_household_blob(
        self,
        data: bytes,
        households: dict[int, Household],
        sims: dict[int, Sim],
    ) -> None:
        """Parse a household resource blob — contains household metadata + sim refs."""
        buf = io.BytesIO(data)
        _magic = buf.read(4)
        _version = struct.unpack("<I", buf.read(4))[0]

        # Household ID
        hh_id = struct.unpack("<Q", buf.read(8))[0]

        # Household name (UTF-16LE)
        name_len = struct.unpack("<I", buf.read(4))[0]
        name_raw = buf.read(name_len * 2)
        name = name_raw.decode("utf-16-le", errors="replace").strip("\x00")

        hh = households.setdefault(hh_id, Household(id=hh_id, name=name or "Unnamed"))
        hh.name = name or "Unnamed"

        # Funds
        _ = buf.read(4)  # skip some fields
        funds_raw = buf.read(8)
        if len(funds_raw) == 8:
            hh.funds = HouseholdFunds(simoleons=struct.unpack("<d", funds_raw)[0])

        # Sim count + IDs
        sim_count = struct.unpack("<I", buf.read(4))[0]
        for _ in range(sim_count):
            sim_id = struct.unpack("<Q", buf.read(8))[0]
            if sim_id not in sims:
                sims[sim_id] = Sim(id=sim_id, first_name="", last_name="")
            sims[sim_id].household_id = hh_id

    def _parse_sim_details(self, sims: dict[int, Sim]) -> None:
        for blob in self._dbpf.get_resources(TAG_SIM_DESCRIPTION):
            try:
                self._read_sim_blob(blob, sims)
            except Exception:
                continue

    def _read_sim_blob(self, data: bytes, sims: dict[int, Sim]) -> None:
        """Parse a Sim description resource."""
        buf = io.BytesIO(data)
        _magic = buf.read(4)
        _version = struct.unpack("<I", buf.read(4))[0]

        sim_id = struct.unpack("<Q", buf.read(8))[0]
        sim = sims.setdefault(sim_id, Sim(id=sim_id, first_name="", last_name=""))

        # First name
        fname_len = struct.unpack("<I", buf.read(4))[0]
        fname = buf.read(fname_len * 2).decode("utf-16-le", errors="replace").strip("\x00")
        sim.first_name = fname or sim.first_name

        # Last name
        lname_len = struct.unpack("<I", buf.read(4))[0]
        lname = buf.read(lname_len * 2).decode("utf-16-le", errors="replace").strip("\x00")
        sim.last_name = lname or sim.last_name

        # Gender
        _ = buf.read(16)  # skip ahead
        gender_byte = buf.read(1)
        if gender_byte:
            sim.gender = SimGender.MALE if gender_byte[0] == 0 else SimGender.FEMALE

        # Age
        age_byte = buf.read(1)
        age_map = {
            0: SimAge.BABY,
            1: SimAge.TODDLER,
            2: SimAge.CHILD,
            3: SimAge.TEEN,
            4: SimAge.YOUNG_ADULT,
            5: SimAge.ADULT,
            6: SimAge.ELDER,
        }
        if age_byte:
            sim.age = age_map.get(age_byte[0])

        # Traits (read from the blob if present)
        if TAG_SIM_TRAITS:
            traits_raw = self._dbpf.get_resource(TAG_SIM_TRAITS)
            if traits_raw:
                self._read_traits(traits_raw, sims)

        # Career
        career_raw = self._dbpf.get_resource(TAG_CAREER)
        if career_raw:
            self._read_careers(career_raw, sims)

    def _read_traits(self, data: bytes, sims: dict[int, Sim]) -> None:
        buf = io.BytesIO(data)
        _magic = buf.read(4)
        _version = struct.unpack("<I", buf.read(4))[0]
        sim_id = struct.unpack("<Q", buf.read(8))[0]
        if sim_id not in sims:
            return
        count = struct.unpack("<I", buf.read(4))[0]
        traits = []
        for _ in range(count):
            tlen = struct.unpack("<I", buf.read(4))[0]
            trait = buf.read(tlen * 2).decode("utf-16-le", errors="replace").strip("\x00")
            if trait:
                traits.append(trait)
        sims[sim_id].traits = traits

    def _read_careers(self, data: bytes, sims: dict[int, Sim]) -> None:
        buf = io.BytesIO(data)
        _magic = buf.read(4)
        _version = struct.unpack("<I", buf.read(4))[0]
        sim_id = struct.unpack("<Q", buf.read(8))[0]
        if sim_id not in sims:
            return
        _ = buf.read(8)  # skip some fields
        name_len = struct.unpack("<I", buf.read(4))[0]
        name = buf.read(name_len * 2).decode("utf-16-le", errors="replace").strip("\x00")
        level = struct.unpack("<I", buf.read(4))[0]
        sims[sim_id].career = Career(name=name, level=level)

    def _assign_sims_to_households(
        self, households: dict[int, Household], sims: dict[int, Sim]
    ) -> None:
        for sim in sims.values():
            if sim.household_id and sim.household_id in households:
                households[sim.household_id].sims.append(sim)


def find_saves(search_path: Path | None = None) -> list[Path]:
    """Locate Sims 4 save files in the standard user directory."""
    default = Path.home() / "Documents" / "Electronic Arts" / "The Sims 4" / "saves"
    root = search_path or default
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir() if p.suffix == ".save" or ".save." in p.name
    )


def load_save(path: str | Path) -> SaveFile:
    """Parse a single save file and return structured models."""
    return SaveFileParser(Path(path)).parse()
