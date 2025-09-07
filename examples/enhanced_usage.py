"""
Enhanced usage examples for SRU Generator with new features.

This example demonstrates the new high-priority enhancements:
- Configuration management
- Enhanced validation
- Multi-currency support
"""

from sru_generator import (
    SRUConfig, 
    create_config,
    validate_trade_data,
    validate_personal_info,
    convert_currency,
    convert_to_sek,
    set_exchange_rate,
    generate_sru_trade_content,
    write_sru_file,
    ValidationError,
    CurrencyError,
    ConfigurationError
)


def example_enhanced_configuration():
    """Demonstrate enhanced configuration management."""
    print("=== Enhanced Configuration Example ===")
    
    # Create a custom configuration
    config = create_config(
        character_converter="greek",
        validation_level="strict",
        strict_validation=True,
        rounding_mode="half_even",
        default_currency="SEK",
        auto_convert_currency=True,
        log_level="DEBUG"
    )
    
    print(f"Configuration: {config.to_dict()}")
    
    # Get character converter from config
    converter = config.get_character_converter()
    print(f"Character converter: {converter.__name__}")
    
    # Set exchange rates
    config.set_exchange_rate("USD", "SEK", 10.5)
    config.set_exchange_rate("EUR", "SEK", 11.2)
    
    print(f"USD to SEK rate: {config.get_exchange_rate('USD', 'SEK')}")
    print(f"EUR to SEK rate: {config.get_exchange_rate('EUR', 'SEK')}")
    
    return config


def example_enhanced_validation():
    """Demonstrate enhanced validation system."""
    print("\n=== Enhanced Validation Example ===")
    
    # Valid trade data
    valid_trade_data = [
        {
            "quantity": 100,
            "stock": "Apple Inc",
            "net value": 15000.00,
            "total net value of purchase": 14000.00,
            "profit/loss": 1000.00,
            "currency": "USD",
            "exchange_rate": 10.5
        },
        {
            "quantity": 50,
            "stock": "Microsoft Corp",
            "net value": 12000.00,
            "total net value of purchase": 13000.00,
            "profit/loss": -1000.00,
            "currency": "EUR",
            "exchange_rate": 11.2
        }
    ]
    
    try:
        # Validate trade data
        validated_data = validate_trade_data(valid_trade_data)
        print("✅ Trade data validation successful!")
        print(f"Validated {len(validated_data)} trade items")
        
        # Show validated data
        for i, item in enumerate(validated_data):
            print(f"  Item {i+1}: {item['stock']} - {item['quantity']} shares")
    
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
    
    # Invalid trade data example
    invalid_trade_data = [
        {
            "quantity": -10,  # Invalid: negative quantity
            "stock": "",      # Invalid: empty stock name
            "net value": "invalid",  # Invalid: not a number
        }
    ]
    
    try:
        validate_trade_data(invalid_trade_data)
    except ValidationError as e:
        print(f"❌ Expected validation error: {e}")
    
    # Personal info validation
    personal_info = {
        "personal_number": "1234567890",
        "full_name": "John Doe",
        "postal_code": "12345",
        "city_name": "Stockholm"
    }
    
    try:
        validated_personal = validate_personal_info(personal_info)
        print("✅ Personal info validation successful!")
        print(f"Validated personal info for: {validated_personal['full_name']}")
    except ValidationError as e:
        print(f"❌ Personal info validation failed: {e}")


def example_multi_currency_support():
    """Demonstrate multi-currency support."""
    print("\n=== Multi-Currency Support Example ===")
    
    # Set up exchange rates
    set_exchange_rate("USD", "SEK", 10.5)
    set_exchange_rate("EUR", "SEK", 11.2)
    set_exchange_rate("GBP", "SEK", 13.1)
    
    # Multi-currency trade data
    multi_currency_trades = [
        {
            "quantity": 100,
            "stock": "Apple Inc",
            "net value": 1500.00,  # USD
            "total net value of purchase": 1400.00,  # USD
            "currency": "USD"
        },
        {
            "quantity": 50,
            "stock": "SAP SE",
            "net value": 2000.00,  # EUR
            "total net value of purchase": 1900.00,  # EUR
            "currency": "EUR"
        },
        {
            "quantity": 25,
            "stock": "BP PLC",
            "net value": 500.00,  # GBP
            "total net value of purchase": 480.00,  # GBP
            "currency": "GBP"
        }
    ]
    
    print("Original multi-currency trades:")
    for trade in multi_currency_trades:
        print(f"  {trade['stock']}: {trade['net value']} {trade['currency']}")
    
    # Convert all to SEK
    print("\nConverted to SEK:")
    for trade in multi_currency_trades:
        amount_sek = convert_to_sek(trade['net value'], trade['currency'])
        cost_sek = convert_to_sek(trade['total net value of purchase'], trade['currency'])
        profit_sek = amount_sek - cost_sek
        
        print(f"  {trade['stock']}: {amount_sek} SEK (profit: {profit_sek} SEK)")
    
    # Direct currency conversion
    usd_amount = 1000.00
    eur_amount = convert_currency(usd_amount, "USD", "EUR")
    print(f"\nDirect conversion: {usd_amount} USD = {eur_amount} EUR")


def example_enhanced_sru_generation():
    """Demonstrate enhanced SRU generation with new features."""
    print("\n=== Enhanced SRU Generation Example ===")
    
    # Create configuration
    config = create_config(
        character_converter="greek",
        validation_level="strict",
        default_currency="SEK"
    )
    
    # Set exchange rates
    config.set_exchange_rate("USD", "SEK", 10.5)
    config.set_exchange_rate("EUR", "SEK", 11.2)
    
    # Multi-currency trade data
    trade_data = [
        {
            "quantity": 100,
            "stock": "Αθήνα",  # Greek characters
            "net value": 1500.00,
            "total net value of purchase": 1400.00,
            "currency": "USD"
        },
        {
            "quantity": 50,
            "stock": "Microsoft Corp",
            "net value": 2000.00,
            "total net value of purchase": 1900.00,
            "currency": "EUR"
        }
    ]
    
    try:
        # Validate data first
        validated_data = validate_trade_data(trade_data)
        print("✅ Data validation successful!")
        
        # Convert currencies to SEK
        for trade in validated_data:
            if trade.get('currency') and trade['currency'] != 'SEK':
                trade['net value'] = float(convert_to_sek(trade['net value'], trade['currency']))
                trade['total net value of purchase'] = float(convert_to_sek(trade['total net value of purchase'], trade['currency']))
                trade['profit/loss'] = trade['net value'] - trade['total net value of purchase']
                trade['currency'] = 'SEK'  # Mark as converted
        
        # Generate SRU content with character conversion
        character_converter = config.get_character_converter()
        sru_content = generate_sru_trade_content(
            trade_data=validated_data,
            full_name="John Doe",
            personal_number="1234567890",
            year=2024,
            character_converter=character_converter
        )
        
        # Write to file
        output_file = "enhanced_example.sru"
        write_sru_file(output_file, sru_content)
        print(f"✅ SRU file generated: {output_file}")
        
        # Show sample content
        print("\nSample SRU content:")
        lines = sru_content.split('\n')[:10]  # First 10 lines
        for line in lines:
            if line.strip():
                print(f"  {line}")
    
    except (ValidationError, CurrencyError, ConfigurationError) as e:
        print(f"❌ Error: {e}")


def main():
    """Run all enhanced examples."""
    print("SRU Generator Enhanced Features Demo")
    print("=" * 50)
    
    try:
        # Run examples
        config = example_enhanced_configuration()
        example_enhanced_validation()
        example_multi_currency_support()
        example_enhanced_sru_generation()
        
        print("\n" + "=" * 50)
        print("✅ All enhanced features working correctly!")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
