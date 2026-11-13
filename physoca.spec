# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("src/physoca/rules", "physoca/rules"),
    ("src/physoca/i18n", "physoca/i18n"),
    ("src/physoca/report/templates", "physoca/report/templates"),
    ("src/physoca/report/static", "physoca/report/static"),
    ("src/physoca/reference/physoca_ref.db", "physoca/reference"),
]
datas += collect_data_files("weasyprint")

a = Analysis(
    ["src/physoca/cli.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="physoca",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
