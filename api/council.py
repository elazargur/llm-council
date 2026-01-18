"""Council endpoint - runs the 3-stage LLM council with SSE streaming."""

from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shared.config import COUNCIL_MODELS, CHAIRMAN_MODEL
from _shared.auth import check_auth, get_auth_from_headers
from _shared.council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings
)


def send_sse_event(wfile, event_type: str, data: dict = None, metadata: dict = None):
    """Send a Server-Sent Event."""
    event = {"type": event_type}
    if data is not None:
        event["data"] = data
    if metadata is not None:
        event["metadata"] = metadata

    message = f"data: {json.dumps(event)}\n\n"
    wfile.write(message.encode())
    wfile.flush()


async def run_council_streaming(wfile, user_query: str, council_models: list, chairman_model: str):
    """Run the 3-stage council process with streaming updates."""

    # Stage 1
    send_sse_event(wfile, "stage1_start")
    stage1_results = await stage1_collect_responses(user_query, models=council_models)
    send_sse_event(wfile, "stage1_complete", data=stage1_results)

    if not stage1_results:
        send_sse_event(wfile, "error", data={"message": "All models failed to respond"})
        return

    # Stage 2
    send_sse_event(wfile, "stage2_start")
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query, stage1_results, models=council_models
    )
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    send_sse_event(
        wfile,
        "stage2_complete",
        data=stage2_results,
        metadata={
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings
        }
    )

    # Stage 3
    send_sse_event(wfile, "stage3_start")
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        chairman_model=chairman_model
    )
    send_sse_event(wfile, "stage3_complete", data=stage3_result)

    # Complete
    send_sse_event(wfile, "complete")


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Password, X-Auth-Email')
        self.end_headers()

    def do_POST(self):
        # Check authentication
        headers = {k.lower(): v for k, v in self.headers.items()}
        password, email = get_auth_from_headers(headers)
        is_valid, error = check_auth(password, email)

        if not is_valid:
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": error}).encode())
            return

        # Parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        user_query = data.get("content", "")
        if not user_query:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "content is required"}).encode())
            return

        # Get model configuration
        council_models = data.get("council_models", COUNCIL_MODELS)
        chairman_model = data.get("chairman_model", CHAIRMAN_MODEL)

        # Send SSE headers
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Run the council with streaming
        asyncio.run(run_council_streaming(
            self.wfile,
            user_query,
            council_models,
            chairman_model
        ))
