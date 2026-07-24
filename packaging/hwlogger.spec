# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

import PySide6
from PyInstaller.utils.hooks import copy_metadata

project_root = Path.cwd()
package_root = project_root / "src" / "hwlogger"

datas = [
    (str(package_root / "resources" / "hwlogger.svg"), "hwlogger/resources"),
    (str(package_root / "resources" / "hwlogger.desktop"), "hwlogger/resources"),
    (str(package_root / "resources" / "style.qss"), "hwlogger/resources"),
]
binaries = []
hiddenimports = [
    "pynvml",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPrintSupport",
]

for distribution in ("hwlogger", "nvidia-ml-py", "pyqtgraph", "psutil"):
    datas += copy_metadata(distribution)

qt_plugins = Path(PySide6.__file__).parent / "Qt" / "plugins"
for plugin_group in (
    "platforms",
    "wayland-decoration-client",
    "wayland-graphics-integration-client",
    "wayland-shell-integration",
    "xcbglintegrations",
    "imageformats",
    "iconengines",
):
    source = qt_plugins / plugin_group
    if source.is_dir():
        datas.append(
            (str(source), f"PySide6/Qt/plugins/{plugin_group}")
        )

a = Analysis(
    [str(package_root / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="HWlogger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(package_root / "resources" / "hwlogger.svg"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HWlogger",
)
