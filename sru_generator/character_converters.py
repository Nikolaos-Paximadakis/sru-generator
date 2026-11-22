"""
Character conversion by name, through the optional ``text-converters`` package.

SRU files are written in ISO-8859-1: Swedish letters (å, ä, ö) survive that encoding as
they are, but Greek and other non-Latin text does not, so it has to be transliterated
before it is written. sru-generator bundles no transliteration rules of its own: the
named converters come from ``text-converters``, installed with
``pip install "sru-generator[transliterate]"``. It is imported lazily, never at package
import time, so sru-generator itself keeps no runtime dependencies.

Builders accept any ``Callable[[str], str]``; a name is only a shortcut for one.
"""

import importlib

from .exceptions import ConfigurationError
from .models import CharacterConverter

#: The converter names sru-generator accepts (CLI choices, SRUConfig validation).
CONVERTER_NAMES: tuple[str, ...] = (
    "none",
    "greek",
    "swedish",
    "german",
    "french",
    "spanish",
)

#: How to get the named converters.
TEXT_CONVERTERS_INSTALL = 'pip install "sru-generator[transliterate]"'
#: A text-converters whose Greek converter does not give this is outdated (its old rules
#: wrote "THessalonikh Papadopoylos") and is refused. Checking behaviour rather than a
#: version number keeps working however that package numbers its releases.
_GREEK_PROBE = ("Θεσσαλονίκη Παπαδόπουλος", "Thessaloniki Papadopoulos")


def no_conversion(text: str) -> str:
    """Return the text unchanged."""
    return text


def _outdated(name: str) -> ConfigurationError:
    return ConfigurationError(
        f"The installed text-converters is outdated and cannot provide the {name!r} "
        f"converter; upgrade it: {TEXT_CONVERTERS_INSTALL} --upgrade",
        config_key="character_converter",
        config_value=name,
    )


def load_character_converter(name: str) -> CharacterConverter:
    """The converter registered under ``name``.

    "none" is the identity and imports nothing. Any other name comes from
    text-converters, imported lazily through importlib (so neither it nor its type
    information is needed at import time or under a type checker).

    Raises:
        ValueError: ``name`` is not one of ``CONVERTER_NAMES``.
        ConfigurationError: text-converters is not installed, or is outdated (its
            Greek converter fails the behaviour check).
    """
    if name not in CONVERTER_NAMES:
        available = ", ".join(CONVERTER_NAMES)
        raise ValueError(f"Unsupported language '{name}'. Available: {available}")
    if name == "none":
        return no_conversion
    try:
        module = importlib.import_module("text_converters")
    except ImportError as e:
        raise ConfigurationError(
            f"The {name!r} character converter needs text-converters: "
            f"{TEXT_CONVERTERS_INSTALL}",
            config_key="character_converter",
            config_value=name,
        ) from e
    factory: object = getattr(module, "get_character_converter", None)
    if not callable(factory):
        raise _outdated(name)
    greek: object = factory("greek")
    if not callable(greek) or greek(_GREEK_PROBE[0]) != _GREEK_PROBE[1]:
        raise _outdated(name)
    loaded: object = factory(name)
    if not callable(loaded):
        raise _outdated(name)

    def converter(text: str) -> str:
        result: object = loaded(text)
        if not isinstance(result, str):
            raise TypeError(
                f"text_converters' {name!r} converter returned "
                f"{type(result).__name__}, not str"
            )
        return result

    return converter


__all__ = [
    "CONVERTER_NAMES",
    "TEXT_CONVERTERS_INSTALL",
    "load_character_converter",
    "no_conversion",
]
