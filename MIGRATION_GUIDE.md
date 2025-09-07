# Migration Guide: From Internal Module to Standalone Package

This guide explains how to migrate from using the internal `sru_generator` module to the standalone `sru-generator` package.

## Installation

### Option 1: Install from local directory (for development)
```bash
cd sru_generator_package
python install_local.py
```

### Option 2: Install in development mode
```bash
cd sru_generator_package
pip install -e .
```

### Option 3: Install from PyPI (when published)
```bash
pip install sru-generator
```

## Code Changes

### Before (using internal module)
```python
from utilities.sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    write_sru_file,
    # ... other imports
)
```

### After (using standalone package)
```python
from sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    write_sru_file,
    # ... other imports
)
```

## Updated Import in Main Project

Update your `utilities/sru_file_operations.py`:

```python
# Change this:
from utilities.sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
    read_crypto_sru_content,
    write_sru_file,
    # ... constants
)

# To this:
from sru_generator import (
    generate_sru_info_content,
    generate_sru_trade_content,
    merge_sru_groups,
    read_crypto_sru_content,
    write_sru_file,
    # ... constants
)
```

## Benefits of Migration

1. **Standalone Package**: Can be published to PyPI and used by other projects
2. **Better Organization**: Clear separation of concerns
3. **Version Control**: Independent versioning and release cycle
4. **Documentation**: Comprehensive documentation and examples
5. **Testing**: Dedicated test suite
6. **CLI Support**: Command-line interface for easy usage

## Backward Compatibility

The API remains the same, so existing code should work without changes after updating the import statements.

## Development Workflow

1. Make changes to the standalone package
2. Test the changes
3. Update the main project to use the new version
4. Publish to PyPI when ready

## Publishing to GitHub

1. Create a new repository on GitHub
2. Push the `sru_generator_package` directory contents to the repository
3. Add proper repository description and topics
4. Create releases for version tags
