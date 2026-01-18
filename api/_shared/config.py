"""Configuration for the LLM Council."""

import os

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Auth configuration
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")
ALLOWED_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_EMAILS", "").split(",")
    if email.strip()
]

# Available models for selection in the UI
AVAILABLE_MODELS = [
    # OpenAI - Latest reasoning models
    "openai/gpt-5.2",
    "openai/gpt-5.1",
    "openai/gpt-5",
    "openai/o1-pro",
    "openai/o1",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4o",
    # Anthropic - Latest reasoning models
    "anthropic/claude-opus-4.5",
    "anthropic/claude-opus-4",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3.5-haiku",
    # Google - Latest reasoning models
    "google/gemini-3-pro-preview",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemini-2.0-flash-001",
    # xAI Grok
    "x-ai/grok-4",
    "x-ai/grok-4-fast",
    "x-ai/grok-3",
    "x-ai/grok-3-mini",
]

# Default council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "anthropic/claude-opus-4.5",
    "openai/gpt-5.2",
    "x-ai/grok-4",
    "google/gemini-3-pro-preview",
]

# Default chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
