#!/usr/bin/env python3
"""
Install the SRU Generator package in development mode.
Run this script to install the package locally for development.
"""

import subprocess
import sys
from pathlib import Path

def install_package():
    """Install the package in development mode."""
    package_dir = Path(__file__).parent
    
    try:
        print("Installing SRU Generator package in development mode...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-e", str(package_dir)
        ])
        print("✓ Package installed successfully!")
        print("\nYou can now import the package:")
        print("  from sru_generator import generate_sru_info_content")
        print("\nOr use the CLI:")
        print("  sru-generator --help")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_package()
