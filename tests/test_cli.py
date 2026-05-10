import json
from pathlib import Path

import pytest

from sru_generator import cli


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


def test_load_trade_data_exits_on_invalid_json(tmp_path: Path, capsys) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        cli.load_trade_data(str(path))

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error loading trade data" in captured.out


def test_main_info_command_writes_file(monkeypatch, capsys) -> None:
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
            "1234567890",
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
    assert "#ORGNR 1234567890" in written["content"]
    assert "John Doe" in written["content"]
    captured = capsys.readouterr()
    assert "Info file generated: custom-info.sru" in captured.out


def test_main_trades_command_merges_crypto_when_file_exists(
    tmp_path: Path, monkeypatch, capsys
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

    monkeypatch.setattr(
        cli,
        "read_crypto_sru_content",
        lambda path: [{"group_number": 1, "uppgifter": ["#UPPGIFT 3410 1"]}],
    )
    monkeypatch.setattr(
        cli,
        "merge_sru_groups",
        lambda stock_content, crypto_groups, full_name, personal_number, year: stock_content
        + "\n"
        + "\n".join(crypto_groups[0]["uppgifter"])
        + "\n#FIL_SLUT\n",
    )
    monkeypatch.setattr(
        cli,
        "write_sru_file",
        lambda file_path, content: written.update(
            {"path": file_path, "content": content}
        )
        or True,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "sru-generator",
            "trades",
            "--data",
            str(trade_path),
            "--personal-number",
            "1234567890",
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


def test_main_without_command_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["sru-generator"])

    cli.main()

    captured = capsys.readouterr()
    assert "Generate Swedish SRU files for tax reporting" in captured.out
