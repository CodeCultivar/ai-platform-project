import os
import time
import anthropic
from typing import Literal
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# Load the environment variables from the .env file
load_dotenv()

MODEL = "claude-haiku-5-5"
MAX_TOKENS = int(os.getenv("MAX_TOKEN", "1024"))

# Each attempt is capped at REQUEST_TIMEOUT_SECONDS. Retries happen in call_model,
# so the SDK's own retries are turned off to avoid stacking the two.
REQUEST_TIMEOUT_SECONDS = 15.0
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.5

client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0)

# Failures that may succeed on another attempt: dropped connections (including timeouts),
# rate limits, and 5xx responses. Other API errors (bad key, bad request) are not retried.
RETRYABLE_ERRORS = (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)

app = FastAPI()

# Define the Request Model
class AskRequest(BaseModel):
    question: str = Field(min_length=10, max_length=5000)

# Define the Response Model
class AskResponse(BaseModel):
    answer: str

# Define the Error Response Model
class ErrorResponse(BaseModel):
    error: Literal["model_timeout", "model_unavailable", "model_error", "model_invalid_response"]
    message: str

class ModelCallError(Exception):
    def __init__(self, status_code: int, body: ErrorResponse):
        super().__init__(body.message)
        self.status_code = status_code
        self.body = body

def read_text(message) -> str:
    text = "".join(block.text for block in message.content if block.type == "text")
    if not text:
        raise ModelCallError(502, ErrorResponse(error="model_invalid_response", message="The model returned no text."))
    return text

def call_model(question: str) -> str:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": question}],
            )
        except anthropic.APITimeoutError as error:
            if attempt == MAX_ATTEMPTS:
                raise ModelCallError(504, ErrorResponse(error="model_timeout", message="The model did not respond in time.")) from error
        except RETRYABLE_ERRORS as error:
            if attempt == MAX_ATTEMPTS:
                raise ModelCallError(502, ErrorResponse(error="model_unavailable", message="The model is temporarily unavailable.")) from error
        except anthropic.APIError as error:
            raise ModelCallError(502, ErrorResponse(error="model_error", message="The model call failed.")) from error
        else:
            return read_text(message)
        time.sleep(RETRY_DELAY_SECONDS)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Sync on purpose: the SDK call and the retry sleep run in FastAPI's threadpool instead of blocking the event loop.
@app.post(
    "/ask",
    response_model=AskResponse,
    responses={502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
def ask(question_in: AskRequest) -> AskResponse | JSONResponse:
    try:
        answer = call_model(question_in.question)
    except ModelCallError as error:
        return JSONResponse(status_code=error.status_code, content=error.body.model_dump())
    return AskResponse(answer=answer)
