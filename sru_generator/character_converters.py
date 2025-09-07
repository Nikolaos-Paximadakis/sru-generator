"""
Character conversion utilities for different languages.
This module now imports from the shared text_converters package.
"""

# Import from the shared text_converters package
import sys
import os

# Add the text_converters package to the path
text_converters_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'text_converters')
if text_converters_path not in sys.path:
    sys.path.insert(0, text_converters_path)

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
