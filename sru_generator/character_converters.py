"""
Character conversion utilities for different languages.

Each converter maps letters with diacritics (or a non-Latin script) to plain ASCII
equivalents. This matters for SRU files, which are written in ISO-8859-1: Swedish
letters (å, ä, ö) survive that encoding as they are, but Greek and other non-Latin
text does not, so it has to be transliterated before it is written.

Conversion now belongs to the separate ``text-converters`` package. Use
``load_character_converter(name)``: it imports ``text_converters`` lazily when it is
installed, and otherwise falls back to the copy bundled below, with a
``DeprecationWarning``. The bundled copy will be removed in 2.0. sru-generator itself
keeps no runtime dependencies: ``text-converters`` is optional and never imported at
package import time.
"""

import importlib
import warnings
from collections.abc import Callable

from .models import CharacterConverter


def _translate(text: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(char, char) for char in text)


_GREEK_TO_ENGLISH: dict[str, str] = {
    "Α": "A",
    "Ά": "A",
    "Β": "B",
    "Γ": "G",
    "Δ": "D",
    "Ε": "E",
    "Έ": "E",
    "Ζ": "Z",
    "Η": "I",
    "Ή": "I",
    "Θ": "TH",
    "Ι": "I",
    "Ί": "I",
    "Ϊ": "I",
    "Κ": "K",
    "Λ": "L",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "X",
    "Ο": "O",
    "Ό": "O",
    "Π": "P",
    "Ρ": "R",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Ύ": "Y",
    "Ϋ": "Y",
    "Φ": "F",
    "Χ": "CH",
    "Ψ": "PS",
    "Ω": "O",
    "Ώ": "O",
    "α": "a",
    "ά": "a",
    "β": "b",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "έ": "e",
    "ζ": "z",
    "η": "i",
    "ή": "i",
    "θ": "th",
    "ι": "i",
    "ί": "i",
    "ϊ": "i",
    "ΐ": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "ό": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "ς": "s",
    "τ": "t",
    "υ": "y",
    "ύ": "y",
    "ϋ": "y",
    "ΰ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
    "ώ": "o",
}

_SWEDISH_TO_ENGLISH: dict[str, str] = {
    "Å": "A",
    "å": "a",
    "Ä": "A",
    "ä": "a",
    "Ö": "O",
    "ö": "o",
    "É": "E",
    "é": "e",
    "È": "E",
    "è": "e",
    "Ü": "U",
    "ü": "u",
    "Ñ": "N",
    "ñ": "n",
    "Ç": "C",
    "ç": "c",
}

_GERMAN_TO_ENGLISH: dict[str, str] = {
    "Ä": "Ae",
    "ä": "ae",
    "Ö": "Oe",
    "ö": "oe",
    "Ü": "Ue",
    "ü": "ue",
    "ß": "ss",
    "É": "E",
    "é": "e",
    "È": "E",
    "è": "e",
    "À": "A",
    "à": "a",
    "Ò": "O",
    "ò": "o",
    "Ù": "U",
    "ù": "u",
}

_FRENCH_TO_ENGLISH: dict[str, str] = {
    "À": "A",
    "à": "a",
    "Á": "A",
    "á": "a",
    "Â": "A",
    "â": "a",
    "Ä": "A",
    "ä": "a",
    "Ç": "C",
    "ç": "c",
    "É": "E",
    "é": "e",
    "È": "E",
    "è": "e",
    "Ê": "E",
    "ê": "e",
    "Ë": "E",
    "ë": "e",
    "Î": "I",
    "î": "i",
    "Ï": "I",
    "ï": "i",
    "Ô": "O",
    "ô": "o",
    "Ö": "O",
    "ö": "o",
    "Ù": "U",
    "ù": "u",
    "Ú": "U",
    "ú": "u",
    "Û": "U",
    "û": "u",
    "Ü": "U",
    "ü": "u",
    "Ÿ": "Y",
    "ÿ": "y",
    "Æ": "Ae",
    "æ": "ae",
    "Œ": "Oe",
    "œ": "oe",
}

_SPANISH_TO_ENGLISH: dict[str, str] = {
    "Á": "A",
    "á": "a",
    "É": "E",
    "é": "e",
    "Í": "I",
    "í": "i",
    "Ó": "O",
    "ó": "o",
    "Ú": "U",
    "ú": "u",
    "Ñ": "N",
    "ñ": "n",
    "Ü": "U",
    "ü": "u",
}


# Capital letters whose Latin form has two letters. "TH" is right inside an all-capitals
# word (ΑΘΗΝΑ -> ATHINA) but wrong at the start of a normal one (Θεσσαλονίκη ->
# Thessaloniki), so the case of the second letter depends on the neighbours.
_GREEK_CAPITAL_DIGRAPHS = {"Θ": "TH", "Χ": "CH", "Ψ": "PS"}
# The pair ου is written "ou" (Παπαδόπουλος -> Papadopoulos), not "oy".
_GREEK_OMICRON = frozenset("οόΟΌ")
_GREEK_UPSILON = {"υ": "u", "ύ": "u", "Υ": "U", "Ύ": "U"}


def convert_greek_characters_to_english(text: str) -> str:
    """Transliterate Greek letters (with or without tonos) to Latin letters.

    Letter by letter, close to the Greek standard ELOT 743 for single letters: η is
    "i" (Θεσσαλονίκη -> Thessaloniki), ου is "ou" (Παπαδόπουλος -> Papadopoulos),
    and Θ, Χ, Ψ give "Th", "Ch", "Ps" unless they stand in an all-capitals word
    (ΑΘΗΝΑ -> ATHINA). The other letter pairs ELOT treats specially (αυ, ευ, μπ,
    γγ, ...) are not handled; see the README for a library-based alternative.
    """
    result: list[str] = []
    for index, char in enumerate(text):
        preceding = text[index - 1] if index > 0 else ""
        if char in _GREEK_UPSILON and preceding in _GREEK_OMICRON:
            result.append(_GREEK_UPSILON[char])
            continue
        digraph = _GREEK_CAPITAL_DIGRAPHS.get(char)
        if digraph is None:
            result.append(_GREEK_TO_ENGLISH.get(char, char))
            continue
        following = text[index + 1] if index + 1 < len(text) else ""
        in_capitals_word = following.isupper() or (
            not following.isalpha() and preceding.isupper()
        )
        result.append(digraph if in_capitals_word else digraph.capitalize())
    return "".join(result)


def convert_swedish_characters_to_english(text: str) -> str:
    """Replace Swedish (and a few common European) diacritics with plain letters."""
    return _translate(text, _SWEDISH_TO_ENGLISH)


def convert_german_characters_to_english(text: str) -> str:
    """Replace German umlauts and ß with their conventional digraphs (ä -> ae)."""
    return _translate(text, _GERMAN_TO_ENGLISH)


def convert_french_characters_to_english(text: str) -> str:
    """Replace French diacritics with plain letters."""
    return _translate(text, _FRENCH_TO_ENGLISH)


def convert_spanish_characters_to_english(text: str) -> str:
    """Replace Spanish diacritics with plain letters."""
    return _translate(text, _SPANISH_TO_ENGLISH)


def no_conversion(text: str) -> str:
    """Return the text unchanged."""
    return text


CHARACTER_CONVERTERS: dict[str, Callable[[str], str]] = {
    "none": no_conversion,
    "greek": convert_greek_characters_to_english,
    "swedish": convert_swedish_characters_to_english,
    "german": convert_german_characters_to_english,
    "french": convert_french_characters_to_english,
    "spanish": convert_spanish_characters_to_english,
}


def get_character_converter(language: str = "none") -> Callable[[str], str]:
    """
    Return the converter registered under ``language``.

    Raises:
        ValueError: if ``language`` is not one of ``CHARACTER_CONVERTERS``.
    """
    if language not in CHARACTER_CONVERTERS:
        available = ", ".join(CHARACTER_CONVERTERS)
        raise ValueError(f"Unsupported language '{language}'. Available: {available}")
    return CHARACTER_CONVERTERS[language]


#: The converter names sru-generator accepts (CLI choices, SRUConfig validation).
CONVERTER_NAMES: tuple[str, ...] = (
    "none",
    "greek",
    "swedish",
    "german",
    "french",
    "spanish",
)

TEXT_CONVERTERS_SOURCE = (
    "git+https://github.com/Nikolaos-Paximadakis/text-converters.git"
)
#: A text-converters whose Greek converter does not give this is outdated (its old rules
#: wrote "THessalonikh Papadopoylos") and is not used. Checking behaviour rather than a
#: version number keeps working however that package numbers its releases.
_GREEK_PROBE = ("Θεσσαλονίκη Παπαδόπουλος", "Thessaloniki Papadopoulos")
BUNDLED_CONVERTERS_WARNING = (
    "sru-generator's bundled character converters will be removed in 2.0; "
    f"install text-converters from {TEXT_CONVERTERS_SOURCE}"
)


def _from_text_converters(name: str) -> CharacterConverter | None:
    """The converter from an installed, current text-converters, or None.

    Imported lazily through importlib, so the package never needs text-converters
    (or its type information) at import time or under a type checker.
    """
    try:
        module = importlib.import_module("text_converters")
    except ImportError:
        return None
    factory: object = getattr(module, "get_character_converter", None)
    if not callable(factory):
        return None
    greek: object = factory("greek")
    if not callable(greek) or greek(_GREEK_PROBE[0]) != _GREEK_PROBE[1]:
        return None  # outdated rules: the bundled copy is better
    loaded: object = factory(name)
    if not callable(loaded):
        return None

    def converter(text: str) -> str:
        result: object = loaded(text)
        if not isinstance(result, str):
            raise TypeError(
                f"text_converters' {name!r} converter returned "
                f"{type(result).__name__}, not str"
            )
        return result

    return converter


def resolve_character_converter(name: str) -> tuple[CharacterConverter, bool]:
    """``(converter, from_bundled_copy)`` for ``name``, without warning.

    "none" is the identity and imports nothing. Any other name comes from an installed
    current text-converters when available, else from the bundled copy (second item
    True). Raises ``ValueError`` for a name not in ``CONVERTER_NAMES``.
    """
    if name not in CONVERTER_NAMES:
        available = ", ".join(CONVERTER_NAMES)
        raise ValueError(f"Unsupported language '{name}'. Available: {available}")
    if name == "none":
        return no_conversion, False
    external = _from_text_converters(name)
    if external is not None:
        return external, False
    return CHARACTER_CONVERTERS[name], True


def load_character_converter(name: str) -> CharacterConverter:
    """The converter for ``name`` (see ``resolve_character_converter``).

    Warns with ``DeprecationWarning`` when it falls back to the bundled copy.
    """
    converter, from_bundled = resolve_character_converter(name)
    if from_bundled:
        warnings.warn(BUNDLED_CONVERTERS_WARNING, DeprecationWarning, stacklevel=2)
    return converter


__all__ = [
    "BUNDLED_CONVERTERS_WARNING",
    "CHARACTER_CONVERTERS",
    "CONVERTER_NAMES",
    "convert_french_characters_to_english",
    "convert_german_characters_to_english",
    "convert_greek_characters_to_english",
    "convert_spanish_characters_to_english",
    "convert_swedish_characters_to_english",
    "get_character_converter",
    "load_character_converter",
    "no_conversion",
    "resolve_character_converter",
]
