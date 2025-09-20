# Brawlhalla ModLoader ![Python 3.6](https://img.shields.io/badge/python-3.8-blue.svg)

**ModLoader** - tool for installing mods in Brawlhalla  
**[ModCreator](https://github.com/Farbigoz/BhModCreator)** - tool for creating mods for Brawlhalla

![window](https://github.com/Farbigoz/BhModloader/blob/main/wiki/readme/window.png)

## 🚀 Universal Compatibility

**The mod loader now works on any machine without setup!**

### Just Run It!

```bash
python main.py
```

**That's it!** The mod loader will start and work with:
- ✅ ZIP files (always supported)
- ✅ RAR files (always supported) 
- ⚠️ 7z files (optional - install `py7zr` for full support)

### Optional: Full 7z Support

For complete 7z file support, install py7zr:
```bash
pip install py7zr
```

### Manual Setup (If needed)

If you want to install all dependencies at once:
```bash
python setup_universal.py
```

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