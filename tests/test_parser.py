from __future__ import annotations

import struct
from pathlib import Path

import pytest

from sims4mcp.parser import DBPFReader, SaveFileParser, find_saves, load_save
from sims4mcp.models import SimAge

from conftest import make_dbpf_v2, make_household_blob, make_sim_description_blob


class TestDBPFReader:
    def test_rejects_non_dbpf_magic(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.save"
        p.write_bytes(b"NOTA" + b"\x00" * 60)
        with pytest.raises(ValueError, match="Not a DBPF file"):
            DBPFReader(p)

    def test_rejects_v1_header(self, tmp_path: Path) -> None:
        header = struct.pack("<IHHII", struct.unpack("<I", b"DBPF")[0], 1, 0, 0, 0)
        p = tmp_path / "v1.save"
        p.write_bytes(header + b"\x00" * 48)
        with pytest.raises(ValueError, match="Unsupported DBPF version"):
            DBPFReader(p)

    def test_empty_index(self, tmp_path: Path) -> None:
        raw = make_dbpf_v2([])
        p = tmp_path / "empty.save"
        p.write_bytes(raw)
        reader = DBPFReader(p)
        assert len(reader._entries) == 0

    def test_single_resource_uncompressed(self, tmp_path: Path) -> None:
        content = b"hello world"
        raw = make_dbpf_v2([(0x12345678, content)])
        p = tmp_path / "single.save"
        p.write_bytes(raw)
        reader = DBPFReader(p)
        assert len(reader._entries) == 1
        data = reader.get_resource(0x12345678)
        assert data is not None
        assert data == content

    def test_get_resource_returns_none_if_missing(self, tmp_path: Path) -> None:
        raw = make_dbpf_v2([(0xAAAAAAAA, b"something")])
        p = tmp_path / "missing.save"
        p.write_bytes(raw)
        reader = DBPFReader(p)
        assert reader.get_resource(0xBBBBBBBB) is None

    def test_multiple_resources(self, tmp_path: Path) -> None:
        r1 = make_household_blob(1, "A", 100.0)
        r2 = make_sim_description_blob(100, "Foo", "Bar")
        raw = make_dbpf_v2([(0x9D763827, r1), (0x02459A1C, r2)])
        p = tmp_path / "multi.save"
        p.write_bytes(raw)
        reader = DBPFReader(p)
        assert len(reader._entries) == 2
        assert reader.get_resource(0x9D763827) is not None
        assert reader.get_resource(0x02459A1C) is not None


class TestSaveFileParser:
    def test_parse_minimal_save(self, minimal_save: Path) -> None:
        sf = load_save(minimal_save)
        assert sf.name == "test_save"
        assert len(sf.households) == 1
        assert sf.households[0].name == "Test Family"
        assert sf.households[0].funds is not None

    def test_parse_sim_in_save(self, minimal_save: Path) -> None:
        sf = load_save(minimal_save)
        sims = sf.sims
        assert len(sims) == 1
        sim = sims[0]
        assert sim.first_name == "Jane"
        assert sim.last_name == "Doe"
        assert sim.id == 1001

    def test_parse_save_no_households(self, tmp_path: Path) -> None:
        raw = make_dbpf_v2([])
        p = tmp_path / "empty.save"
        p.write_bytes(raw)
        sf = load_save(p)
        assert sf.name == "empty"
        assert len(sf.households) == 0

    def test_load_save_roundtrip(self, minimal_save: Path) -> None:
        sf = load_save(str(minimal_save))
        assert len(sf.sims) == 1
        assert sf.sims[0].first_name == "Jane"


class TestFindSaves:
    def test_find_saves_returns_empty_for_nonexistent(self, tmp_path: Path) -> None:
        result = find_saves(tmp_path / "nope")
        assert result == []

    def test_find_saves_finds_save_files(self, tmp_path: Path) -> None:
        (tmp_path / "slot_00000001.save").write_bytes(b"x")
        (tmp_path / "slot_00000002.save.ver1").write_bytes(b"x")
        (tmp_path / "not_a_save.txt").write_bytes(b"x")
        result = find_saves(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".save" or ".save." in p.name for p in result)

    def test_find_saves_defaults_to_documents(self) -> None:
        result = find_saves()
        assert isinstance(result, list)
