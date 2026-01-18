# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Development Commands

### Setup
```bash
# Backend (uses uv for Python package management)
uv sync

# Frontend
cd frontend && npm install
```

### Running the Application
```bash
# Option 1: Start both servers
./start.sh

# Option 2: Run manually (two terminals)
# Terminal 1 - Backend (port 8001):
uv run python -m backend.main

# Terminal 2 - Frontend (port 5173):
cd frontend && npm run dev
```

### Linting
```bash
cd frontend && npm run lint
```

### Building
```bash
cd frontend && npm run build
```

## Architecture

### Three-Stage Pipeline
```
User Query
    ↓
Stage 1: Parallel queries → [individual responses from all council models]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
```

### Backend (`backend/`)
- **`config.py`**: `COUNCIL_MODELS` list and `CHAIRMAN_MODEL` - edit here to change which models participate
- **`council.py`**: Core 3-stage logic. `stage2_collect_rankings()` anonymizes responses as "Response A, B, C" and returns `label_to_model` mapping for de-anonymization
- **`openrouter.py`**: Async model queries via OpenRouter API with graceful degradation (continues if some models fail)
- **`storage.py`**: JSON-based conversation storage in `data/conversations/`
- **`main.py`**: FastAPI app with CORS for localhost:5173 and localhost:3000

### Frontend (`frontend/src/`)
- **`App.jsx`**: Main orchestration, conversation state management
- **`components/Stage1.jsx`**: Tab view of individual model responses
- **`components/Stage2.jsx`**: Raw evaluations with client-side de-anonymization, shows parsed rankings for validation
- **`components/Stage3.jsx`**: Final chairman synthesis (green background)

## Key Design Decisions

### De-anonymization Strategy
- Models receive anonymous labels: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names for readability, but original evaluation used anonymous labels
- Metadata (label_to_model, aggregate_rankings) is NOT persisted to storage, only returned via API

### Stage 2 Prompt Format
Strict format for reliable parsing:
1. Evaluate each response individually
2. "FINAL RANKING:" header
3. Numbered list: "1. Response C", "2. Response A"
4. No text after ranking section

## Common Gotchas

1. **Module Import Errors**: Always run backend as `uv run python -m backend.main` from project root, not from backend directory. Backend uses relative imports.
2. **Port Configuration**: Backend runs on 8001 (not 8000). Update both `backend/main.py` and `frontend/src/api.js` if changing.
3. **Markdown Rendering**: Wrap ReactMarkdown in `<div className="markdown-content">` for proper 12px padding (defined in `index.css`).
4. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order.
