"""Desktop launcher for AutoSocial Poster.
Starts the local backend server on 127.0.0.1:8000 and opens the UI
in a native pywebview desktop window (with browser fallback).
Enforces single-instance execution to avoid port and database collisions.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure numpy compatibility shim is active before loading any packages
import utils.numpy_compat

import requests
import uvicorn
from config import APP_NAME, HOST, PORT, LOG_FILE_PATH
from utils.logging_config import logger
from utils.single_instance import SingleInstance
from app import app

def show_error_dialog(title: str, message: str):
    """Display native Windows error dialog on fatal launch failure."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass

def wait_for_server(url: str, timeout: int = 15) -> bool:
    """Poll health endpoint until server is responsive."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def run_uvicorn():
    """Start uvicorn server with explicit configuration."""
    logger.info(f"Starting embedded Uvicorn server on http://{HOST}:{PORT}...")
    try:
        config = uvicorn.Config(
            app=app,
            host=HOST,
            port=PORT,
            log_level="warning",
            loop="asyncio",
            lifespan="on",
            log_config=None,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Uvicorn server crashed: {e}")

def main():
    logger.info(f"Initializing {APP_NAME} Launcher...")

    # Single-instance check
    lock = SingleInstance()
    if not lock.acquire():
        logger.warning(f"Another instance of {APP_NAME} is already running. Focusing existing window...")
        webbrowser.open(f"http://{HOST}:{PORT}")
        sys.exit(0)

    # Launch server in background thread
    server_thread = threading.Thread(target=run_uvicorn, daemon=True)
    server_thread.start()

    server_url = f"http://{HOST}:{PORT}"
    health_url = f"{server_url}/api/health"

    if not wait_for_server(health_url, timeout=15):
        err_msg = f"Backend server failed to start within timeout.\nCheck logs at: {LOG_FILE_PATH}"
        logger.error(err_msg)
        show_error_dialog(f"{APP_NAME} Startup Error", err_msg)
        lock.release()
        sys.exit(1)

    logger.info(f"Backend healthy at {server_url}. Opening client interface...")

    # Fast verification mode for automated testing
    if "--check" in sys.argv:
        logger.info("Startup check mode enabled (--check). Validating server and SPA endpoints...")
        try:
            r_health = requests.get(f"{server_url}/api/health", timeout=5.0)
            r_bootstrap = requests.get(f"{server_url}/api/bootstrap", timeout=5.0)
            r_spa = requests.get(f"{server_url}/", timeout=5.0)
            r_index = requests.get(f"{server_url}/index.html", timeout=5.0)
            
            token_present_root = "window.__APP_CONFIG__" in r_spa.text and "sessionToken" in r_spa.text
            token_present_index = "window.__APP_CONFIG__" in r_index.text and "sessionToken" in r_index.text
            
            if r_health.status_code == 200 and r_bootstrap.status_code == 200 and token_present_root and token_present_index:
                print(f"[EXE_VERIFICATION_PASS] Health: {r_health.status_code}, Bootstrap: {r_bootstrap.status_code}, Token Injected: True")
                lock.release()
                sys.exit(0)
            else:
                print(f"[EXE_VERIFICATION_FAIL] Health: {r_health.status_code}, Bootstrap: {r_bootstrap.status_code}, Root Token: {token_present_root}, Index Token: {token_present_index}")
                lock.release()
                sys.exit(1)
        except Exception as exc:
            print(f"[EXE_VERIFICATION_FAIL] Exception: {exc}")
            lock.release()
            sys.exit(1)

    # Try native desktop window via pywebview
    opened_window = False
    try:
        import webview

        class DesktopApi:
            def open_external(self, url: str) -> bool:
                """Open external link or OAuth in operating system's default browser."""
                logger.info(f"DesktopApi: Opening external URL in default browser: {url}")
                return webbrowser.open(url)

        api = DesktopApi()
        logger.info("Launching native window with pywebview...")
        webview.create_window(
            title=APP_NAME,
            url=server_url,
            width=1360,
            height=900,
            min_size=(1024, 720),
            confirm_close=False,
            js_api=api,
        )
        webview.start()
        opened_window = True
    except Exception as e:
        logger.warning(f"Native pywebview window could not be opened ({e}). Falling back to system browser.")

    if not opened_window:
        webbrowser.open(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    lock.release()
    logger.info(f"{APP_NAME} exited gracefully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fatal = f"Fatal launcher crash: {exc}"
        logger.error(fatal)
        show_error_dialog("Fatal Launch Error", fatal)
        sys.exit(1)
