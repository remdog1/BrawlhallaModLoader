# Brawlhalla ModLoader ![Python 3.6](https://img.shields.io/badge/python-3.8-blue.svg)

**ModLoader** - tool for installing mods in Brawlhalla  
**[ModCreator](https://github.com/Farbigoz/BhModCreator)** - tool for creating mods for Brawlhalla

![window](https://github.com/Farbigoz/BhModloader/blob/main/wiki/readme/window.png)

## Quick Setup (Universal)

**For any machine to work with the mod loader:**

1. **Run the setup script:**
   ```bash
   python setup_universal.py
   ```
   Or on Windows: Double-click `setup.bat`

2. **Start the mod loader:**
   ```bash
   python main.py
   ```

This ensures all dependencies are installed and the mod loader works universally on any machine.

## Download application
For downloading the app, see [**latest release**](https://github.com/Farbigoz/BhModloader/releases/latest). 
Older versions and pre-releases builds are available on [**releases section**](https://github.com/Farbigoz/BhModloader/releases)

## Project

### Required libraries
    $ pip install JPype1
    $ pip install PySide6
    $ pip install psutil
    $ pip install pywin32   #If your system - Windows
    $ pip install rarfile
    $ pip install py7zr
    
### Build
    $ pip install pyinstaller  
    $ pyinstaller main.spec

## Licenses

Brawlhalla ModLoader is licensed with GNU GPL v3, see the [license.txt](license.txt).
It uses modified code of these libraries:

* [FFDec Library](https://github.com/jindrapetrik/jpexs-decompiler) - LGPLv3