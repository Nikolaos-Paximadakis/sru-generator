import json
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest

from sru_generator import cli
from sru_generator.models import CryptoSRUGroup


def test_load_trade_data_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "trades.json"
    path.write_text(
        json.dumps(
            [
                {
                    "quantity": 10,
                    "stock": "Test Stock",
                    "net value": 1000,
                    "total net value of purchase": 900,
                    "profit/loss": 100,
                }
            ]
        ),
        encoding="utf-8",
    )

    payload = cli.load_trade_data(str(path))

    assert payload[0]["stock"] == "Test Stock"
    assert payload[0]["profit/loss"] == 100


def test_load_trade_data_exits_on_invalid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        cli.load_trade_data(str(path))

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error loading trade data" in captured.out


def test_main_info_command_writes_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    written: dict[str, str] = {}

    def fake_write_sru_file(file_path: str, content: str) -> bool:
        written["path"] = file_path
        written["content"] = content
        return True

    monkeypatch.setattr(cli, "write_sru_file", fake_write_sru_file)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "info",
            "--personal-number",
            "198112189876",
            "--full-name",
            "John Doe",
            "--postal-code",
            "12345",
            "--city-name",
            "Stockholm",
            "--output",
            "custom-info.sru",
        ],
    )

    cli.main()

    assert written["path"] == "custom-info.sru"
    assert "#ORGNR 198112189876" in written["content"]
    assert "John Doe" in written["content"]
    captured = capsys.readouterr()
    assert "Info file generated: custom-info.sru" in captured.out


def test_main_trades_command_merges_crypto_when_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    trade_path = tmp_path / "trades.json"
    trade_path.write_text(
        json.dumps(
            [
                {
                    "quantity": 4,
                    "stock": "Test Stock",
                    "net value": 542.4,
                    "total net value of purchase": 444.0,
                    "profit/loss": 98.4,
                }
            ]
        ),
        encoding="utf-8",
    )
    crypto_path = tmp_path / "crypto.sru"
    crypto_path.write_text("dummy", encoding="utf-8")
    written: dict[str, str] = {}

    def fake_read(path: str) -> list[CryptoSRUGroup]:
        return [{"group_number": 1, "uppgifter": ["#UPPGIFT 3410 1"]}]

    def fake_merge(
        stock_content: str,
        crypto_groups: list[CryptoSRUGroup],
        full_name: str,
        personal_number: str,
        year: int,
    ) -> str:
        return (
            stock_content
            + "\n"
            + "\n".join(crypto_groups[0]["uppgifter"])
            + "\n#FIL_SLUT\n"
        )

    def fake_write(file_path: str, content: str) -> bool:
        written.update({"path": file_path, "content": content})
        return True

    monkeypatch.setattr(cli, "read_crypto_sru_content", fake_read)
    monkeypatch.setattr(cli, "merge_sru_groups", fake_merge)
    monkeypatch.setattr(cli, "write_sru_file", fake_write)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(trade_path),
            "--personal-number",
            "198112189876",
            "--full-name",
            "John Doe",
            "--year",
            "2024",
            "--output",
            "blanketter.sru",
            "--crypto-file",
            str(crypto_path),
            "--character-conversion",
            "none",
        ],
    )

    cli.main()

    assert written["path"] == "blanketter.sru"
    assert "#UPPGIFT 3410 1" in written["content"]
    captured = capsys.readouterr()
    assert "Trade file generated: blanketter.sru" in captured.out


def test_main_without_command_prints_help(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["sru-generator"])

    cli.main()

    captured = capsys.readouterr()
    assert "Generate Swedish SRU files" in captured.out


def test_main_trades_command_without_crypto_ends_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    trade_path = tmp_path / "trades.json"
    trade_path.write_text(
        json.dumps(
            [
                {
                    "quantity": 4,
                    "stock": "Test Stock",
                    "net value": 542.4,
                    "total net value of purchase": 444.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "blanketter.sru"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(trade_path),
            "--personal-number",
            "198112189876",
            "--full-name",
            "John Doe",
            "--output",
            str(output),
        ],
    )

    cli.main()

    content = output.read_bytes().decode("iso-8859-1")
    assert content.endswith("#BLANKETTSLUT\n#FIL_SLUT\n")
    assert "#UPPGIFT 3100 4\n" in content


def test_main_trades_command_rejects_invalid_trades(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trade_path = tmp_path / "trades.json"
    trade_path.write_text(
        json.dumps([{"quantity": -1, "stock": "X"}]), encoding="utf-8"
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(trade_path),
            "--personal-number",
            "198112189876",
            "--full-name",
            "John Doe",
            "--output",
            str(tmp_path / "out.sru"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert "Invalid trade data" in str(exc_info.value.code)
    assert not (tmp_path / "out.sru").exists()


def _trades_file(tmp_path: Path) -> Path:
    path = tmp_path / "trades.json"
    path.write_text(
        json.dumps(
            [
                {
                    "quantity": 1,
                    "stock": "ABB",
                    "net value": 100,
                    "total net value of purchase": 50,
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_personal_details_come_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "out.sru"
    monkeypatch.setenv("SRU_PERSONAL_NUMBER", "198112189876")
    monkeypatch.setenv("SRU_FULL_NAME", "Åsa Öberg")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(_trades_file(tmp_path)),
            "--year",
            "2025",
            "--output",
            str(output),
        ],
    )

    cli.main()

    content = output.read_bytes().decode("iso-8859-1")
    assert "#IDENTITET 198112189876 " in content
    assert "#NAMN Åsa Öberg\n" in content
    assert "#BLANKETT K4-2025P4\n" in content


def test_option_beats_environment_beats_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = tmp_path / "me.json"
    profile.write_text(
        json.dumps(
            {
                "personal_number": "191212121212",
                "full_name": "From Profile",
                "postal_code": "11122",
                "city_name": "Göteborg",
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "INFO.SRU"
    monkeypatch.setenv("SRU_FULL_NAME", "From Env")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "info",
            "--profile",
            str(profile),
            "--personal-number",
            "198112189876",
            "--output",
            str(output),
        ],
    )

    cli.main()

    content = output.read_bytes().decode("iso-8859-1")
    assert "#ORGNR 198112189876\n" in content
    assert "#NAMN From Env\n" in content
    assert "#POSTORT Göteborg\n" in content


def test_missing_personal_number_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SRU_PERSONAL_NUMBER", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(_trades_file(tmp_path)),
            "--full-name",
            "A",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2
    assert "SRU_PERSONAL_NUMBER" in capsys.readouterr().err


def test_info_command_validates_personal_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "info",
            "--personal-number",
            "12-34",
            "--full-name",
            "A",
            "--postal-code",
            "11122",
            "--city-name",
            "B",
            "--output",
            str(tmp_path / "INFO.SRU"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert "Invalid personal details" in str(exc_info.value.code)


def test_trade_json_numbers_are_read_as_decimal(tmp_path: Path) -> None:
    path = tmp_path / "trades.json"
    path.write_text(
        '[{"quantity": 1, "stock": "A", "net value": 100.10,'
        ' "total net value of purchase": 300.00000000000006}]',
        encoding="utf-8",
    )
    (row,) = cli.load_trade_data(str(path))
    assert row["net value"] == Decimal("100.10")
    assert isinstance(row["total net value of purchase"], Decimal)


def test_an_impossible_year_is_a_clean_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(_trades_file(tmp_path)),
            "--personal-number",
            "198112189876",
            "--full-name",
            "A",
            "--year",
            "25",
            "--output",
            str(tmp_path / "out.sru"),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert "four-digit income year" in str(exc_info.value.code)
    assert not (tmp_path / "out.sru").exists()


@pytest.mark.parametrize("content", ['{"not": "a list"}', '[{"quantity": 1}, 7]'])
def test_trade_json_of_the_wrong_shape(tmp_path: Path, content: str) -> None:
    path = tmp_path / "trades.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cli.load_trade_data(str(path))
    assert "expected a JSON list of objects" in str(exc_info.value.code)


@pytest.mark.parametrize(
    ("content", "message"),
    [("{not json", "Error loading profile"), ("[1, 2]", "must be a JSON object")],
)
def test_bad_profile_files(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "profile.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        cli.load_profile(str(path))
    assert message in str(exc_info.value.code)


@pytest.mark.parametrize("command", ["info", "trades"])
def test_a_failed_write_exits_with_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    monkeypatch.setattr(cli, "write_sru_file", lambda path, content: False)
    argv = [
        "sru-generator",
        command,
        "--personal-number",
        "198112189876",
        "--full-name",
        "A",
        "--output",
        str(tmp_path / "out.sru"),
    ]
    if command == "info":
        argv += ["--postal-code", "11122", "--city-name", "B"]
    else:
        argv += ["--data", str(_trades_file(tmp_path)), "--year", "2025"]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert "Failed to write" in str(exc_info.value.code)


def _run_trades_with_conversion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conversion: str
) -> str:
    output = tmp_path / "out.sru"
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(_trades_file(tmp_path)),
            "--personal-number",
            "198112189876",
            "--full-name",
            "A",
            "--year",
            "2025",
            "--character-conversion",
            conversion,
            "--output",
            str(output),
        ],
    )
    cli.main()
    return output.read_bytes().decode("iso-8859-1")


def test_cli_notes_the_bundled_converter_on_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(sys.modules, "text_converters", None)  # not installed
    _run_trades_with_conversion(tmp_path, monkeypatch, "greek")
    err = capsys.readouterr().err
    assert "bundled 'greek' converter" in err
    assert "Install text-converters: pip install text-converters\n" in err


def test_cli_is_quiet_with_text_converters_or_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = types.ModuleType("text_converters")
    module.__dict__["get_character_converter"] = lambda name: (
        lambda text: (
            "Thessaloniki Papadopoulos"  # passes the loader's behaviour check
            if text == "Θεσσαλονίκη Παπαδόπουλος"
            else text + "-tc"
        )
    )
    monkeypatch.setitem(sys.modules, "text_converters", module)
    content = _run_trades_with_conversion(tmp_path, monkeypatch, "greek")
    assert "#UPPGIFT 3101 ABB-tc\n" in content  # text-converters' converter ran
    assert "bundled" not in capsys.readouterr().err
    _run_trades_with_conversion(tmp_path, monkeypatch, "none")
    assert "bundled" not in capsys.readouterr().err
