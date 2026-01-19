## 2026-01-19 | Added Web Access for Council Models

**Goal**: Enable LLM council models to search the web when answering questions.

**Done**:
- Added OpenRouter web search plugin to council queries
- Fixed bug: web search was running on all stages, causing Stage 2/3 to hang
- Now only Stage 1 uses web search (answering user's question)
- Added user guide/welcome screen explaining how to use the council

**Pending**:
- None

**Decisions**:
- Used OpenRouter's `plugins: [{"id": "web"}]` parameter (simplest approach)
- Web search only on Stage 1 to avoid unnecessary latency/cost on ranking and synthesis stages

**Changed**: [api/index.py, frontend/src/components/ChatInterface.jsx, frontend/src/components/ChatInterface.css]

---

## 2026-01-18 | Added Session Persistence with Upstash Redis

**Goal**: Save user conversation history so sessions persist across page refreshes.

**Done**:
- Added Vercel KV/Upstash Redis client to api/index.py using urllib.request
- Added session endpoints: GET/POST /api/sessions, GET/DELETE /api/sessions/{id}
- Modified /api/council to accept session_id and auto-save conversations
- Frontend: Added session API methods to api.js
- Frontend: Sessions load on login, auto-create on first message, show in sidebar
- Frontend: Conversation list with titles, dates, message counts, and delete buttons
- Set up Upstash for Redis via Vercel Marketplace (KV moved to marketplace)

**Pending**:
- None

**Decisions**:
- Used Upstash for Redis (Vercel KV replacement via Marketplace)
- Store full conversations per user keyed by email: `sessions:{email}`
- Auto-generate title from first 50 chars of first user message
- Code supports both old KV_REST_API_* and new UPSTASH_REDIS_REST_* env var names

**Changed**: [api/index.py, frontend/src/api.js, frontend/src/App.jsx, frontend/src/components/Sidebar.jsx, frontend/src/components/Sidebar.css]

---

## 2026-01-18 | Added Hebrew RTL Support

**Goal**: Add Hebrew language support with automatic right-to-left text direction.

**Done**:
- Added `dir="auto"` to HTML root and all text content containers
- Replaced hardcoded `padding-left`/`border-left` CSS with logical properties (`padding-inline-start`, `border-inline-start/end`)
- Updated ChatInterface, Stage1, Stage2, Stage3 components with `dir="auto"` on markdown content
- Added `dir="auto"` to textarea input for proper Hebrew typing

**Pending**:
- None

**Decisions**:
- Used auto-detect approach (`dir="auto"`) rather than manual toggle or forced RTL - browser handles Hebrew detection automatically via Unicode Bidirectional Algorithm

**Changed**: [frontend/index.html, frontend/src/index.css, frontend/src/components/Sidebar.css, frontend/src/components/Stage2.css, frontend/src/components/ChatInterface.jsx, frontend/src/components/Stage1.jsx, frontend/src/components/Stage2.jsx, frontend/src/components/Stage3.jsx]

---

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
