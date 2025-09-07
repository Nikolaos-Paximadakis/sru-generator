#!/usr/bin/env python3
"""
Advanced usage example for SRU Generator with crypto support.
"""

import json
from sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
    read_crypto_sru_content,
    write_sru_file
)

def load_trade_data(filename: str):
    """Load trade data from JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # Load trade data from file
    print("Loading trade data...")
    trade_data = load_trade_data("sample_trades.json")
    print(f"✓ Loaded {len(trade_data)} trade records")
    
    # Generate info file
    print("Generating SRU info file...")
    info_content = generate_sru_info_content(
        personal_number="1234567890",
        full_name="John Doe",
        postal_code="12345",
        city_name="Stockholm"
    )
    write_sru_file("info.sru", info_content)
    print("✓ Info file created: info.sru")
    
    # Generate stock trade content
    print("Generating stock trade content...")
    stock_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024
    )
    print("✓ Stock trade content generated")
    
    # Check for crypto file and merge if available
    crypto_file = "crypto_data.sru"
    try:
        print(f"Looking for crypto file: {crypto_file}")
        crypto_groups = read_crypto_sru_content(crypto_file)
        
        if crypto_groups:
            print(f"✓ Found {len(crypto_groups)} crypto groups")
            print("Merging stock and crypto data...")
            final_content = merge_sru_groups(
                stock_content=stock_content,
                crypto_groups=crypto_groups,
                full_name="John Doe",
                personal_number="1234567890",
                year=2024
            )
            print("✓ Data merged successfully")
        else:
            print("No crypto data found, using stock data only")
            final_content = stock_content
            
    except FileNotFoundError:
        print(f"No crypto file found at {crypto_file}, using stock data only")
        final_content = stock_content
    
    # Write final SRU file
    print("Writing final SRU file...")
    write_sru_file("blanketter.sru", final_content)
    print("✓ Final SRU file created: blanketter.sru")
    
    print("\nSRU generation completed successfully!")

if __name__ == "__main__":
    main()
