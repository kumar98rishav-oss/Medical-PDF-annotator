"""
Medical PDF Annotator — Desktop Application Launcher
"""

import sys
import os
import socket
import threading
import time
import logging
from pathlib import Path


# ══════════════════════════════════════════════════════
#  PATH SETUP — Must happen BEFORE any app imports
# ══════════════════════════════════════════════════════

def setup_paths():
    """Configure paths for both dev and packaged modes."""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent

        # PyInstaller _MEIPASS for onefile, or exe dir for folder mode
        meipass = getattr(sys, '_MEIPASS', None)

        # Add all possible locations where 'app' package might be
        search_dirs = [
            exe_dir,                           # dist/MedicalPDFAnnotator/
            exe_dir / "backend",               # dist/MedicalPDFAnnotator/backend/
        ]
        if meipass:
            search_dirs.insert(0, Path(meipass))
            search_dirs.insert(1, Path(meipass) / "backend")

        for d in search_dirs:
            if (d / "app" / "__init__.py").exists():
                sys.path.insert(0, str(d))
                break
            elif (d / "app" / "main.py").exists():
                sys.path.insert(0, str(d))
                break

        os.chdir(str(exe_dir))
    else:
        project_root = Path(__file__).parent
        backend_dir = project_root / "backend"
        sys.path.insert(0, str(backend_dir))
        os.chdir(str(project_root))


# ══════════════════════════════════════════════════════
#  LOGGING — Write to file so we can debug packaged exe
# ══════════════════════════════════════════════════════

def setup_logging():
    """Log to file in AppData so we can debug failures."""
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_dir = Path(appdata) / "MedicalPDFAnnotator"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
    else:
        log_file = Path("app.log")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), mode='w', encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger("MedPDFAnnotator")


logger = setup_logging()


# ══════════════════════════════════════════════════════
#  VERIFY IMPORTS — Test that app module is findable
# ══════════════════════════════════════════════════════

def verify_imports():
    """
    Try importing the FastAPI app. If it fails, log exactly why.
    Returns the app object or None.
    """
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"sys.path: {sys.path[:5]}")

    # Check if app directory exists
    for p in sys.path:
        app_dir = Path(p) / "app"
        if app_dir.exists():
            logger.info(f"Found app/ at: {app_dir}")
            contents = list(app_dir.iterdir())
            logger.info(f"  Contents: {[c.name for c in contents]}")
            break
    else:
        logger.error("app/ directory NOT FOUND in any sys.path entry")
        # List what IS in the directories
        for p in sys.path[:3]:
            pp = Path(p)
            if pp.exists():
                logger.error(f"  {pp}: {[c.name for c in pp.iterdir()]}")

    try:
        from app.main import app as fastapi_app
        logger.info("✓ Successfully imported app.main")
        return fastapi_app
    except ImportError as e:
        logger.error(f"✗ Failed to import app.main: {e}")
        logger.error(f"  Full error:", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"✗ Unexpected error importing app: {e}", exc_info=True)
        return None


# ══════════════════════════════════════════════════════
#  SERVER
# ══════════════════════════════════════════════════════

import uvicorn


def find_free_port(start=8000, end=8100) -> int:
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                if sock.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        except Exception:
            continue
    raise RuntimeError(f"No free port found between {start}-{end}")


def wait_for_server(port: int, timeout: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def show_error(message: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, message,
            "Medical PDF Annotator — Error",
            0x10
        )
    except Exception:
        print(f"ERROR: {message}")


class ServerThread(threading.Thread):
    def __init__(self, app_object, port: int):
        super().__init__(daemon=True)
        self.app_object = app_object
        self.port = port
        self.server = None
        self.error = None

    def run(self):
        try:
            config = uvicorn.Config(
                self.app_object,       # ← Pass object directly, NOT string
                host="127.0.0.1",
                port=self.port,
                log_level="warning",
                reload=False,
                access_log=False,
                log_config=None,
                use_colors=False,
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            self.error = str(e)
            logger.error(f"Server thread crashed: {e}", exc_info=True)

    def stop(self):
        if self.server:
            self.server.should_exit = True


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

def main():
    # ── Configure sys.path BEFORE any app import (dev + frozen) ──
    setup_paths()

    logger.info("=" * 50)
    logger.info("Medical PDF Annotator — Starting")
    logger.info("=" * 50)

    # ── Verify the app can be imported ──
    fastapi_app = verify_imports()
    if fastapi_app is None:
        log_location = ""
        if getattr(sys, 'frozen', False):
            appdata = os.environ.get('APPDATA', '')
            log_location = f"\n\nCheck log file:\n{appdata}\\MedicalPDFAnnotator\\app.log"

        show_error(
            "Failed to load the application modules.\n\n"
            "The app package could not be imported."
            f"{log_location}"
        )
        sys.exit(1)

    # ── Find free port ──
    try:
        port = find_free_port()
        logger.info(f"Selected port: {port}")
    except RuntimeError as e:
        show_error(str(e))
        sys.exit(1)

    # ── Start server with the actual app object ──
    server = ServerThread(fastapi_app, port)
    server.start()

    logger.info("Waiting for server...")
    if not wait_for_server(port):
        error_detail = server.error or "Unknown error"
        log_location = ""
        if getattr(sys, 'frozen', False):
            appdata = os.environ.get('APPDATA', '')
            log_location = f"\n\nCheck log:\n{appdata}\\MedicalPDFAnnotator\\app.log"

        show_error(
            f"Server failed to start.\n\n"
            f"Error: {error_detail}\n\n"
            f"Please try:\n"
            f"1. Close any other instances\n"
            f"2. Restart your computer"
            f"{log_location}"
        )
        sys.exit(1)

    logger.info("Server ready!")

    # ── Open window ──
    url = f"http://127.0.0.1:{port}"

    try:
        import webview

        class Api:
            """Exposed to JavaScript as window.pywebview.api"""

            def open_file_dialog(self):
                """Open native file-picker and return the selected PDF path (or None)."""
                try:
                    paths = webview.windows[0].create_file_dialog(
                        webview.OPEN_DIALOG,
                        allow_multiple=False,
                        file_types=("PDF files (*.pdf)", "All files (*.*)")
                    )
                    if paths:
                        p = Path(paths[0])
                        return {"path": str(p), "filename": p.name}
                except Exception as exc:
                    logger.warning(f"open_file_dialog failed: {exc}")
                return None

        window = webview.create_window(
            title="Medical PDF Annotator",
            url=url,
            width=1400,
            height=900,
            min_size=(1000, 600),
            resizable=True,
            confirm_close=False,
            text_select=True,
            js_api=Api(),
        )

        logger.info(f"Opening native window: {url}")
        webview.start(debug=not getattr(sys, 'frozen', False))

    except ImportError:
        logger.warning("pywebview not available, opening in browser")
        import webbrowser
        webbrowser.open(url)
        try:
            input("\nPress Enter to stop the server...\n")
        except (EOFError, KeyboardInterrupt):
            pass
        except RuntimeError as e:
            if "lost sys.stdin" in str(e):
                # We are in windowed mode with no console. Sleep forever to keep server alive.
                # User will have to kill the process via Task Manager since there's no UI.
                while True:
                    time.sleep(1)
            else:
                raise

    logger.info("Shutting down...")
    server.stop()
    time.sleep(0.5)
    logger.info("Done.")


if __name__ == "__main__":
    main()