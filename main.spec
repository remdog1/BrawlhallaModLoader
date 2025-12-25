# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['run.py'],
             binaries=[],
             datas=[('ui/ui_sources', 'ui/ui_sources'), ('tools', 'tools'), ('libs', 'libs'), ('file_icon.ico', '.'), ('splash.png', '.'), ('custom_splash.py', '.'), ('license.txt', '.'), ('mod_timestamps.json', '.'), ('core/core/ffdec/ffdec_lib.jar', 'core/core/ffdec'), ('core/core/ffdec/cmykjpeg.jar', 'core/core/ffdec'), ('core/core/ffdec/jl1.0.1.jar', 'core/core/ffdec'), ('core/core/ffdec/playerglobal32_0.swc', 'core/core/ffdec')],
             hiddenimports=['win32api', 'win32con', 'jpype', 'jpype._jvmfinder', 'pyi_splash'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tkinter', '_tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          Tree("core/core", "core/core", excludes=["*.pyc", "*.pyo"]),
          [],
          name='Brawlhalla Mod Loader 2025 Beta',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          runtime_tmpdir=None,
          console=False,
          uac_admin=False,
          icon='ui/ui_sources/resources/icons/App.ico',
          splash='splash.png')