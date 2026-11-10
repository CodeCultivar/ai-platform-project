# AI Platform Project

A small FastAPI service that provides a health check and a question-and-answer endpoint. The `/ask` endpoint sends the question to Claude (`claude-haiku-5-5`) and returns the answer as JSON.

Configuration is read from a `.env` file in the repository root:

- `ANTHROPIC_API_KEY`: your Anthropic API key.
- `CLAUDE_MODEL` (optional, default `claude-haiku-5-5`): the Claude model used for answers.
- `MAX_TOKEN` (optional, default `1024`): the maximum number of tokens in a model reply.
- `REQUEST_TIMEOUT_SECONDS` (optional, default `15`): the timeout for each model call attempt.
- `MAX_ATTEMPTS` (optional, default `3`): the total number of attempts per question, including the first.
- `RETRY_DELAY_SECONDS` (optional, default `0.5`): the pause between attempts.

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
| `POST` | `/ask` | Accepts a question and returns the model's answer. |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What does a cow say?"}'
```

The question must be between 10 and 5,000 characters. Successful responses have the form:

```json
{"answer": "A cow says moo."}
```

Each model call has a 15-second timeout and is retried up to 3 times in total, with a 0.5-second pause between attempts. If the model call still fails, the service returns a JSON error with one of these statuses:

| Status | `error` | When |
|---|---|---|
| `504` | `model_timeout` | Every attempt timed out. |
| `502` | `model_unavailable` | Connection failures, rate limits, or server errors persisted across all attempts. |
| `502` | `model_error` | The model rejected the request (for example, an invalid API key). Not retried. |
| `502` | `model_invalid_response` | The model reply contained no text. |

```json
{"error": "model_timeout", "message": "The model did not respond in time."}
```

Invalid requests are rejected with HTTP `422`.

## Tests

Run the test suite from the repository root:

```bash
PYTHONPATH=src python -m pytest tests/
```

The tests cover the health check, a valid question, and invalid question input. A GitHub Actions workflow at `.github/workflows/tests.yml` runs this command on every push.
