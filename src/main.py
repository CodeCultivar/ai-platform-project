from fastapi import FastAPI

from ask import router as ask_router

app = FastAPI()
app.include_router(ask_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
