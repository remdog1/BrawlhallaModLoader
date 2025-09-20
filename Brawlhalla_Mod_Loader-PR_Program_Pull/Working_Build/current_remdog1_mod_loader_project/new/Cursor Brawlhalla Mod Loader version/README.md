# Brawlhalla ModLoader ![Python 3.6](https://img.shields.io/badge/python-3.8-blue.svg)

**ModLoader** - tool for installing mods in Brawlhalla  
**[ModCreator](https://github.com/Farbigoz/BhModCreator)** - tool for creating mods for Brawlhalla

![window](https://github.com/Farbigoz/BhModloader/blob/main/wiki/readme/window.png)

## Quick Start

### For Users (Download and Run)
For downloading the app, see [**latest release**](https://github.com/Farbigoz/BhModloader/releases/latest). 
Older versions and pre-releases builds are available on [**releases section**](https://github.com/Farbigoz/BhModloader/releases)

### For Developers (Source Code)

#### Prerequisites
- **Git** installed ([Download Git](https://git-scm.com/download/win))
- **Python 3.7+** installed
- Internet connection

#### Setup Instructions

**Option 1: Automatic Setup (Recommended)**
```bash
# Clone the repository
git clone https://github.com/remdog1/BrawlhallaModLoader.git
cd BrawlhallaModLoader

# Run the setup script
python setup.py
```

**Option 2: Manual Setup**
```bash
# Clone the repository with submodules
git clone --recursive https://github.com/remdog1/BrawlhallaModLoader.git
cd BrawlhallaModLoader

# Install dependencies
pip install -r requirements.txt
pip install -r core/requirements.txt
```

**Option 3: Windows Batch Setup**
```cmd
# Clone the repository
git clone https://github.com/remdog1/BrawlhallaModLoader.git
cd BrawlhallaModLoader

# Run the batch setup
setup.bat
```

#### Troubleshooting

**If you get "ModuleNotFoundError: No module named 'py7zr'" or similar errors:**
1. Make sure you ran the setup script first
2. If the core folder appears empty, run: `git submodule update --init --recursive`
3. Install dependencies: `pip install -r requirements.txt` and `pip install -r core/requirements.txt`

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