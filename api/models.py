"""Models endpoint - returns available models and defaults."""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _shared.config import AVAILABLE_MODELS, COUNCIL_MODELS, CHAIRMAN_MODEL
from _shared.auth import check_auth, get_auth_from_headers


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Password, X-Auth-Email')
        self.end_headers()

    def do_GET(self):
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

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = {
            "available_models": AVAILABLE_MODELS,
            "default_council_models": COUNCIL_MODELS,
            "default_chairman_model": CHAIRMAN_MODEL
        }
        self.wfile.write(json.dumps(response).encode())
