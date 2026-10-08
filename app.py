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
        host=os.getenv("FACE_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8001")),
    )
