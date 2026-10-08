"""CampusHub face embedding service.

This service does not train a model and never records attendance. It uses the
pre-trained InsightFace ArcFace model only to detect one face and return its
normalized embedding. Laravel remains responsible for authorization, matching,
database storage, duplicate checks, and attendance decisions.
"""

from contextlib import asynccontextmanager
import os
import secrets
from typing import Annotated

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from insightface.app import FaceAnalysis


face_analyzer: FaceAnalysis | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load the CPU ArcFace pipeline once when the service starts."""
    global face_analyzer
    if os.getenv("APP_ENV", "local") == "production" and not os.getenv("FACE_SERVICE_API_KEY", "").strip():
        raise RuntimeError("FACE_SERVICE_API_KEY is required in production.")
    face_analyzer = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    yield
    face_analyzer = None


app = FastAPI(
    title="CampusHub Face Embedding Service",
    version="1.0.0",
    lifespan=lifespan,
)


def error_response(message: str, status_code: int = 422) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message},
    )


@app.api_route("/health", methods=["GET", "POST"])
async def health() -> dict[str, str]:
    """Support POST as specified and GET for browser/operations checks."""
    return {"status": "ok", "message": "Face service is running"}


async def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Accept the shared key sent by Laravel; allow keyless local development."""
    expected = os.getenv("FACE_SERVICE_API_KEY", "").strip()
    if not expected:
        if os.getenv("APP_ENV", "local") == "production":
            raise HTTPException(status_code=503, detail="Face service API key is not configured.")
        return
    if not secrets.compare_digest((x_api_key or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid face service API key.")


@app.post("/extract-embedding", dependencies=[Depends(require_api_key)])
async def extract_embedding(image: UploadFile = File(...)):
    """Detect exactly one face and return a normalized ArcFace embedding."""
    if face_analyzer is None:
        return error_response(
            "Face recognition service is currently unavailable.",
            status_code=503,
        )

    try:
        image_bytes = await image.read()
        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    except (cv2.error, ValueError, TypeError):
        frame = None

    if frame is None or frame.size == 0:
        return error_response("Invalid image file.", status_code=400)

    try:
        faces = face_analyzer.get(frame)
    except (cv2.error, RuntimeError, ValueError):
        return error_response("Invalid image file.", status_code=400)

    if len(faces) == 0:
        return error_response(
            "No face detected. Please capture a clear face image."
        )

    if len(faces) > 1:
        return error_response(
            "Multiple faces detected. Please capture only one face."
        )

    # Reject images that are too dark, overexposed, or blurred to be a
    # dependable live capture. This is a quality gate, not a replacement for
    # a dedicated presentation-attack detector.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if brightness < 25 or brightness > 235:
        return error_response(
            "Face image lighting is not suitable. Please move to better light."
        )
    if sharpness < 18:
        return error_response(
            "Face image is too blurry. Please hold the phone steady."
        )

    # InsightFace exposes the ArcFace vector on normed_embedding. Normalize
    # once more defensively so Laravel can use a stable cosine calculation.
    embedding = np.asarray(faces[0].normed_embedding, dtype=np.float32)
    norm = float(np.linalg.norm(embedding))
    if embedding.ndim != 1 or embedding.size == 0 or norm <= 0:
        return error_response("Unable to generate a face embedding.")

    normalized = embedding / norm
    return {
        "success": True,
        "embedding": normalized.astype(float).tolist(),
        "quality": {
            "brightness": brightness,
            "sharpness": sharpness,
        },
        "message": "Face embedding extracted successfully",
    }
