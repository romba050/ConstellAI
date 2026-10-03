# MED-R5 backend (wired)

## 1) install python deps

```bash
cd backend
python -m venv .venv
# windows:
.venv\Scripts\activate
# mac/linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 2) install engines (from your zips)

Place these zip files inside `backend/` (same folder as `setup_engines.py`), then:

```bash
python setup_engines.py
```

Expected zip names (either with or without leading `~`):
- `potential gene crossover experiment - engine.zip`
- `prev research pubmed 2 - scorer (for early kill confirm bias).zip`
- `supplement_compound - subjective vs objective data.zip`
- `disease overlap 1 - genes.zip`

## 3) run backend

```bash
uvicorn app:app --reload --port 8787
```

Health check:
- `http://localhost:8787/api/health`

## LM Studio

The pubmed scorer engine calls LM Studio by default on:
- `http://localhost:1234/v1/chat/completions`

If LM Studio is not running or times out, the backend keeps the research workflow alive with deterministic screening output.

## Local security posture

Default CORS origins are limited to local Vite hosts:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`

Override with `CORS_ALLOW_ORIGINS` if needed.
