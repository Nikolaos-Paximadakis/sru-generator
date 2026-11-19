"""
Command-line interface for SRU Generator.

Personal details can come from command-line options, environment variables or a
JSON profile file, in that order of precedence. Prefer the environment or a profile
for the personal number: command-line arguments are saved in shell history and are
visible to other users in the process list.
"""

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TypeGuard

from .character_converters import (
    CONVERTER_NAMES,
    TEXT_CONVERTERS_INSTALL,
    resolve_character_converter,
)
from .exceptions import SRUGeneratorError
from .sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
    read_crypto_sru_content,
    write_sru_file,
)
from .validators import PersonalInfoValidator, validate_trade_data

DISCLAIMER_URL = (
    "https://github.com/Nikolaos-Paximadakis/sru-generator/blob/main/DISCLAIMER.md"
)

# field -> (command-line option, environment variable)
PERSONAL_FIELDS = {
    "personal_number": ("--personal-number", "SRU_PERSONAL_NUMBER"),
    "full_name": ("--full-name", "SRU_FULL_NAME"),
    "postal_code": ("--postal-code", "SRU_POSTAL_CODE"),
    "city_name": ("--city-name", "SRU_CITY_NAME"),
}


def load_trade_data(file_path: str) -> list[Mapping[str, object]]:
    """Load trade data from a JSON file: a list of objects, one per sale."""
    try:
        with Path(file_path).open(encoding="utf-8") as f:
            # Decimal, not float: money must not pick up binary noise on the way in.
            data: object = json.load(f, parse_float=Decimal)
    except Exception as e:
        print(f"Error loading trade data from {file_path}: {e}")
        sys.exit(1)
    if not _is_json_array(data):
        sys.exit(f"Invalid trade data in {file_path}: expected a JSON list of objects")
    rows: list[Mapping[str, object]] = []
    for item in data:
        if not _is_json_object(item):
            sys.exit(
                f"Invalid trade data in {file_path}: expected a JSON list of objects"
            )
        rows.append(_json_object(item))
    return rows


def _is_json_array(value: object) -> TypeGuard[list[object]]:
    """Whether a parsed JSON value is an array (json gives ``list`` for those)."""
    return isinstance(value, list)


def _is_json_object(value: object) -> TypeGuard[dict[object, object]]:
    """Whether a parsed JSON value is an object (json gives ``dict`` for those)."""
    return isinstance(value, dict)


def _json_object(value: dict[object, object]) -> dict[str, object]:
    """A parsed JSON object with its (always string) keys typed as such."""
    return {str(key): item for key, item in value.items()}


def load_profile(file_path: str | None) -> dict[str, object]:
    """Load personal details from a JSON profile file, or {} when none is given."""
    if not file_path:
        return {}
    try:
        with Path(file_path).open(encoding="utf-8") as f:
            profile: object = json.load(f)
    except Exception as e:
        sys.exit(f"Error loading profile from {file_path}: {e}")
    if not _is_json_object(profile):
        sys.exit(f"Profile {file_path} must be a JSON object")
    return _json_object(profile)


def resolve_personal_details(
    args: argparse.Namespace, fields: list[str], parser: argparse.ArgumentParser
) -> dict[str, str]:
    """Option, then environment variable, then profile file; error if none has it."""
    profile = load_profile(args.profile)
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for field in fields:
        option, env_var = PERSONAL_FIELDS[field]
        value = (
            getattr(args, field, None) or os.environ.get(env_var) or profile.get(field)
        )
        if value in (None, ""):
            missing.append(f"{option} (or {env_var}, or '{field}' in --profile)")
        else:
            resolved[field] = str(value)
    if missing:
        parser.error("missing " + "; ".join(missing))
    return resolved


def validate_personal_details(details: dict[str, str]) -> dict[str, str]:
    """Validate just the fields given, with the library's own validators."""
    validators = PersonalInfoValidator().validators
    validated: dict[str, str] = {}
    try:
        for field, value in details.items():
            cleaned = validators[field].validate(value)
            if cleaned is None:  # every personal field is required
                sys.exit(f"Invalid personal details: {field} is required")
            validated[field] = cleaned
    except SRUGeneratorError as e:
        sys.exit(f"Invalid personal details: {e}")
    return validated


def add_personal_options(parser: argparse.ArgumentParser, fields: list[str]) -> None:
    help_texts = {
        "personal_number": "Personnummer, 12 digits (YYYYMMDDNNNN). Prefer "
        "SRU_PERSONAL_NUMBER or --profile: command-line arguments end up in "
        "shell history",
        "full_name": "Full name (or SRU_FULL_NAME)",
        "postal_code": "Postal code, 5 digits (or SRU_POSTAL_CODE)",
        "city_name": "City (or SRU_CITY_NAME)",
    }
    for field in fields:
        parser.add_argument(
            PERSONAL_FIELDS[field][0], dest=field, help=help_texts[field]
        )
    parser.add_argument(
        "--profile",
        help="JSON file with any of: " + ", ".join(fields),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sru-generator",
        description=(
            "Generate Swedish SRU files (INFO.SRU, BLANKETTER.SRU) for bilaga K4"
        ),
        epilog=f"Not tax advice. See {DISCLAIMER_URL}",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show informational log messages"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    info_parser = subparsers.add_parser("info", help="Generate the INFO.SRU file")
    add_personal_options(info_parser, list(PERSONAL_FIELDS))
    info_parser.add_argument("--output", default="INFO.SRU", help="Output file path")

    trade_parser = subparsers.add_parser(
        "trades", help="Generate the BLANKETTER.SRU file"
    )
    trade_parser.add_argument("--data", required=True, help="JSON file with trade data")
    add_personal_options(trade_parser, ["personal_number", "full_name"])
    trade_parser.add_argument(
        "--year",
        type=int,
        # Local date: the income year being declared is last year where the user is.
        default=datetime.now().astimezone().year - 1,
        help="Income year being declared (default: last year)",
    )
    trade_parser.add_argument(
        "--output", default="BLANKETTER.SRU", help="Output file path"
    )
    trade_parser.add_argument("--crypto-file", help="Optional crypto SRU file to merge")
    trade_parser.add_argument(
        "--character-conversion",
        choices=sorted(CONVERTER_NAMES),
        default="none",
        help="Character conversion to apply to stock names",
    )
    return parser


def _character_converter(name: str) -> Callable[[str], str]:
    """The converter for --character-conversion, with a note if it is the bundled one.

    The library warns with DeprecationWarning, which Python hides from CLI users, so
    the CLI says it on stderr instead.
    """
    converter, from_bundled = resolve_character_converter(name)
    if from_bundled:
        print(
            f"Note: using sru-generator's bundled '{name}' converter, which will be "
            f"removed in 2.0. Install text-converters: {TEXT_CONVERTERS_INSTALL}",
            file=sys.stderr,
        )
    return converter


def main() -> None:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "info":
        details = validate_personal_details(
            resolve_personal_details(args, list(PERSONAL_FIELDS), parser)
        )
        content = generate_sru_info_content(**details)
        if not write_sru_file(args.output, content):
            sys.exit(f"Failed to write info file: {args.output} (see the log above)")
        print(f"Info file generated: {args.output}")

    elif args.command == "trades":
        details = validate_personal_details(
            resolve_personal_details(args, ["personal_number", "full_name"], parser)
        )
        raw_trades = load_trade_data(args.data)
        try:
            trade_data = validate_trade_data(raw_trades)
        except SRUGeneratorError as e:
            sys.exit(f"Invalid trade data in {args.data}: {e}")
        try:
            character_converter = _character_converter(args.character_conversion)
            trade_content = generate_sru_trade_content(
                trade_data=trade_data,
                full_name=details["full_name"],
                personal_number=details["personal_number"],
                year=args.year,
                character_converter=character_converter,
            )

            crypto_groups = []
            if args.crypto_file and Path(args.crypto_file).exists():
                crypto_groups = read_crypto_sru_content(args.crypto_file)
            # Always merge, even with no crypto groups: this is what closes the file
            # with #FIL_SLUT, exactly as build_blanketter_sru does.
            final_content = merge_sru_groups(
                stock_content=trade_content,
                crypto_groups=crypto_groups,
                full_name=details["full_name"],
                personal_number=details["personal_number"],
                year=args.year,
            )

        except SRUGeneratorError as e:
            sys.exit(f"Cannot build {args.output}: {e}")

        if not write_sru_file(args.output, final_content):
            sys.exit(f"Failed to write trade file: {args.output} (see the log above)")
        print(f"Trade file generated: {args.output}")
        print(
            "Not tax advice: check every row and total in Skatteverket's e-service "
            f"before you sign. See {DISCLAIMER_URL}"
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
