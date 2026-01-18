"""Minimal test API."""

from fastapi import FastAPI

app = FastAPI()

@app.get("/api")
async def health():
    return {"status": "ok", "service": "LLM Council API"}

@app.get("/api/test")
async def test():
    return {"message": "Python is working!"}
