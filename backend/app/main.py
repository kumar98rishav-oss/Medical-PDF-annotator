"""
FastAPI app — serves both API and static frontend.
Enterprise backend redesign.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager

from .database import engine, Base
from .config import STATIC_DIR, IS_FROZEN, DATA_DIR
from .routes import upload, annotations, process, admin, auto_detect, search, batch

from .errors import AppError
from .logging_config import logger

# ── Create all tables ──
Base.metadata.create_all(bind=engine)
from .db_models import upgrade_tables
upgrade_tables(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .config import THUMBNAILS_DIR
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Starting Medical PDF Annotator Backend...")
    yield
    logger.info("Shutting down Medical PDF Annotator Backend...")

# ── App ──
app = FastAPI(
    title="Medical PDF Annotator",
    description="Enterprise-grade local-first medical PDF workflow.",
    version="2.0.0",
    lifespan=lifespan
)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error(f"[{exc.status_code}] {exc.message} | Detail: {exc.internal_detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": type(exc).__name__}
    )

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API routes ──
app.include_router(upload.router)
app.include_router(annotations.router)
app.include_router(process.router)
app.include_router(admin.router)
app.include_router(auto_detect.router)
app.include_router(search.router)
app.include_router(batch.router)


# ── Health / Info ──
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "mode": "desktop" if IS_FROZEN else "development",
        "data_dir": str(DATA_DIR),
        "version": "2.0.0"
    }

# ── Serve Static Frontend ──
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_frontend(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))

else:
    @app.get("/", tags=["Health"])
    async def root():
        return {
            "service": "Medical PDF Annotator",
            "version": "2.0.0",
            "mode": "development",
            "note": "Frontend not built. Run 'npm run dev' in frontend/",
            "docs": "/docs",
        }