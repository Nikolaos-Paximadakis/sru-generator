"""Every example runs, and every SRU file it writes is complete."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.mark.parametrize(
    "example", sorted(p.name for p in EXAMPLES.glob("*.py")), ids=str
)
def test_example_runs_and_writes_complete_files(example: str, tmp_path: Path) -> None:
    source = (EXAMPLES / example).read_text(encoding="utf-8")
    if "import text_converters" in source or "from text_converters" in source:
        if importlib.util.find_spec("text_converters") is None:
            pytest.skip(
                "needs text-converters: uv run --with ../text_converters pytest"
            )
    for data in EXAMPLES.glob("*.json"):
        shutil.copy(data, tmp_path)
    result = subprocess.run(  # noqa: S603 -- fixed argv: this interpreter and a repo file
        [
            sys.executable,
            # Examples must not use deprecated API; the one allowed warning is the
            # bundled-converter fallback, which depends on what is installed.
            "-W",
            "error::DeprecationWarning",
            "-W",
            "ignore:sru-generator's bundled character converters:DeprecationWarning",
            str(EXAMPLES / example),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    written = sorted(tmp_path.glob("*.[sS][rR][uU]"))
    assert written, "the example wrote no SRU file"
    for path in written:
        text = path.read_bytes().decode("iso-8859-1")
        if "#BLANKETT " in text:
            assert text.endswith("#BLANKETTSLUT\n#FIL_SLUT\n"), path.name
        else:
            assert text.startswith("#DATABESKRIVNING_START\n"), path.name
            assert text.endswith("#MEDIELEV_SLUT\n"), path.name
