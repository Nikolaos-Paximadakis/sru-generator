"""load_character_converter: named converters come from text-converters, or raise."""

import importlib
import os
import subprocess
import sys
import types
from collections.abc import Callable

import pytest

import sru_generator
from sru_generator import ConfigurationError, SRUGeneratorError
from sru_generator import character_converters as loader
from sru_generator.character_converters import (
    CONVERTER_NAMES,
    TEXT_CONVERTERS_INSTALL,
    load_character_converter,
)


def _fake_text_converters(
    monkeypatch: pytest.MonkeyPatch, *, outdated: bool = False
) -> list[str]:
    """Install a fake text_converters module; return the names it was asked for.

    Its "greek" converter passes the loader's behaviour check unless ``outdated``; the
    other names return a marker so tests can see which implementation ran.
    """
    asked: list[str] = []
    probe_in, probe_out = loader._GREEK_PROBE

    def get_character_converter(name: str) -> Callable[[str], str]:
        asked.append(name)
        if name == "greek":
            answer = "THessalonikh Papadopoylos" if outdated else probe_out
            return lambda text: answer if text == probe_in else f"<greek:{text}>"
        return lambda text: f"<{name}:{text}>"

    module = types.ModuleType("text_converters")
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
    converter = load_character_converter("swedish")
    assert converter("Åsa") == "<swedish:Åsa>"
    assert "swedish" in asked


def test_a_missing_text_converters_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_text_converters(monkeypatch)
    with pytest.raises(ConfigurationError) as caught:
        load_character_converter("greek")
    error = caught.value
    assert isinstance(error, SRUGeneratorError)
    assert "'greek'" in str(error)
    assert str(error).endswith(TEXT_CONVERTERS_INSTALL)
    assert TEXT_CONVERTERS_INSTALL == 'pip install "sru-generator[transliterate]"'
    assert isinstance(error.__cause__, ImportError)
    assert error.config_key == "character_converter"
    assert error.config_value == "greek"


def test_an_outdated_text_converters_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Old rules (THessalonikh) fail the behaviour check."""
    _fake_text_converters(monkeypatch, outdated=True)
    with pytest.raises(ConfigurationError, match=r"outdated.*--upgrade"):
        load_character_converter("greek")


@pytest.mark.parametrize(
    "module_contents",
    [
        {},  # no get_character_converter at all
        {"get_character_converter": "not callable"},
        {"get_character_converter": lambda name: None},  # greek is not callable
    ],
    ids=["missing-factory", "factory-not-callable", "converter-not-callable"],
)
def test_a_text_converters_without_the_contract_is_refused(
    monkeypatch: pytest.MonkeyPatch, module_contents: dict[str, object]
) -> None:
    module = types.ModuleType("text_converters")
    module.__dict__.update(module_contents)
    monkeypatch.setitem(sys.modules, "text_converters", module)
    with pytest.raises(ConfigurationError, match="outdated"):
        load_character_converter("swedish")


def test_a_non_callable_named_converter_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_in, probe_out = loader._GREEK_PROBE

    def converters(name: str) -> object:
        if name == "greek":
            return lambda text: probe_out if text == probe_in else text
        return None

    module = types.ModuleType("text_converters")
    module.__dict__["get_character_converter"] = converters
    monkeypatch.setitem(sys.modules, "text_converters", module)
    with pytest.raises(ConfigurationError, match="'french'"):
        load_character_converter("french")


def test_none_imports_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _fake_text_converters(monkeypatch)
    converter = load_character_converter("none")
    assert converter("Åsa Ελλάδα") == "Åsa Ελλάδα"
    assert asked == []
    _no_text_converters(monkeypatch)
    assert load_character_converter("none")("x") == "x"


def test_unknown_names_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_text_converters(monkeypatch)
    with pytest.raises(ValueError, match="Unsupported language"):
        load_character_converter("klingon")


def test_a_converter_returning_a_non_string_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_in, probe_out = loader._GREEK_PROBE

    def converters(name: str) -> Callable[[str], object]:
        return lambda text: probe_out if text == probe_in else 42

    module = types.ModuleType("text_converters")
    module.__dict__["get_character_converter"] = converters
    monkeypatch.setitem(sys.modules, "text_converters", module)
    with pytest.raises(TypeError, match="not str"):
        load_character_converter("greek")("x")


@pytest.mark.parametrize(
    "name",
    [
        "CHARACTER_CONVERTERS",
        "convert_greek_characters_to_english",
        "get_character_converter",
        "no_conversion",
        "resolve_character_converter",
    ],
)
def test_the_removed_top_level_names_are_gone(name: str) -> None:
    assert not hasattr(sru_generator, name)
    assert not hasattr(loader, name) or name == "no_conversion"
    assert name not in sru_generator.__all__


def test_load_character_converter_is_public() -> None:
    assert "load_character_converter" in sru_generator.__all__


def test_importing_the_package_does_not_import_text_converters() -> None:
    code = (
        "import sys, sru_generator; "
        "assert 'text_converters' not in sys.modules, 'imported eagerly'"
    )
    subprocess.run(  # noqa: S603 -- fixed argv: this interpreter and a literal
        [sys.executable, "-W", "error::DeprecationWarning", "-c", code], check=True
    )


#: Set in CI's text-converters job: a missing or outdated package fails, never skips.
REQUIRE_TEXT_CONVERTERS = os.environ.get("SRU_REQUIRE_TEXT_CONVERTERS") == "1"

#: One sample per converter, with the result text-converters' contract promises.
CONTRACT_SAMPLES = {
    "none": ("Åsa Ελλάδα", "Åsa Ελλάδα"),
    "greek": ("Θεσσαλονίκη ΑΘΗΝΑ Παπαδόπουλος", "Thessaloniki ATHINA Papadopoulos"),
    "swedish": ("Åsa Öberg", "Asa Oberg"),
    "german": ("Größe", "Groesse"),
    "french": ("cœur Œuvre", "coeur Oeuvre"),
    "spanish": ("Niño", "Nino"),
}


def test_contract_with_the_real_text_converters() -> None:
    """The loader against the real package: `uv run --with text-converters pytest`."""
    if REQUIRE_TEXT_CONVERTERS:
        real = importlib.import_module("text_converters")  # must exist here
    else:
        real = pytest.importorskip("text_converters")
    assert set(real.CHARACTER_CONVERTERS) == set(CONVERTER_NAMES)
    assert set(CONTRACT_SAMPLES) == set(CONVERTER_NAMES)
    for name, (sample, expected) in CONTRACT_SAMPLES.items():
        assert load_character_converter(name)(sample) == expected, name
