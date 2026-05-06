Backend services structure (production-friendly):

- api/            -> Canonical Node/Express DPR API service
- backend/        -> Legacy copy kept for backward compatibility
- evaluations/    -> Python AI evaluation API (FastAPI + uvicorn)
- server.js       -> Older Node API entrypoint

Recommended:
1) Run Node API from backend/api/server.js
2) Run AI API from backend/evaluations using uvicorn
