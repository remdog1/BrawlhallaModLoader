# Brawlhalla Mod Loader - File Association Setup

This document explains how to set up proper file associations for `.bmod` files with the Brawlhalla Mod Loader.

## Overview

The file association system allows users to:
- Double-click `.bmod` files to automatically install them
- See the Brawlhalla Mod Loader icon on `.bmod` files
- Use "Open with" context menu to choose Brawlhalla Mod Loader
- Have the system automatically detect the latest installation

## Files Included

### Core Files
- `setup_file_association.py` - Main file association setup script
- `registry_manager.py` - Registry management utilities
- `core/windows.py` - Windows-specific association logic

### Installer Files
- `install_file_associations.py` - Automatic installer with admin elevation
- `install_associations.bat` - Batch file for easy installation
- `setup_association.bat` - Original batch file (updated)

## How to Use

### Method 1: Automatic Installation (Recommended)
1. Run `install_associations.bat` as Administrator
2. The script will automatically detect the latest Brawlhalla Mod Loader installation
3. Set up all necessary file associations

### Method 2: Manual Installation
1. Run `setup_file_association.py` as Administrator
2. The script will:
   - Find the latest installation automatically
   - Set up `.bmod` file association
   - Add "Open with" context menu
   - Configure proper icons

### Method 3: Programmatic Installation
```python
from registry_manager import register
register()
```

## Features

### Latest Installation Detection
The system automatically finds the most recently modified Brawlhalla Mod Loader installation by checking:
- Current development directory (`dist/` folder)
- `Program Files/Brawlhalla Mod Loader/`
- `Program Files (x86)/Brawlhalla Mod Loader/`
- `%LOCALAPPDATA%/Programs/Brawlhalla Mod Loader/`
- `%APPDATA%/Brawlhalla Mod Loader/`

### Icon Support
- Uses the Brawlhalla Mod Loader program icon for all `.bmod` files
- Icon appears in file explorer, context menus, and "Open with" dialogs
- Automatically copies icon to AppData for system-wide access

### Context Menu Support
- Right-click on `.bmod` files shows "Open with Brawlhalla Mod Loader" option
- Appears in Windows "Open with" dialog
- Properly configured with program icon

### Registry Entries Created
- `HKEY_CLASSES_ROOT\.bmod` - File extension association
- `HKEY_CLASSES_ROOT\BrawlhallaModLoader.bmod` - File type definition
- `HKEY_CLASSES_ROOT\Applications\Brawlhalla Mod Loader 2025 Beta.exe` - Open with list
- `HKEY_CLASSES_ROOT\bmod` - URL protocol for `bmod://` links

## Troubleshooting

### Common Issues

1. **"Permission denied" error**
   - Solution: Run as Administrator

2. **Icon not showing**
   - Solution: Restart Windows Explorer or reboot
   - Check that `file_icon.ico` exists in the executable directory

3. **Association not working**
   - Solution: Check that the executable path is correct
   - Verify registry entries were created successfully

4. **Multiple installations detected**
   - The system automatically uses the most recently modified installation
   - To use a specific installation, modify the `find_latest_installation()` function

### Manual Registry Cleanup
If you need to remove associations manually:
```python
from registry_manager import unregister
unregister()
```

Or run:
```bash
python setup_file_association.py remove
```

## Technical Details

### Registry Structure
```
HKEY_CLASSES_ROOT\
├── .bmod
│   └── (Default) = "BrawlhallaModLoader.bmod"
├── BrawlhallaModLoader.bmod
│   ├── (Default) = "Brawlhalla Mod File"
│   ├── DefaultIcon
│   │   └── (Default) = "C:\Path\To\file_icon.ico,0"
│   ├── shell
│   │   ├── open
│   │   │   └── command
│   │   │       └── (Default) = "C:\Path\To\Brawlhalla Mod Loader 2025 Beta.exe" "%1"
│   │   └── openwith
│   │       ├── (Default) = "Open with Brawlhalla Mod Loader"
│   │       ├── DefaultIcon
│   │       │   └── (Default) = "C:\Path\To\file_icon.ico,0"
│   │       └── command
│   │           └── (Default) = "C:\Path\To\Brawlhalla Mod Loader 2025 Beta.exe" "%1"
└── Applications
    └── Brawlhalla Mod Loader 2025 Beta.exe
        ├── (Default) = "Brawlhalla Mod Loader 2025 Beta"
        ├── DefaultIcon
        │   └── (Default) = "C:\Path\To\file_icon.ico,0"
        └── shell
            └── open
                └── command
                    └── (Default) = "C:\Path\To\Brawlhalla Mod Loader 2025 Beta.exe" "%1"
```

### Command Line Arguments
The Mod Loader accepts file paths as command line arguments:
- `"Brawlhalla Mod Loader 2025 Beta.exe" "C:\Path\To\Mod.bmod"`
- Files are automatically copied to the Mods folder and installed

## Integration with Main Application

The file association system is integrated into the main application:
- `main.py` checks for associations on startup
- `core/windows.py` handles Windows-specific association logic
- Single-instance application ensures only one Mod Loader runs at a time
- New instances pass file paths to the running instance via IPC

## Security Considerations

- All scripts require Administrator privileges to modify the registry
- File paths are properly quoted to prevent command injection
- Icon files are copied to AppData for system-wide access
- Registry entries are cleaned up during uninstallation

## Future Enhancements

- Support for additional file types (`.zip`, `.7z`, etc.)
- Automatic association updates when Mod Loader is updated
- Support for custom installation directories
- Integration with Windows installer packages
