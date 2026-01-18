"""Main API entry point for Vercel serverless."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shared.config import AVAILABLE_MODELS, COUNCIL_MODELS, CHAIRMAN_MODEL
from _shared.auth import check_auth, get_auth_from_headers
from _shared.council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings
)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_auth(request: Request):
    """Check authentication from request headers."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    password, email = get_auth_from_headers(headers)
    is_valid, error = check_auth(password, email)
    if not is_valid:
        raise HTTPException(status_code=401, detail=error)


@app.get("/api")
async def health():
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/models")
async def get_models(request: Request):
    verify_auth(request)
    return {
        "available_models": AVAILABLE_MODELS,
        "default_council_models": COUNCIL_MODELS,
        "default_chairman_model": CHAIRMAN_MODEL
    }


@app.post("/api/council")
async def run_council(request: Request):
    verify_auth(request)

    body = await request.json()
    user_query = body.get("content", "")

    if not user_query:
        raise HTTPException(status_code=400, detail="content is required")

    council_models = body.get("council_models", COUNCIL_MODELS)
    chairman_model = body.get("chairman_model", CHAIRMAN_MODEL)

    async def generate():
        # Stage 1
        yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
        stage1_results = await stage1_collect_responses(user_query, models=council_models)
        yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

        if not stage1_results:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'All models failed to respond'}})}\n\n"
            return

        # Stage 2
        yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
        stage2_results, label_to_model = await stage2_collect_rankings(
            user_query, stage1_results, models=council_models
        )
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

        # Stage 3
        yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
        stage3_result = await stage3_synthesize_final(
            user_query, stage1_results, stage2_results, chairman_model=chairman_model
        )
        yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

        # Complete
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
