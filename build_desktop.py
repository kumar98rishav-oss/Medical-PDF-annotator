"""
Medical PDF Annotator — PyInstaller Build Script

Builds a single-folder Windows desktop application.
Run: python build_desktop.py

Output: dist/MedicalPDFAnnotator/MedicalPDFAnnotator.exe
"""

import PyInstaller.__main__
import os
import shutil
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")
ICON_PATH = os.path.join(ROOT_DIR, "icon.ico")

print("=" * 60)
print("  Medical PDF Annotator — Desktop Build")
print("=" * 60)

# 1. Build the Frontend
print("\n  Building Frontend (React -> Static Files)...")
frontend_dir = os.path.join(ROOT_DIR, "frontend")
subprocess.run(["npm", "run", "build"], cwd=frontend_dir, shell=True, check=True)

# 2. Clean previous build
for d in [DIST_DIR, BUILD_DIR]:
    if os.path.exists(d):
        print(f"  Cleaning {d}...")
        try:
            shutil.rmtree(d)
        except Exception as e:
            print(f"  Warning: Could not fully clean {d}: {e}")

# Build arguments
args = [
    os.path.join(ROOT_DIR, "launcher.py"),        # Entry point
    "--name=MedicalPDFAnnotator_v2",                 # Output name
    "--windowed",                                 # No console window
    "--noconfirm",                                # Don't ask to overwrite

    # Bundle the backend and frontend static as data
    f"--add-data={os.path.join(ROOT_DIR, 'backend', 'app')};app",
    f"--add-data={os.path.join(ROOT_DIR, 'backend', 'static')};static",
    f"--add-data=C:\\Program Files\\Tesseract-OCR;Tesseract-OCR",

    # Paths
    f"--paths={os.path.join(ROOT_DIR, 'backend')}",

    # Hidden imports that PyInstaller might miss
    "--hidden-import=uvicorn.logging",
    "--hidden-import=uvicorn.loops",
    "--hidden-import=uvicorn.loops.auto",
    "--hidden-import=uvicorn.protocols",
    "--hidden-import=uvicorn.protocols.http",
    "--hidden-import=uvicorn.protocols.http.auto",
    "--hidden-import=uvicorn.protocols.http.h11_impl",
    "--hidden-import=uvicorn.protocols.http.httptools_impl",
    "--hidden-import=uvicorn.protocols.websockets",
    "--hidden-import=uvicorn.protocols.websockets.auto",
    "--hidden-import=uvicorn.lifespan",
    "--hidden-import=uvicorn.lifespan.on",
    "--hidden-import=uvicorn.lifespan.off",
    "--hidden-import=sqlalchemy.dialects.sqlite",
    "--hidden-import=aiofiles",
    "--hidden-import=aiofiles.os",
    "--hidden-import=aiofiles.ospath",
    "--hidden-import=multipart",
    "--hidden-import=app",
    "--hidden-import=app.main",
    "--hidden-import=app.config",
    "--hidden-import=app.database",
    "--hidden-import=app.db_models",
    "--hidden-import=app.models",
    "--hidden-import=app.pdf_processor",
    "--hidden-import=app.logging_config",
    "--hidden-import=app.routes",
    "--hidden-import=app.routes.upload",
    "--hidden-import=app.routes.annotations",
    "--hidden-import=app.routes.process",
    "--hidden-import=app.routes.admin",
    "--hidden-import=app.routes.auto_detect",
    "--hidden-import=app.routes.search",
    "--hidden-import=app.routes.batch",
    "--hidden-import=app.errors",
    "--hidden-import=app.services",
    "--hidden-import=app.services.upload_service",
    "--hidden-import=app.services.annotation_service",
    "--hidden-import=app.services.process_service",
    "--hidden-import=app.processors",
    "--hidden-import=app.processors.pdf_reader",
    "--hidden-import=app.processors.combined_builder",
    "--hidden-import=app.processors.split_builder",
    "--hidden-import=app.validators",
    "--hidden-import=app.validators.pdf_validator",
    "--hidden-import=app.validators.annotation_validator",
    "--hidden-import=app.cleanup",
    "--hidden-import=app.cleanup.lifecycle_manager",
    "--hidden-import=app.text_extractor",
    "--hidden-import=app.auto_annotator",
    "--hidden-import=app.smart_matcher",
    "--hidden-import=fitz",
    "--hidden-import=fitz.fitz",
    "--hidden-import=pymupdf",
    "--hidden-import=pytesseract",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",

    # Collect all submodules for these packages
    "--collect-submodules=app",
    "--collect-all=pymupdf",

    # Exclude unnecessary modules to reduce size
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=scipy",
    "--exclude-module=pandas",
    "--exclude-module=cv2",
    "--exclude-module=torch",
    "--exclude-module=tensorflow",

    # Output directory
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
]

# Add icon if it exists
if os.path.exists(ICON_PATH):
    args.append(f"--icon={ICON_PATH}")
    print(f"  Using icon: {ICON_PATH}")

print("\n  Building with PyInstaller...\n")
# Set UTF8 encoding environment variable to avoid unicode issues
os.environ["PYTHONUTF8"] = "1"
PyInstaller.__main__.run(args)

output_dir = os.path.join(DIST_DIR, "MedicalPDFAnnotator_v2")

print("\n" + "=" * 60)
print(f"  BUILD COMPLETE!")
print(f"  Output: {os.path.join(output_dir, 'MedicalPDFAnnotator_v2.exe')}")
print(f"\n  To distribute: zip the entire '{output_dir}' folder")
print(f"  and share it. The user just double-clicks MedicalPDFAnnotator_v2.exe")
print("=" * 60)
