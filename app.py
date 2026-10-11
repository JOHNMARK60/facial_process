"""Compatibility runner; the FastAPI application lives in main.py."""

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

from main import app


if __name__ == "__main__":
    uvicorn.run(
        app,
        # Bind to all interfaces so the service is reachable from Docker,
        # Laravel, or another device on the local network. Override with
        # FACE_BIND_HOST=127.0.0.1 when localhost-only access is preferred.
        host=os.getenv("FACE_BIND_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8001")),
    )
