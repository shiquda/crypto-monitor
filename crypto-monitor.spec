# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/icons', 'assets/icons'), ('assets/sounds', 'assets/sounds'), ('i18n', 'i18n')],
    hiddenimports=['winsdk', 'winsdk.windows.ui.notifications', 'winsdk.windows.data.xml.dom', 'winsdk.windows.foundation', 'winsdk.windows.foundation.collections', 'winsdk.windows.storage.streams', 'winsdk.windows.system', 'packaging', 'desktop_notifier.resources'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='crypto-monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\icons\\crypto-monitor.ico',
)
