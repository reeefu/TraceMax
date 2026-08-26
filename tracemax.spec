# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TraceMax (SeismoLog Trace Editor).
Cross-platform: generates a single-folder bundle on both Windows and Linux.

Usage:
    pyinstaller tracemax.spec
"""

import os
import sys
import platform

block_cipher = None

# ---------- paths ----------------------------------------------------------
SPEC_DIR = os.path.abspath(SPECPATH)
SRC_DIR  = os.path.join(SPEC_DIR, 'src')
ASSETS   = os.path.join(SRC_DIR, 'assets')

# ---------- icon -----------------------------------------------------------
if platform.system() == 'Windows':
    ICON = os.path.join(ASSETS, 'tracemax.ico')
else:
    ICON = os.path.join(ASSETS, 'tracemax.png')

# ---------- data files to bundle -------------------------------------------
# datas = [(source, destination_folder_in_bundle)]
datas = [
    (os.path.join(ASSETS, 'newlogo.png'),          'assets'),
    (os.path.join(ASSETS, 'seismolog.css'),         'assets'),
    (os.path.join(ASSETS, 'strings.json'),          'assets'),
    (os.path.join(ASSETS, 'tracemax.ico'),          'assets'),
    (os.path.join(ASSETS, 'tracemax.png'),          'assets'),
]

# Include ML model files if any exist
models_dir = os.path.join(SRC_DIR, 'plugin', 'ml_picker', 'models')
if os.path.isdir(models_dir):
    for f in os.listdir(models_dir):
        fpath = os.path.join(models_dir, f)
        if os.path.isfile(fpath) and f != '.gitkeep':
            datas.append((fpath, os.path.join('plugin', 'ml_picker', 'models')))

# ---------- hidden imports -------------------------------------------------
hiddenimports = [
    # PyQt5
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.sip',
    # Numerical / science
    'numpy',
    'scipy',
    'scipy.signal',
    'scipy.fft',
    'scipy.interpolate',
    'scipy.ndimage',
    'obspy',
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    # Seismic I/O
    'segyio',
    'segysak',
    'h5py',
    'h5netcdf',
    'xarray',
    # ML / deep learning
    'torch',
    'torchvision',
    'keras',
    'sklearn',
    'ultralytics',
    # Data
    'pandas',
    'openpyxl',
    'reportlab',
    'python-docx',
    'python-pptx',
    # Misc
    'loguru',
    'cv2',
    'PIL',
    'json',
    'csv',
    # Application packages
    'config',
    'app',
    'app.mainwindow',
    'app.toolbar',
    'app.dialogs',
    'app.arrival_dialog',
    'app.stalta_dialog',
    'app.hagiwara_dialog',
    'core',
    'core.actions',
    'core.autopick',
    'core.plotter',
    'core.refraction',
    'core.trace_model',
    'fileio',
    'fileio.fileio',
    'widgets',
    'widgets.seiswidgets',
    'plugin',
    'plugin.ml_picker',
    'plugin.ml_picker.lstm_base',
    'plugin.ml_picker.lstm_model',
    'plugin.ml_picker.lstm_model_unidirectional',
    'plugin.ml_picker.ml_picker_dialog',
    'plugin.ml_picker.ml_preprocess',
]

# ---------- Analysis -------------------------------------------------------
a = Analysis(
    [os.path.join(SRC_DIR, 'tracemax.py')],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'jupyter',
        'notebook',
        'jupyterlab',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------- PYZ (Python bytecode archive) ----------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------- EXE ------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TraceMax',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                    # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

# ---------- COLLECT (one-folder bundle) ------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TraceMax',
)
