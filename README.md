

https://github.com/user-attachments/assets/511e17d6-6df7-4b66-8330-36520726fe9a




website url: https://multi-agent-research-network.onrender.com/docs
# Multi-Agent Research Network
### CrewAI Market Research Automation Pipeline

A 3-agent CrewAI pipeline (**Researcher → Analyst → Writer**) that automates
competitor analysis, exposed via a FastAPI endpoint with a human-in-the-loop
approval step.

## Architecture

```
POST /research
      │
      ▼
 ┌─────────────┐    ┌────────────┐    ┌────────────┐
 │  Researcher │ -> │  Analyst   │ -> │   Writer   │ -> draft markdown report
 │ (Tavily +   │    │(Calculator)│    │            │
 │  PDF reader)│    │            │    │            │
 └─────────────┘    └────────────┘    └────────────┘
      │
      ▼
 status = "pending_approval"
      │
      ▼
POST /research/{run_id}/approve  (human review)
      │
      ▼
 status = "completed" / "rejected"
```

Resilience layer (`app/crew.py`):
- **Retry logic** — up to 3 attempts with exponential backoff on transient
  errors or a validation failure.
- **Validation guards** — rejects reports that are too short or start with
  an error marker, forcing a retry.
- **Fallback response** — if all retries fail, the API still returns a
  usable markdown report explaining what went wrong, instead of a raw 500.

## Setup

```bash
cd multi-agent-research-network
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY and TAVILY_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Docs at `http://localhost:8000/docs`.

## Usage

**1. Kick off a research run:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Notion",
    "industry": "productivity SaaS",
    "focus_areas": ["pricing", "recent funding", "AI features"]
  }'
```
Returns `{"run_id": "...", "status": "running", ...}`.

**2. Poll for the draft report:**
```bash
curl http://localhost:8000/research/<run_id>
```
Once `status` becomes `"pending_approval"`, `report_markdown` holds the draft.

**3. Approve or reject:**
```bash
curl -X POST http://localhost:8000/research/<run_id>/approve \
  -H "Content-Type: application/json" \
  -d '{"approve": true, "reviewer_notes": "Looks good, ship it."}'
```

## Project layout

```
app/
├── main.py               # FastAPI endpoints + human-in-the-loop gate
├── crew.py               # Crew orchestration, retry/fallback/validation
├── models.py             # Pydantic request/response schemas
├── agents/
│   ├── definitions.py    # Researcher, Analyst, Writer agent configs
│   └── tasks.py          # Task descriptions wiring agents together
└── tools/
    └── custom_tools.py   # TavilySearchTool, PDFReaderTool, CalculatorTool
```

## Notes
- Swap the in-memory `RUNS` dict in `main.py` for Redis/Postgres in production.
- Model defaults to `gpt-4o-mini` (override with `OPENAI_MODEL` in `.env`).
- Target: generates a structured markdown report in well under 2 minutes per run.
