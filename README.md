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
python app.py
```

The runner loads `.env` and defaults to `127.0.0.1:8001` for local use.
Set `FACE_SERVICE_API_KEY` to the same value as in Laravel. Flutter calls Laravel;
Laravel sends the shared key in `X-API-Key` when requesting an embedding.

For local development with automatic reload, use
`uvicorn main:app --env-file .env --host 127.0.0.1 --port 8001 --reload`.

## Hostinger VPS / Dokploy

Deploy this repository separately from Laravel on the VPS `72.60.197.131`.
The DNS A record for `face-ai.slsubc.tech` must point to that IP.

1. Create a Docker Compose deployment using `./docker-compose.yml`.
2. Set `FACE_SERVICE_API_KEY` in Dokploy's Environment to the same value as
   Laravel's deployment. The local `.env` is ignored by Git and Docker; copy the
   key securely into both deployments. Production startup requires this key.
3. Route `face-ai.slsubc.tech` to service `face`, container port `8001`, path `/`,
   and enable HTTPS. Docker binds the process to `0.0.0.0` inside the container;
   its port is not published directly on the server.
4. Deploy. The first startup downloads the model; the `face_models` volume
   preserves it across deployments. Allow time for the initial download.
5. Verify `https://face-ai.slsubc.tech/health`, then set Laravel's
   `FACE_SERVICE_URL=https://face-ai.slsubc.tech` and redeploy Laravel.

This service does not connect to cPanel or MySQL. Only Laravel needs the cPanel
database credentials. The health endpoint is public; extraction requires the
shared API key. If the domain check expects `187.127.121.33`, verify that this
deployment is assigned to the intended server `72.60.197.131`.

## Endpoints

- `GET /health` and `POST /health` return `{"status":"ok","message":"Face service is running"}`.
- `POST /extract-embedding` accepts multipart field `image` and returns one
  normalized embedding. Images with zero or multiple faces are rejected.

Health check:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/health
```

## Verification

Install `httpx` in the development virtual environment, then run
`python -m unittest discover -s tests -v`. The HTTP checks exercise authentication
and health without loading or downloading the face model.
