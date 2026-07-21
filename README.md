# CampusHub Face Embedding Service

This is a small FastAPI service used only for face detection and ArcFace
embedding extraction. It uses InsightFace's pre-trained `buffalo_l` model; it
does not train a new model, authorize users, access MySQL, compare students, or
record attendance. Laravel remains the application backend and source of truth.

## Setup on Windows

```powershell
cd C:\laragon\www\face_service
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

InsightFace downloads the pre-trained model the first time the service starts.
Internet access is therefore needed for that initial startup.

## Run

```powershell
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Keep the service bound to `127.0.0.1`; Flutter must call Laravel, never this
Python process directly.

## Endpoints

- `POST /health` returns `{"status":"ok","message":"Face service is running"}`.
- `POST /extract-embedding` accepts multipart field `image` and returns one
  normalized embedding. Images with zero or multiple faces are rejected.

Health check:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/health
```
