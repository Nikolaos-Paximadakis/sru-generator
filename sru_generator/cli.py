"""
Command-line interface for SRU Generator.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

from .sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    write_sru_file,
    read_crypto_sru_content,
    merge_sru_groups,
)
from .character_converters import get_character_converter


def load_trade_data(file_path: str) -> List[Dict[str, Any]]:
    """Load trade data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading trade data from {file_path}: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Swedish SRU files for tax reporting"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info file command
    info_parser = subparsers.add_parser('info', help='Generate SRU info file')
    info_parser.add_argument('--personal-number', required=True, help='Personal number')
    info_parser.add_argument('--full-name', required=True, help='Full name')
    info_parser.add_argument('--postal-code', required=True, help='Postal code')
    info_parser.add_argument('--city-name', required=True, help='City name')
    info_parser.add_argument('--output', default='info.sru', help='Output file path')
    
    # Trade file command
    trade_parser = subparsers.add_parser('trades', help='Generate SRU trade file')
    trade_parser.add_argument('--data', required=True, help='JSON file with trade data')
    trade_parser.add_argument('--personal-number', required=True, help='Personal number')
    trade_parser.add_argument('--full-name', required=True, help='Full name')
    trade_parser.add_argument('--year', type=int, default=2024, help='Tax year')
    trade_parser.add_argument('--output', default='blanketter.sru', help='Output file path')
    trade_parser.add_argument('--crypto-file', help='Optional crypto SRU file to merge')
    trade_parser.add_argument('--character-conversion', 
                             choices=['greek', 'swedish', 'german', 'french', 'spanish', 'none'],
                             default='none',
                             help='Character conversion to apply to stock names')
    
    args = parser.parse_args()
    
    if args.command == 'info':
        content = generate_sru_info_content(
            personal_number=args.personal_number,
            full_name=args.full_name,
            postal_code=args.postal_code,
            city_name=args.city_name
        )
        write_sru_file(args.output, content)
        print(f"Info file generated: {args.output}")
        
    elif args.command == 'trades':
        trade_data = load_trade_data(args.data)
        character_converter = get_character_converter(args.character_conversion)
        trade_content = generate_sru_trade_content(
            trade_data=trade_data,
            full_name=args.full_name,
            personal_number=args.personal_number,
            year=args.year,
            character_converter=character_converter
        )
        
        if args.crypto_file and Path(args.crypto_file).exists():
            crypto_groups = read_crypto_sru_content(args.crypto_file)
            final_content = merge_sru_groups(
                stock_content=trade_content,
                crypto_groups=crypto_groups,
                full_name=args.full_name,
                personal_number=args.personal_number,
                year=args.year
            )
        else:
            final_content = trade_content
            
        write_sru_file(args.output, final_content)
        print(f"Trade file generated: {args.output}")
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
