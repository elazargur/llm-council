## 2026-01-18 | Fixed Invalid OpenRouter Model IDs

**Goal**: Debug "Unable to generate final synthesis" error in Stage 3 of the LLM Council.

**Done**:
- Identified root cause: `google/gemini-3-pro` returning 400 Bad Request (invalid model ID on OpenRouter)
- Queried OpenRouter API to get valid model IDs
- Fixed `config.py` with correct model names (`gemini-3-pro` → `gemini-3-pro-preview`)
- Updated council to user's preferred models: Claude Opus 4.5, GPT 5.2, Grok 4, Gemini 3 Pro Preview
- Cleaned up AVAILABLE_MODELS list (removed invalid groq models, fixed haiku ID)

**Pending**:
- None

**Decisions**:
- Kept `google/gemini-3-pro-preview` as chairman model (same as before, just corrected ID)

**Changed**: [backend/config.py]

---
