"""Launch the FastAPI backend from the correct directory (dev mode).

Resolves all paths relative to this file, so it works regardless of where
the project lives on disk. Prefers the project venv's Python if present,
otherwise falls back to the interpreter running this script.
"""
import os
import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).resolve().parent
backend_dir = project_root / "backend"

# Prefer a project-local venv interpreter, else use the current one.
venv_candidates = [
    backend_dir / "venv" / "Scripts" / "python.exe",   # Windows
    backend_dir / "venv" / "bin" / "python",           # POSIX
    project_root / "venv" / "Scripts" / "python.exe",
    project_root / "venv" / "bin" / "python",
]
python_exe = next((str(p) for p in venv_candidates if p.exists()), sys.executable)

os.chdir(str(backend_dir))
subprocess.run([
    python_exe, "-m", "uvicorn",
    "app.main:app",
    "--reload",
    "--port", "8000",
    "--host", "127.0.0.1",
])
