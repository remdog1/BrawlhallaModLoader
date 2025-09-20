#!/usr/bin/env python3
"""
Setup script for Brawlhalla Mod Loader
This script initializes the core submodule and installs dependencies
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    print("🚀 Setting up Brawlhalla Mod Loader...")
    
    # Check if we're in the right directory
    if not os.path.exists('.gitmodules'):
        print("❌ Error: .gitmodules not found. Please run this script from the root of the repository.")
        return False
    
    # Initialize and update submodules
    if not run_command("git submodule update --init --recursive", "Initializing core submodule"):
        print("❌ Failed to initialize submodule. Make sure you have git installed.")
        return False
    
    # Install Python dependencies
    if os.path.exists('requirements.txt'):
        if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing main dependencies"):
            print("⚠️  Warning: Failed to install main dependencies")
    
    # Install core dependencies
    if os.path.exists('core/requirements.txt'):
        if not run_command(f"{sys.executable} -m pip install -r core/requirements.txt", "Installing core dependencies"):
            print("⚠️  Warning: Failed to install core dependencies")
    
    print("\n🎉 Setup completed! You can now run the mod loader.")
    print("📝 Note: If you encounter any issues, make sure you have:")
    print("   - Git installed")
    print("   - Python 3.7+ installed")
    print("   - Internet connection for downloading dependencies")
    
    return True

if __name__ == "__main__":
    main()
