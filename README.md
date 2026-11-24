# Compliance & Legal AI Hub (ClauseVerify AI)

An AI-powered Legal & Compliance Knowledge Hub that enforces zero-hallucination verification. Every answer links to an exact physical bounding-box citation on the original signed document.

## Features
- **Split-Screen Dashboard:** Chat and ask complex legal/compliance questions on the left; view highlighted source documents on the right.
- **Visual Bounding-Box Citations:** Clicking any citation badge smoothly scrolls to the page and draws a yellow highlight rectangle over the exact clause.
- **Dual Mode (Demo & Live AI):**
  - **Demo/Mock Mode:** Works out of the box with realistic preloaded contracts (MSAs, SOC 2 reports, SLAs).
  - **Live AI Mode:** Provide your Anthropic (`CLAUDE_API_KEY`) or OpenAI (`OPENAI_API_KEY`) to run real-time contract analysis.
- **Immutable Audit Logging:** Every query, answer, and retrieved chunk is recorded with timestamps for compliance audits.
- **Zero-Dependency Architecture:** Runs out of the box with standard Python (3.10+).

## Quick Start

### 1. Run the Server
```powershell
python server.py
```
Or if using your local Python binary:
```powershell
& 'C:\Users\Yasir\AppData\Local\Python\bin\python.exe' server.py
```

### 2. Open in Browser
Navigate to:
```
http://localhost:8000
```

### 3. (Optional) Enable Live AI Mode
Create a `.env` file or export your API key:
```env
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
```
