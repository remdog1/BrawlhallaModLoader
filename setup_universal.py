#!/usr/bin/env python3
"""
Universal setup script for Brawlhalla Mod Loader
Installs all required dependencies from requirements.txt files
"""

import os
import sys
import subprocess

def run_pip_install(requirements_file):
    """Install packages from a requirements file"""
    if not os.path.exists(requirements_file):
        print(f"⚠️  Warning: {requirements_file} not found, skipping...")
        return False
    
    print(f"\n📦 Installing dependencies from {requirements_file}...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Successfully installed dependencies from {requirements_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies from {requirements_file}:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("🚀 Brawlhalla Mod Loader - Universal Setup")
    print("=" * 60)
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Install root requirements
    root_requirements = os.path.join(script_dir, "requirements.txt")
    root_success = run_pip_install(root_requirements)
    
    # Install core requirements
    core_requirements = os.path.join(script_dir, "core", "requirements.txt")
    core_success = run_pip_install(core_requirements)
    
    # Summary
    print("\n" + "=" * 60)
    if root_success and core_success:
        print("✅ Setup completed successfully!")
        print("\nYou can now run the mod loader with:")
        print("  python main.py")
    else:
        print("⚠️  Setup completed with some errors.")
        print("Please review the errors above and try installing manually:")
        print("  pip install -r requirements.txt")
        print("  pip install -r core/requirements.txt")
    print("=" * 60)
    
    return 0 if (root_success and core_success) else 1

if __name__ == "__main__":
    sys.exit(main())

