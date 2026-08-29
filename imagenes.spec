# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller. Se usa asi:  pyinstaller --clean imagenes.spec"""

a = Analysis(
    ["imagenes.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    # pillow_heif es opcional en el codigo, pero si esta instalado queremos
    # que viaje dentro del .exe para poder leer fotos HEIC de iPhone.
    hiddenimports=[
        "imagenes", "imagenes.cli", "imagenes.config", "imagenes.core",
        "imagenes.report", "imagenes.runner", "imagenes.ui", "imagenes.wizard",
        "PIL.ImageCms", "PIL.ImageSequence", "pillow_heif",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Fuera lo que no usamos: recorta bastante el tamano del ejecutable.
    excludes=["tkinter", "numpy", "matplotlib", "scipy", "pytest",
              "PIL.ImageQt", "PySide6", "PyQt5", "PyQt6"],
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
    name="imagenes",
    icon="imagenes.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
