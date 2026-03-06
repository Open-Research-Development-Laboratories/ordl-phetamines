# ORDL Platform Backend

Clean-room FastAPI backend for the ORDL fleet governance platform.

## Run (dev)

```powershell
cd ordl_platform\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8891
```

## Test

```powershell
pytest
```
