# SRU Generator - Setup Guide

## Project Structure
This is now a **separate, independent project** with its own source control.

**Location**: `E:\Python\sru-generator\`

## Quick Start

### 1. Install the Package
```bash
cd E:\Python\sru-generator
pip install -e .
```

### 2. Test Installation
```bash
python -c "from sru_generator import generate_sru_info_content; print('Package installed successfully!')"
```

### 3. Run Tests
```bash
python -m pytest tests/ -v
```

### 4. Try CLI
```bash
python -m sru_generator.cli --help
```

## Development Setup

### 1. Initialize Git (if not already done)
```bash
git init
git add .
git commit -m "Initial commit: SRU Generator package"
```

### 2. Create GitHub Repository
1. Create new repository on GitHub
2. Add remote origin:
   ```bash
   git remote add origin https://github.com/yourusername/sru-generator.git
   git branch -M main
   git push -u origin main
   ```

### 3. Development Workflow
```bash
# Make changes
# Test changes
python -m pytest tests/ -v

# Commit changes
git add .
git commit -m "Description of changes"

# Push to GitHub
git push origin main
```

## Publishing to PyPI

### 1. Install Build Tools
```bash
pip install build twine
```

### 2. Build Package
```bash
python -m build
```

### 3. Upload to PyPI
```bash
twine upload dist/*
```

## Usage in Other Projects

Once published to PyPI, other projects can install it with:
```bash
pip install sru-generator
```

Or for development:
```bash
pip install -e E:\Python\sru-generator
```

## Project Benefits

- ✅ **Independent Version Control** - Separate Git repository
- ✅ **Clean Separation** - No confusion with Mihalis project
- ✅ **Independent Publishing** - Can be published separately
- ✅ **Better Organization** - Each project has its own space
- ✅ **Easier Maintenance** - Changes don't affect other projects
