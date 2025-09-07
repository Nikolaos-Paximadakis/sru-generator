"""
Character conversion utilities for different languages.
This module now imports from the shared text_converters package.
"""

import os
import sys

# Add the text_converters package to the path
text_converters_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "..", "text_converters"
)
if text_converters_path not in sys.path:
    sys.path.insert(0, text_converters_path)

# Import from the shared text_converters package
try:
    from character_converters import (
        convert_greek_characters_to_english,
        convert_swedish_characters_to_english,
        convert_german_characters_to_english,
        convert_french_characters_to_english,
        convert_spanish_characters_to_english,
        no_conversion,
        CHARACTER_CONVERTERS,
        get_character_converter,
    )
except ImportError:
    # Fallback if text_converters is not available
    def convert_greek_characters_to_english(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    def convert_swedish_characters_to_english(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    def convert_german_characters_to_english(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    def convert_french_characters_to_english(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    def convert_spanish_characters_to_english(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    def no_conversion(text: str) -> str:
        """Fallback: return text unchanged."""
        return text

    CHARACTER_CONVERTERS = {}

    def get_character_converter(converter_name: str):  # pylint: disable=unused-argument
        """Fallback: return no_conversion function."""
        # converter_name is ignored in fallback mode
        return no_conversion


# Re-export for backward compatibility
__all__ = [
    "convert_greek_characters_to_english",
    "convert_swedish_characters_to_english",
    "convert_german_characters_to_english",
    "convert_french_characters_to_english",
    "convert_spanish_characters_to_english",
    "no_conversion",
    "CHARACTER_CONVERTERS",
    "get_character_converter",
]
