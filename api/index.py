"""
LegalConsult AI - Vercel Serverless Entry Point (Mangum WSGI handler)
"""
import os
import sys
from pathlib import Path

# Fix path: api/index.py -> project root
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DATABASE_PATH", "/tmp/legalconsult.db")

from main import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")
