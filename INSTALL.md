# 🚨 INSTALLATION REQUIRED - READ THIS FIRST! 🚨

## If you get this error:
```
ModuleNotFoundError: No module named 'py7zr'
```

**You MUST run the setup script first!**

## Quick Installation

### Option 1: Automatic Setup (Recommended)
```bash
python setup_universal.py
```

### Option 2: Windows Users
Double-click `setup.bat`

### Option 3: Manual Installation
```bash
pip install -r requirements.txt
pip install -r core/requirements.txt
```

## After Installation
```bash
python main.py
```

## Why This Is Needed
The Brawlhalla Mod Loader requires several Python packages that are not included with Python by default. The setup script automatically installs all required dependencies.

## Troubleshooting
- **"python is not recognized"**: Install Python from python.org
- **Permission errors**: Run as administrator or use `pip install --user`
- **Still getting errors**: Try `python -m pip install -r requirements.txt`

---
**Remember: Always run the setup script before trying to run the mod loader!**
