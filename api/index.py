"""Main API entry point for Vercel serverless."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import os
import re
import httpx
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

# ============== CONFIG ==============

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")
ALLOWED_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "").split(",")
    if email.strip()
]

AVAILABLE_MODELS = [
    "openai/gpt-5.2",
    "openai/gpt-5.1",
    "openai/gpt-5",
    "openai/o1-pro",
    "openai/o1",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4o",
    "anthropic/claude-opus-4.5",
    "anthropic/claude-opus-4",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3.5-haiku",
    "google/gemini-3-pro-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemini-2.0-flash-001",
    "x-ai/grok-4",
    "x-ai/grok-4-fast",
    "x-ai/grok-3",
    "x-ai/grok-3-mini",
]

COUNCIL_MODELS = [
    "anthropic/claude-opus-4.5",
    "openai/gpt-5.2",
    "x-ai/grok-4",
    "google/gemini-3-pro-preview",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ============== AUTH ==============

def check_auth(password: str, email: str) -> tuple:
    if not AUTH_PASSWORD:
        return False, "Server auth not configured"
    if not password:
        return False, "Password required"
    if password != AUTH_PASSWORD:
        return False, "Invalid password"
    if not email:
        return False, "Email required"
    if email.strip().lower() not in ALLOWED_EMAILS:
        return False, "Email not authorized"
    return True, ""

def get_auth_from_headers(headers: dict) -> tuple:
    password = headers.get("x-auth-password", "") or headers.get("X-Auth-Password", "")
    email = headers.get("x-auth-email", "") or headers.get("X-Auth-Email", "")
    return password, email

# ============== OPENROUTER ==============

async def query_model(model: str, messages: List[Dict[str, str]], timeout: float = 120.0) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data['choices'][0]['message']
            return {'content': message.get('content'), 'reasoning_details': message.get('reasoning_details')}
    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None

async def query_models_parallel(models: List[str], messages: List[Dict[str, str]]) -> Dict[str, Optional[Dict[str, Any]]]:
    tasks = [query_model(model, messages) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}

# ============== COUNCIL ==============

async def stage1_collect_responses(user_query: str, models: List[str] = None) -> List[Dict[str, Any]]:
    models_to_use = models if models else COUNCIL_MODELS
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(models_to_use, messages)
    return [{"model": model, "response": response.get('content', '')} for model, response in responses.items() if response]

async def stage2_collect_rankings(user_query: str, stage1_results: List[Dict[str, Any]], models: List[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    models_to_use = models if models else COUNCIL_MODELS
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {f"Response {label}": result['model'] for label, result in zip(labels, stage1_results)}

    responses_text = "\n\n".join([f"Response {label}:\n{result['response']}" for label, result in zip(labels, stage1_results)])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually.
2. Then, at the very end, provide a final ranking.

IMPORTANT: Format your ranking as:
FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]
    responses = await query_models_parallel(models_to_use, messages)

    stage2_results = []
    for model, response in responses.items():
        if response:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({"model": model, "ranking": full_text, "parsed_ranking": parsed})

    return stage2_results, label_to_model

async def stage3_synthesize_final(user_query: str, stage1_results: List[Dict[str, Any]], stage2_results: List[Dict[str, Any]], chairman_model: str = None) -> Dict[str, Any]:
    chairman = chairman_model if chairman_model else CHAIRMAN_MODEL

    stage1_text = "\n\n".join([f"Model: {r['model']}\nResponse: {r['response']}" for r in stage1_results])
    stage2_text = "\n\n".join([f"Model: {r['model']}\nRanking: {r['ranking']}" for r in stage2_results])

    chairman_prompt = f"""You are the Chairman of an LLM Council.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Synthesize all information into a single, comprehensive answer:"""

    messages = [{"role": "user", "content": chairman_prompt}]
    response = await query_model(chairman, messages)

    if response is None:
        return {"model": chairman, "response": "Error: Unable to generate final synthesis."}
    return {"model": chairman, "response": response.get('content', '')}

def parse_ranking_from_text(ranking_text: str) -> List[str]:
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]
            return re.findall(r'Response [A-Z]', ranking_section)
    return re.findall(r'Response [A-Z]', ranking_text)

def calculate_aggregate_rankings(stage2_results: List[Dict[str, Any]], label_to_model: Dict[str, str]) -> List[Dict[str, Any]]:
    model_positions = defaultdict(list)
    for ranking in stage2_results:
        parsed = parse_ranking_from_text(ranking['ranking'])
        for position, label in enumerate(parsed, start=1):
            if label in label_to_model:
                model_positions[label_to_model[label]].append(position)

    aggregate = [{"model": model, "average_rank": round(sum(pos) / len(pos), 2), "rankings_count": len(pos)} for model, pos in model_positions.items() if pos]
    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate

# ============== FASTAPI APP ==============

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_auth(request: Request):
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
        yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
        stage1_results = await stage1_collect_responses(user_query, models=council_models)
        yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

        if not stage1_results:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'All models failed'}})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
        stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results, models=council_models)
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

        yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
        stage3_result = await stage3_synthesize_final(user_query, stage1_results, stage2_results, chairman_model=chairman_model)
        yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
