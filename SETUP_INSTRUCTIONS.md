# Brawlhalla Mod Loader - Universal Setup Instructions

## Quick Setup (Recommended)

1. **Run the setup script:**
   ```bash
   python setup_universal.py
   ```

2. **Start the mod loader:**
   ```bash
   python main.py
   ```

## Manual Setup

If the automatic setup doesn't work, follow these steps:

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r core/requirements.txt
   ```

2. **Verify installation:**
   ```bash
   python -c "import py7zr; print('py7zr installed successfully')"
   ```

3. **Run the mod loader:**
   ```bash
   python main.py
   ```

## Troubleshooting

### "ModuleNotFoundError: No module named 'py7zr'"
- Run: `pip install py7zr`
- Or run the setup script: `python setup_universal.py`

### "ModuleNotFoundError: No module named 'core'"
- Make sure you're in the correct directory (the one containing `main.py`)
- The `core` folder should be in the same directory as `main.py`

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Try running the setup script: `python setup_universal.py`

## File Structure

```
BrawlhallaModLoader/
├── main.py                 # Main entry point
├── run.py                  # Multiprocessing handler
├── setup_universal.py     # Universal setup script
├── requirements.txt       # Root dependencies
├── core/                  # Core library
│   ├── __init__.py
│   ├── requirements.txt   # Core dependencies
│   └── core/             # Inner core module
│       ├── __init__.py
│       ├── controller/
│       └── worker/
└── ui/                    # User interface
```

The mod loader uses relative paths and should work on any machine when dependencies are properly installed.

