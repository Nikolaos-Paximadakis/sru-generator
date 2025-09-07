#!/usr/bin/env python3
"""
Basic usage example for SRU Generator.
"""

from sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    write_sru_file
)

def main():
    # Example trade data
    trade_data = [
        {
            "quantity": 100,
            "stock": "Apple Inc",
            "net value": 15000.00,
            "total net value of purchase": 14000.00,
            "profit/loss": 1000.00
        },
        {
            "quantity": 50,
            "stock": "Microsoft Corp",
            "net value": 12000.00,
            "total net value of purchase": 13000.00,
            "profit/loss": -1000.00
        }
    ]
    
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
    
    # Generate trade file
    print("Generating SRU trade file...")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024
    )
    write_sru_file("blanketter.sru", trade_content)
    print("✓ Trade file created: blanketter.sru")
    
    print("\nSRU files generated successfully!")

if __name__ == "__main__":
    main()
