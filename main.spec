# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['run.py'],
             binaries=[],
             datas=[('ui/ui_sources', 'ui/ui_sources')],
             hiddenimports=['win32api', 'win32con', 'pyi_splash'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tkinter', '_tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
splash = Splash('splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(153, 231),
                text_font="Exo 2",
                text_size=13,
                text_color='#92B7D1')
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          Tree("core", "core", excludes=["*.pyc", "*.pyo"]),
          [],
          splash,
          splash.binaries,
          name='BrawlhallaModLoader+Sound',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          runtime_tmpdir=None,
          version='version.spec',
          console=False,
          uac_admin=False,
          icon='ui/ui_sources/resources/icons/App.ico')
