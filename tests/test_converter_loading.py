"""load_character_converter: text-converters when installed, else the bundled copy."""

import subprocess
import sys
import types
import warnings
from collections.abc import Callable

import pytest

import sru_generator
from sru_generator import character_converters as bundled
from sru_generator.character_converters import (
    BUNDLED_CONVERTERS_WARNING,
    CONVERTER_NAMES,
    load_character_converter,
    resolve_character_converter,
)


def _fake_text_converters(
    monkeypatch: pytest.MonkeyPatch, *, outdated: bool = False
) -> list[str]:
    """Install a fake text_converters module; return the names it was asked for.

    Its "greek" converter passes the loader's behaviour check unless ``outdated``; the
    other names return a marker so tests can see which implementation ran.
    """
    asked: list[str] = []
    probe_in, probe_out = bundled._GREEK_PROBE

    def get_character_converter(name: str) -> Callable[[str], str]:
        asked.append(name)
        if name == "greek":
            answer = "THessalonikh Papadopoylos" if outdated else probe_out
            return lambda text: answer if text == probe_in else f"<greek:{text}>"
        return lambda text: f"<{name}:{text}>"

    module = types.ModuleType("text_converters")
    module.__dict__["__version__"] = "0.1.0"
    module.__dict__["get_character_converter"] = get_character_converter
    monkeypatch.setitem(sys.modules, "text_converters", module)
    return asked


def _no_text_converters(monkeypatch: pytest.MonkeyPatch) -> None:
    # None in sys.modules makes the import raise ImportError, as if not installed.
    monkeypatch.setitem(sys.modules, "text_converters", None)


def test_text_converters_is_used_when_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _fake_text_converters(monkeypatch)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        converter = load_character_converter("greek")
    assert converter("Ελλάδα") == "<greek:Ελλάδα>"
    assert "greek" in asked


def test_bundled_copy_with_a_warning_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_text_converters(monkeypatch)
    with pytest.warns(DeprecationWarning, match="removed in 2.0") as caught:
        converter = load_character_converter("greek")
    assert converter("Θεσσαλονίκη") == "Thessaloniki"
    assert str(caught[0].message) == BUNDLED_CONVERTERS_WARNING
    assert "text-converters.git" in BUNDLED_CONVERTERS_WARNING


def test_an_outdated_text_converters_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Old rules (THessalonikh) fail the behaviour check; the bundled copy is better."""
    _fake_text_converters(monkeypatch, outdated=True)
    with pytest.warns(DeprecationWarning):
        converter = load_character_converter("greek")
    assert converter("Θεσσαλονίκη") == "Thessaloniki"


def test_none_imports_nothing_and_does_not_warn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _fake_text_converters(monkeypatch)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        converter = load_character_converter("none")
    assert converter("Åsa Ελλάδα") == "Åsa Ελλάδα"
    assert asked == []
    _no_text_converters(monkeypatch)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert load_character_converter("none")("x") == "x"


def test_unknown_names_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_text_converters(monkeypatch)
    with pytest.raises(ValueError, match="Unsupported language"):
        load_character_converter("klingon")


def test_resolve_reports_the_source_without_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_text_converters(monkeypatch)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert resolve_character_converter("swedish")[1] is True
        assert resolve_character_converter("none")[1] is False
    _fake_text_converters(monkeypatch)
    assert resolve_character_converter("swedish")[1] is False


def test_a_converter_returning_a_non_string_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_in, probe_out = bundled._GREEK_PROBE

    def converters(name: str) -> Callable[[str], object]:
        return lambda text: probe_out if text == probe_in else 42

    module = types.ModuleType("text_converters")
    module.__dict__["get_character_converter"] = converters
    monkeypatch.setitem(sys.modules, "text_converters", module)
    with pytest.raises(TypeError, match="not str"):
        load_character_converter("greek")("x")


def test_old_top_level_names_still_work_with_a_warning() -> None:
    for name in (
        "CHARACTER_CONVERTERS",
        "convert_greek_characters_to_english",
        "get_character_converter",
        "no_conversion",
    ):
        with pytest.warns(DeprecationWarning, match=f"sru_generator.{name}"):
            value = getattr(sru_generator, name)
        assert value is getattr(bundled, name)
        assert name not in sru_generator.__all__
    assert "load_character_converter" in sru_generator.__all__


def test_importing_the_package_does_not_warn() -> None:
    # A fresh interpreter: the deprecated names must warn only when used.
    code = "import sru_generator; from sru_generator import load_character_converter"
    subprocess.run(  # noqa: S603 -- fixed argv: this interpreter and a literal
        [sys.executable, "-W", "error::DeprecationWarning", "-c", code], check=True
    )


PARITY_SAMPLES = (
    "Θεσσαλονίκη Χανιά Ηράκλειο Παπαδόπουλος ΑΘΗΝΑ ΚΑΛΥΨ Χ. Ούζο Υδρα",
    "Åsa Öberg Göteborg É è Ü Ñ Ç",
    "Größe Straße Ärger Öl Übel",
    "François Ça Éé Àà Ôô Ÿ cœur Œuvre ex æquo Ægir",
    "Niño Señor Ángel Íñigo Úrsula",
)


def test_parity_with_the_real_text_converters() -> None:
    """Compares with the real package: `uv run --with ../text_converters pytest`."""
    real = pytest.importorskip("text_converters")
    if (
        real.get_character_converter("greek")(bundled._GREEK_PROBE[0])
        != (bundled._GREEK_PROBE[1])
    ):
        pytest.skip("an outdated text-converters is installed")
    for name in CONVERTER_NAMES:
        external = real.get_character_converter(name)
        local = bundled.CHARACTER_CONVERTERS[name]
        for sample in PARITY_SAMPLES:
            assert external(sample) == local(sample), (name, sample)
    assert set(real.CHARACTER_CONVERTERS) == set(CONVERTER_NAMES)
