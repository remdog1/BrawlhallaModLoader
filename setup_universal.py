#!/usr/bin/env python3
"""
Universal Setup Script for Brawlhalla Mod Loader
This script ensures the mod loader works on any machine by:
1. Installing required dependencies
2. Verifying the setup works
"""

import os
import sys
import subprocess
import importlib

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies from requirements.txt"""
    print("📦 Installing dependencies...")
    
    requirements_files = ['requirements.txt', 'core/requirements.txt']
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            print(f"Installing from {req_file}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file])
                print(f"✅ Successfully installed dependencies from {req_file}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies from {req_file}: {e}")
                return False
        else:
            print(f"⚠️  {req_file} not found, skipping...")
    
    return True

def verify_setup():
    """Verify that the setup works by testing imports"""
    print("🔍 Verifying setup...")
    
    # Add core to path
    core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'core'))
    if core_path not in sys.path:
        sys.path.insert(0, core_path)
    
    # Test critical imports
    try:
        import py7zr
        print("✅ py7zr imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import py7zr: {e}")
        return False
    
    try:
        from core.core import Controller
        print("✅ Core Controller imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Controller: {e}")
        return False
    
    try:
        import PySide6
        print("✅ PySide6 imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import PySide6: {e}")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Brawlhalla Mod Loader - Universal Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Verify setup
    if not verify_setup():
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("The Brawlhalla Mod Loader should now work on this machine.")
    print("\nTo run the mod loader, execute: python main.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)




