from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sims4mcp.cli import cli
from sims4mcp.models import SaveFile, Household, Sim, SimAge, HouseholdFunds, Career


def _make_mock_save() -> SaveFile:
    sim = Sim(
        id=1,
        first_name="Test",
        last_name="Sim",
        age=SimAge.ADULT,
        traits=["Active"],
        career=Career(name="Athlete", level=3),
        money=5000,
    )
    hh = Household(id=10, name="Test Family", funds=HouseholdFunds(5000.0), sims=[sim])
    return SaveFile(path=Path("/fake/test.save"), name="test_save", households=[hh])


class TestInfoCommand:
    def test_info_output(self) -> None:
        runner = CliRunner()
        with patch("sims4mcp.cli._resolve_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "Sims:" in result.output
        assert "Test Family" in result.output

    def test_info_with_path(self, tmp_path: Path) -> None:
        save_file = tmp_path / "test.save"
        save_file.write_bytes(b"")
        runner = CliRunner()
        with patch("sims4mcp.cli.load_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["info", str(save_file)])
        assert result.exit_code == 0


class TestSimsCommand:
    def test_sims_lists_all(self) -> None:
        runner = CliRunner()
        with patch("sims4mcp.cli._resolve_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["sims"])
        assert result.exit_code == 0
        assert "Test Sim" in result.output
        assert "Active" in result.output  # trait
        assert "Athlete" in result.output  # career

    def test_sims_by_id(self) -> None:
        runner = CliRunner()
        with patch("sims4mcp.cli._resolve_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["sims", "--sim-id", "1"])
        assert result.exit_code == 0
        assert "Test Sim" in result.output

    def test_sims_by_id_not_found(self) -> None:
        runner = CliRunner()
        with patch("sims4mcp.cli._resolve_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["sims", "--sim-id", "999"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()


class TestHouseholdsCommand:
    def test_households_output(self) -> None:
        runner = CliRunner()
        with patch("sims4mcp.cli._resolve_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["households"])
        assert result.exit_code == 0
        assert "Test Family" in result.output
        assert "Test Sim" in result.output

    def test_households_with_path(self, tmp_path: Path) -> None:
        save_file = tmp_path / "test.save"
        save_file.write_bytes(b"")
        runner = CliRunner()
        with patch("sims4mcp.cli.load_save", return_value=_make_mock_save()):
            result = runner.invoke(cli, ["households", str(save_file)])
        assert result.exit_code == 0


class TestHelp:
    def test_help_shows_commands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "info" in result.output
        assert "sims" in result.output
        assert "households" in result.output
