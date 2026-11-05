from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

# Define the Request Model
class AskRequest(BaseModel):
    question: str = Field(min_length=10, max_length=5000)

# Define the Response Model
class AskResponse(BaseModel):
    answer: str = Field(min_length=3, max_length=5000)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
async def ask(question_in: AskRequest) -> AskResponse:

    mock_answer = {
        "answer":"Moo"
    }

    return mock_answer