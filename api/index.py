"""LLM Council API for Vercel Serverless."""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import asyncio
import uuid
import urllib.request
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

# Try to import httpx, handle if not available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ============== CONFIG ==============

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")
ALLOWED_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "").split(",")
    if email.strip()
]

# Upstash Redis (Vercel KV replacement)
KV_URL = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
KV_TOKEN = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

AVAILABLE_MODELS = [
    "openai/gpt-5.2",
    "openai/gpt-5.1",
    "openai/gpt-4.1",
    "anthropic/claude-opus-4.5",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-3-pro-preview",
    "google/gemini-2.5-pro",
    "x-ai/grok-4",
    "x-ai/grok-3",
]

COUNCIL_MODELS = [
    "anthropic/claude-opus-4.5",
    "openai/gpt-5.2",
    "x-ai/grok-4",
    "google/gemini-3-pro-preview",
]

CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ============== VERCEL KV ==============

def kv_get(key):
    if not KV_URL or not KV_TOKEN:
        return None
    try:
        req = urllib.request.Request(f"{KV_URL}/get/{key}")
        req.add_header("Authorization", f"Bearer {KV_TOKEN}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data.get("result")
            return json.loads(result) if result else None
    except Exception as e:
        print(f"KV get error: {e}")
        return None

def kv_set(key, value):
    if not KV_URL or not KV_TOKEN:
        return False
    try:
        url = f"{KV_URL}/set/{key}"
        data = json.dumps(value).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {KV_TOKEN}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"KV set error: {e}")
        return False

# ============== AUTH ==============

def check_auth(password, email):
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

# ============== SESSIONS ==============

def get_user_sessions(email):
    key = f"sessions:{email.lower()}"
    sessions = kv_get(key)
    return sessions if sessions else []

def save_user_sessions(email, sessions):
    key = f"sessions:{email.lower()}"
    return kv_set(key, sessions)

def create_session(email, title="New Conversation"):
    sessions = get_user_sessions(email)
    new_session = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "title": title,
        "messages": []
    }
    sessions.insert(0, new_session)  # Newest first
    save_user_sessions(email, sessions)
    return new_session

def get_session(email, session_id):
    sessions = get_user_sessions(email)
    for s in sessions:
        if s["id"] == session_id:
            return s
    return None

def update_session(email, session_id, updates):
    sessions = get_user_sessions(email)
    for i, s in enumerate(sessions):
        if s["id"] == session_id:
            sessions[i].update(updates)
            save_user_sessions(email, sessions)
            return sessions[i]
    return None

def add_message_to_session(email, session_id, message):
    sessions = get_user_sessions(email)
    for i, s in enumerate(sessions):
        if s["id"] == session_id:
            sessions[i]["messages"].append(message)
            # Update title from first user message if still default
            if sessions[i]["title"] == "New Conversation" and message.get("role") == "user":
                content = message.get("content", "")
                sessions[i]["title"] = content[:50] + ("..." if len(content) > 50 else "")
            save_user_sessions(email, sessions)
            return True
    return False

def delete_session(email, session_id):
    sessions = get_user_sessions(email)
    sessions = [s for s in sessions if s["id"] != session_id]
    save_user_sessions(email, sessions)
    return True

# ============== OPENROUTER ==============

async def query_model(model, messages, timeout=120.0, web_search=False):
    if not HTTPX_AVAILABLE:
        return None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages}
    if web_search:
        payload["plugins"] = [{"id": "web"}]
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data['choices'][0]['message']
            return {'content': message.get('content', '')}
    except Exception as e:
        print(f"Error querying {model}: {e}")
        return None

async def query_models_parallel(models, messages, web_search=False):
    tasks = [query_model(model, messages, web_search=web_search) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: resp for model, resp in zip(models, responses)}

# ============== COUNCIL ==============

async def stage1_collect_responses(user_query, models=None):
    models_to_use = models or COUNCIL_MODELS
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(models_to_use, messages, web_search=True)
    return [{"model": m, "response": r.get('content', '')} for m, r in responses.items() if r]

async def stage2_collect_rankings(user_query, stage1_results, models=None):
    models_to_use = models or COUNCIL_MODELS
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {f"Response {l}": r['model'] for l, r in zip(labels, stage1_results)}

    responses_text = "\n\n".join([f"Response {l}:\n{r['response']}" for l, r in zip(labels, stage1_results)])

    ranking_prompt = f"""Evaluate these responses to: {user_query}

{responses_text}

Evaluate each response, then provide:
FINAL RANKING:
1. Response X
2. Response Y
..."""

    messages = [{"role": "user", "content": ranking_prompt}]
    responses = await query_models_parallel(models_to_use, messages)

    results = []
    for model, resp in responses.items():
        if resp:
            text = resp.get('content', '')
            parsed = parse_ranking(text)
            results.append({"model": model, "ranking": text, "parsed_ranking": parsed})

    return results, label_to_model

async def stage3_synthesize(user_query, stage1_results, stage2_results, chairman=None):
    chairman = chairman or CHAIRMAN_MODEL

    s1_text = "\n\n".join([f"{r['model']}: {r['response']}" for r in stage1_results])
    s2_text = "\n\n".join([f"{r['model']}: {r['ranking']}" for r in stage2_results])

    prompt = f"""You are the Chairman. Synthesize the best answer.

Question: {user_query}

Responses:
{s1_text}

Rankings:
{s2_text}

Provide the final answer:"""

    messages = [{"role": "user", "content": prompt}]
    resp = await query_model(chairman, messages)

    if not resp:
        return {"model": chairman, "response": "Error: Unable to synthesize."}
    return {"model": chairman, "response": resp.get('content', '')}

def parse_ranking(text):
    if "FINAL RANKING:" in text:
        section = text.split("FINAL RANKING:")[1]
        matches = re.findall(r'\d+\.\s*Response [A-Z]', section)
        if matches:
            return [re.search(r'Response [A-Z]', m).group() for m in matches]
    return re.findall(r'Response [A-Z]', text)

def calc_aggregate(stage2_results, label_to_model):
    positions = defaultdict(list)
    for r in stage2_results:
        for i, label in enumerate(parse_ranking(r['ranking']), 1):
            if label in label_to_model:
                positions[label_to_model[label]].append(i)

    agg = [{"model": m, "average_rank": round(sum(p)/len(p), 2)} for m, p in positions.items() if p]
    agg.sort(key=lambda x: x['average_rank'])
    return agg

# ============== HANDLER ==============

class handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Password, X-Auth-Email')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_sse(self, event_type, data=None, metadata=None):
        event = {"type": event_type}
        if data is not None:
            event["data"] = data
        if metadata is not None:
            event["metadata"] = metadata
        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
        self.wfile.flush()

    def get_auth(self):
        password = self.headers.get('X-Auth-Password', '')
        email = self.headers.get('X-Auth-Email', '')
        return password, email

    def check_auth(self):
        password, email = self.get_auth()
        return check_auth(password, email)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Password, X-Auth-Email')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/api' or path == '/api/':
            self.send_json({"status": "ok", "service": "LLM Council API"})
            return

        if path == '/api/models':
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return
            self.send_json({
                "available_models": AVAILABLE_MODELS,
                "default_council_models": COUNCIL_MODELS,
                "default_chairman_model": CHAIRMAN_MODEL
            })
            return

        if path == '/api/sessions':
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return
            _, email = self.get_auth()
            sessions = get_user_sessions(email)
            # Return summary only (no full messages)
            summary = [{"id": s["id"], "title": s["title"], "created_at": s["created_at"], "message_count": len(s["messages"])} for s in sessions]
            self.send_json(summary)
            return

        # GET /api/sessions/{id}
        if path.startswith('/api/sessions/'):
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return
            _, email = self.get_auth()
            session_id = path.split('/api/sessions/')[1]
            session = get_session(email, session_id)
            if session:
                self.send_json(session)
            else:
                self.send_json({"error": "Session not found"}, 404)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/api/sessions':
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return
            _, email = self.get_auth()
            session = create_session(email)
            self.send_json(session)
            return

        if path == '/api/council':
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return

            _, email = self.get_auth()
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            user_query = body.get('content', '')
            if not user_query:
                self.send_json({"error": "content required"}, 400)
                return

            session_id = body.get('session_id')
            council_models = body.get('council_models', COUNCIL_MODELS)
            chairman = body.get('chairman_model', CHAIRMAN_MODEL)

            # Send SSE headers
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Run council and save results
            async def run():
                self.send_sse("stage1_start")
                s1 = await stage1_collect_responses(user_query, council_models)
                self.send_sse("stage1_complete", s1)

                if not s1:
                    self.send_sse("error", {"message": "All models failed"})
                    return

                self.send_sse("stage2_start")
                s2, label_map = await stage2_collect_rankings(user_query, s1, council_models)
                agg = calc_aggregate(s2, label_map)
                self.send_sse("stage2_complete", s2, {"label_to_model": label_map, "aggregate_rankings": agg})

                self.send_sse("stage3_start")
                s3 = await stage3_synthesize(user_query, s1, s2, chairman)
                self.send_sse("stage3_complete", s3)

                # Save to session if session_id provided
                if session_id:
                    # Add user message
                    add_message_to_session(email, session_id, {"role": "user", "content": user_query})
                    # Add assistant message with all stages
                    assistant_msg = {
                        "role": "assistant",
                        "stage1": s1,
                        "stage2": s2,
                        "stage3": s3,
                        "metadata": {"label_to_model": label_map, "aggregate_rankings": agg}
                    }
                    add_message_to_session(email, session_id, assistant_msg)

                self.send_sse("complete")

            asyncio.run(run())
            return

        self.send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        # DELETE /api/sessions/{id}
        if path.startswith('/api/sessions/'):
            valid, error = self.check_auth()
            if not valid:
                self.send_json({"error": error}, 401)
                return
            _, email = self.get_auth()
            session_id = path.split('/api/sessions/')[1]
            delete_session(email, session_id)
            self.send_json({"success": True})
            return

        self.send_json({"error": "Not found"}, 404)
