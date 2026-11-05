# AI Platform Project

A small FastAPI service that provides a health check and a mock question-and-answer endpoint. The `/ask` endpoint currently returns a fixed response (`"Moo"`); it is an API scaffold, not yet connected to an AI model.

## Requirements

- Python 3.12 or later
- Dependencies listed in `requirements.txt`

## Run locally

Create and activate a virtual environment, then install the project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the development server from the repository root:

```bash
PYTHONPATH=src uvicorn main:app --reload
```

The API is available at <http://127.0.0.1:8000>. FastAPI's interactive API documentation is at <http://127.0.0.1:8000/docs>.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` when the service is running. |
| `POST` | `/ask` | Accepts a question and returns the current mock answer. |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What does a cow say?"}'
```

The question must be between 10 and 5,000 characters. Successful responses have the form:

```json
{"answer": "Moo"}
```

Invalid requests are rejected with HTTP `422`.

## Tests

Run the test suite from the repository root:

```bash
PYTHONPATH=src python -m pytest tests/
```

The tests cover the health check, a valid question, and invalid question input. A GitHub Actions workflow at `.github/workflows/tests.yml` runs this command on every push.
