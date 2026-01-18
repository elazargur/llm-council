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
