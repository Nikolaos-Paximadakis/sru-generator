#!/usr/bin/env python3
"""
Example demonstrating flexible character conversion in SRU Generator.
"""

from sru_generator import (
    generate_sru_trade_content,
    write_sru_file,
    convert_greek_characters_to_english,
    convert_swedish_characters_to_english,
    convert_german_characters_to_english,
    get_character_converter,
    no_conversion
)

def main():
    # Example trade data with different character sets
    trade_data = [
        {
            "quantity": 100,
            "stock": "Αθήνα",  # Greek characters
            "net value": 15000.00,
            "total net value of purchase": 14000.00,
            "profit/loss": 1000.00
        },
        {
            "quantity": 50,
            "stock": "Göteborg",  # Swedish characters
            "net value": 12000.00,
            "total net value of purchase": 13000.00,
            "profit/loss": -1000.00
        },
        {
            "quantity": 200,
            "stock": "München",  # German characters
            "net value": 25000.00,
            "total net value of purchase": 20000.00,
            "profit/loss": 5000.00
        }
    ]
    
    print("=== SRU Generator - Flexible Character Conversion Demo ===\n")
    
    # Example 1: No character conversion
    print("1. No character conversion:")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=no_conversion
    )
    write_sru_file("no_conversion.sru", trade_content)
    print("✓ Generated: no_conversion.sru")
    
    # Example 2: Greek character conversion
    print("\n2. Greek character conversion:")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=convert_greek_characters_to_english
    )
    write_sru_file("greek_conversion.sru", trade_content)
    print("✓ Generated: greek_conversion.sru")
    
    # Example 3: Swedish character conversion
    print("\n3. Swedish character conversion:")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=convert_swedish_characters_to_english
    )
    write_sru_file("swedish_conversion.sru", trade_content)
    print("✓ Generated: swedish_conversion.sru")
    
    # Example 4: German character conversion
    print("\n4. German character conversion:")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=convert_german_characters_to_english
    )
    write_sru_file("german_conversion.sru", trade_content)
    print("✓ Generated: german_conversion.sru")
    
    # Example 5: Using the convenience function
    print("\n5. Using convenience function:")
    character_converter = get_character_converter("greek")
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=character_converter
    )
    write_sru_file("convenience_function.sru", trade_content)
    print("✓ Generated: convenience_function.sru")
    
    # Example 6: Custom character converter
    print("\n6. Custom character converter:")
    def custom_converter(text: str) -> str:
        """Custom converter that removes all special characters."""
        return ''.join(c for c in text if c.isalnum() or c.isspace())
    
    trade_content = generate_sru_trade_content(
        trade_data=trade_data,
        full_name="John Doe",
        personal_number="1234567890",
        year=2024,
        character_converter=custom_converter
    )
    write_sru_file("custom_converter.sru", trade_content)
    print("✓ Generated: custom_converter.sru")
    
    print("\n=== Demo completed! ===")
    print("Check the generated .sru files to see the different character conversions.")

if __name__ == "__main__":
    main()
