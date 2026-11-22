# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

project_root = Path.cwd().resolve()
backend_dir = project_root / 'backend'
frontend_dist = project_root / 'dist'

added_files = []
if (frontend_dist / 'index.html').exists():
    added_files.append((str(frontend_dist / 'index.html'), 'dist'))
if (frontend_dist / 'assets').exists():
    added_files.append((str(frontend_dist / 'assets'), 'dist/assets'))

# Collect essential Python Windows runtime DLLs (OpenSSL, SQLite, libffi, vcruntime)
# so the exe is 100% self-contained on other machines without Python installed
extra_binaries = []
dll_search_dirs = [
    Path(sys.base_prefix) / 'DLLs',
    Path(sys.prefix) / 'DLLs',
    Path(sys.executable).parent / 'DLLs',
    Path(sys.base_prefix),
]

for d in dll_search_dirs:
    if d.exists():
        for dll_name in ['libcrypto-3-x64.dll', 'libssl-3-x64.dll', 'libffi-8.dll', 'sqlite3.dll', 'vcruntime140.dll', 'msvcp140.dll']:
            p = d / dll_name
            if p.exists() and not any(b[0] == str(p) for b in extra_binaries):
                extra_binaries.append((str(p), '.'))

hidden_imports = [
    'dotenv',
    'keyring',
    'keyring.backends.Windows',
    'cryptography',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespans',
    'uvicorn.lifespans.on',
    'uvicorn.lifespans.off',
    'fastapi',
    'fastapi.staticfiles',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    'pydantic',
    'pydantic_core',
    'httpx',
    'requests',
    'sqlite3',
    'webview',
    'webview.platforms.winforms',
    'clr_loader',
    'pythonnet',
]

excluded_modules = [
    'pytest',
    'unittest',
    'tests',
    'numpy',
    'scipy',
    'pandas',
    'matplotlib',
]

a = Analysis(
    [str(backend_dir / 'launcher.py')],
    pathex=[str(backend_dir), str(project_root)],
    binaries=extra_binaries,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='poster-v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Desktop GUI, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='poster-v2',
)
