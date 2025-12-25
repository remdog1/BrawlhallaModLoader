# New Asset Creation Feature

## Overview

This feature allows the Brawlhalla Mod Loader to create **new assets** (sprites and ActionScript classes) that don't already exist in the game's SWF files. This is a groundbreaking upgrade that enables modders to add completely new visual elements and functionality to the game.

## What Was Added

### 1. New Sprite Creation (`importSprite` enhancement)

The `GameSwf.importSprite()` method now supports creating new sprites that don't exist in the game SWF:

- **New Parameter**: `createIfNotExists=False` - When set to `True`, creates a new sprite if it doesn't exist
- **Automatic Detection**: The system automatically detects when a sprite doesn't exist in the target SWF
- **Symbol Class Integration**: New sprites are automatically added to the SymbolClass with proper ID mapping
- **Dependency Handling**: All dependent elements (shapes, bitmaps, fonts, etc.) are properly cloned and mapped

### 2. New ActionScript Class Creation (`importScript` enhancement)

The `GameSwf.importScript()` method now supports creating new ActionScript classes:

- **New Parameter**: `createIfNotExists=False` - When set to `True`, attempts to create a new ActionScript class
- **ABC Compilation**: Attempts to compile ActionScript source to ABC bytecode (may have limitations)
- **Automatic Detection**: Detects when a script doesn't exist in the target SWF

### 3. Enhanced Installation Logic

The `ModClass.install()` method now:

- Automatically detects when assets are new vs existing
- Attempts to create new assets when they don't exist
- Provides detailed debug logging for troubleshooting
- Handles both new and existing assets seamlessly

## How It Works

### For Sprites

1. **Detection**: When installing a mod, the system checks if the sprite exists in the game SWF's SymbolClass
2. **Creation**: If the sprite doesn't exist and `createIfNotExists=True`:
   - Assigns a new character ID
   - Adds the sprite element to the SWF
   - Adds the sprite to the SymbolClass with the proper name mapping
   - Clones and maps all dependent elements (shapes, bitmaps, etc.)

### For ActionScript Classes

1. **Detection**: Checks if the ActionScript class exists in the SWF's AS3 packs
2. **Creation**: If the class doesn't exist and `createIfNotExists=True`:
   - Attempts to compile the ActionScript source to ABC bytecode
   - Creates a new DoABC tag or adds to existing ABC
   - Associates the class with the SWF

**Note**: ActionScript creation is more complex and may have limitations. The FFDec library needs to compile AS3 source to ABC bytecode, which may not always work perfectly.

## Usage

### In Mod Source Structure

The mod source structure remains the same. Simply place your sprites and scripts in the appropriate folders:

```
ModName/
├── game.swf/
│   ├── sprites/
│   │   └── DefineSprite_123_NewSpriteName/
│   │       └── frames.swf
│   └── scripts/
│       └── com.example.NewClass.as
```

### Automatic Behavior

The system **automatically** attempts to create new assets when:
- A sprite is not found in the game SWF's SymbolClass
- An ActionScript class is not found in the game SWF's AS3 packs

You don't need to do anything special - just include the assets in your mod as usual!

### Manual Control (Advanced)

If you need more control, you can check the debug logs to see:
- `✨ NEW SPRITE DETECTED: 'SpriteName' does not exist in game SWF`
- `✨ NEW SCRIPT DETECTED: 'ClassName' does not exist in game SWF`

## Limitations and Considerations

### Sprites

✅ **Fully Supported**: Creating new sprites works well and is fully functional.

### ActionScript Classes

⚠️ **Partially Supported**: Creating new ActionScript classes is more complex:

1. **ABC Compilation**: The system attempts to compile AS3 source to ABC bytecode, but this may not always work perfectly
2. **FFDec Library**: Relies on FFDec's capabilities for ABC manipulation
3. **Fallback**: If automatic creation fails, you may need to:
   - Manually add the script to the SWF using FFDec GUI first
   - Or ensure the script exists in the game SWF before modding

### Best Practices

1. **Test Thoroughly**: Always test new assets in-game to ensure they work correctly
2. **Check Logs**: Review debug logs to see if assets were created successfully
3. **ActionScript**: For complex ActionScript classes, consider adding them to the game SWF first using FFDec GUI
4. **Dependencies**: Ensure all sprite dependencies (shapes, bitmaps, fonts) are properly included

## Technical Details

### Files Modified

1. **`core/core/swf/swf.py`**:
   - Added `addAS3()` method for creating new ActionScript classes
   - Added DoABC tag support

2. **`core/core/worker/gameswf.py`**:
   - Enhanced `importSprite()` with `createIfNotExists` parameter
   - Enhanced `importScript()` with `createIfNotExists` parameter
   - Added automatic detection and creation logic

3. **`core/core/worker/mod.py`**:
   - Updated `install()` to detect new assets
   - Added automatic `createIfNotExists=True` for new assets
   - Enhanced debug logging

4. **`core/core/ffdec/classes.py`**:
   - Added DoABCTag and DoABC2Tag class definitions

### Symbol Class Integration

New sprites are automatically added to the SymbolClass, which is crucial for:
- Proper linking between sprites and their ActionScript classes
- Game engine recognition of the assets
- Proper asset loading and rendering

## Future Improvements

Potential enhancements for the future:

1. **Better ABC Compilation**: Improve ActionScript to ABC bytecode compilation
2. **Asset Validation**: Add validation to ensure new assets are properly structured
3. **Conflict Detection**: Enhanced conflict detection for new assets
4. **Uninstall Support**: Better handling of new assets during uninstallation

## Troubleshooting

### New Sprite Not Appearing

1. Check debug logs for creation messages
2. Verify the sprite structure is correct (frames.swf exists)
3. Ensure all dependencies are included
4. Check that the sprite name matches the expected format

### New ActionScript Not Working

1. Check if the class was created (look for success messages in logs)
2. Verify the ActionScript syntax is correct
3. Consider manually adding the script using FFDec GUI first
4. Check that the class name matches the file name

### General Issues

1. Enable debug logging to see detailed creation process
2. Check that the game SWF file is writable
3. Verify mod structure matches expected format
4. Review error messages in the logs

## Conclusion

This feature represents a significant advancement in modding capabilities, allowing modders to add entirely new assets to Brawlhalla. While sprite creation is fully functional, ActionScript creation may require some manual intervention in complex cases. The system is designed to be as automatic as possible while providing detailed feedback through debug logs.





