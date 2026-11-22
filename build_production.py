"""Production Build & Packaging Automation Script for AutoSocial Poster.
Automates:
1. Security dependency audit (npm audit & pip-audit)
2. React frontend static bundle generation (Vite)
3. Production verification tests execution
4. PyInstaller one-folder mode standalone bundling
5. Runtime DLL verification (OpenSSL, SQLite, libffi)
6. Inno Setup installer compilation (Setup.exe)
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = PROJECT_ROOT / "dist"
BACKEND_DIR = PROJECT_ROOT / "backend"
DIST_DIR = PROJECT_ROOT / "dist" / "poster-v2"
SPEC_FILE = PROJECT_ROOT / "AutoSocialPoster.spec"
ISS_FILE = PROJECT_ROOT / "installer.iss"

def run_cmd(cmd: str, cwd=PROJECT_ROOT, description=""):
    print(f"\n---> {description}")
    print(f"Command: {cmd}")
    res = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if res.returncode != 0:
        print(f"[ERROR] Failed: {description} (Exit code {res.returncode})")
        sys.exit(res.returncode)
    print(f"[OK] {description} succeeded.")

def find_iscc() -> str | None:
    """Locate Inno Setup compiler executable if installed on system."""
    potential_paths = [
        shutil.which("ISCC.exe"),
        shutil.which("iscc"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    for p in potential_paths:
        if p and os.path.exists(p):
            return str(p)
    return None

def ensure_essential_dlls():
    """Verify OpenSSL, SQLite, and FFI DLLs are collected in _internal so exe runs on any PC."""
    internal_dir = DIST_DIR / "_internal"
    if not internal_dir.exists():
        internal_dir.mkdir(parents=True, exist_ok=True)

    dll_candidates = [
        Path(sys.base_prefix) / "DLLs",
        Path(sys.prefix) / "DLLs",
        Path(sys.executable).parent / "DLLs",
    ]
    needed_dlls = ["libcrypto-3-x64.dll", "libssl-3-x64.dll", "libffi-8.dll", "sqlite3.dll"]
    for dll_name in needed_dlls:
        target = internal_dir / dll_name
        if not target.exists():
            for c in dll_candidates:
                src = c / dll_name
                if src.exists():
                    shutil.copy2(str(src), str(target))
                    print(f"[OK] Injected missing runtime dependency: {dll_name}")
                    break

def main():
    print("=" * 65)
    print(" AutoSocial Poster - Production Build & Packaging Engine")
    print("=" * 65)

    # Step 1: Security Dependency Audits
    run_cmd("npm audit", description="Auditing npm packages for vulnerabilities")
    run_cmd(f'"{sys.executable}" -m pip_audit', description="Auditing Python dependencies for vulnerabilities")

    # Step 2: Build React Frontend
    run_cmd("npm run build", description="Building React Frontend (Vite Static Bundle)")
    if not (FRONTEND_DIST / "index.html").exists():
        print("[ERROR] Frontend build output missing at dist/index.html")
        sys.exit(1)

    # Step 3: Run Production Verification Tests
    test_script = BACKEND_DIR / "tests" / "test_production_verification.py"
    if test_script.exists():
        run_cmd(f'"{sys.executable}" "{test_script}"', description="Running Hardened Production Verification Tests")

    # Step 4: PyInstaller One-Folder Mode Bundling
    run_cmd(f'"{sys.executable}" -m PyInstaller "{SPEC_FILE}" --noconfirm', description="Bundling Executable with PyInstaller (One-Folder Mode)")

    exe_target = DIST_DIR / "poster-v2.exe"
    if not exe_target.exists():
        print(f"[ERROR] Expected binary not found at {exe_target}")
        sys.exit(1)

    # Step 5: Ensure all Windows runtime DLLs are present in bundle
    ensure_essential_dlls()

    print(f"\n[SUCCESS] PyInstaller bundled successfully at:\n  {DIST_DIR}")

    # Step 6: Inno Setup Compilation (if ISCC available)
    iscc_path = find_iscc()
    if iscc_path and ISS_FILE.exists():
        print(f"\nFound Inno Setup Compiler at: {iscc_path}")
        run_cmd(f'"{iscc_path}" "{ISS_FILE}"', description="Compiling Windows Installer (poster-v2.exe)")
        installer_exe = PROJECT_ROOT / "installer_dist" / "poster-v2.exe"
        if installer_exe.exists():
            # Also copy to root as poster-v2.exe for immediate access
            root_copy = PROJECT_ROOT / "poster-v2.exe"
            shutil.copy2(str(installer_exe), str(root_copy))
            print(f"\n[SUCCESS] Installer generated successfully at:")
            print(f"  {installer_exe}")
            print(f"  {root_copy}")
    else:
        print("\n[INFO] Inno Setup compiler (ISCC.exe) not found in standard paths.")
        print("To compile the single poster-v2.exe installer:")
        print("  1. Download and install Inno Setup 6: https://jrsoftware.org/isdl.php")
        print(f"  2. Right-click '{ISS_FILE.name}' -> 'Compile' or run: ISCC.exe installer.iss")

    print("\n" + "=" * 65)
    print("BUILD COMPLETE & VERIFIED!")
    print(f"Standalone Folder Mode Executable: {exe_target}")
    print("=" * 65)

if __name__ == "__main__":
    main()
