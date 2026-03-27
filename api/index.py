"""
LegalConsult AI - Vercel Serverless Entry Point (Mangum WSGI handler)
With error diagnostics for FUNCTION_INVOCATION_FAILED
"""
import os
import sys
import traceback
from pathlib import Path

# Fix path: api/index.py -> project root
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DATABASE_PATH", "/tmp/legalconsult.db")

try:
    from main import app
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except Exception as e:
    # Fallback: create a minimal FastAPI app that reports the error
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from mangum import Mangum

    error_app = FastAPI()

    @error_app.get("/")
    @error_app.get("/{path:path}")
    async def error_handler(path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "App initialization failed",
                "detail": str(e),
                "traceback": traceback.format_exc(),
                "python_version": sys.version,
                "sys_path": sys.path[:5],
                "cwd": os.getcwd(),
            }
        )

    handler = Mangum(error_app, lifespan="off")
