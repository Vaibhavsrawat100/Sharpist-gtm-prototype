# Sharpist GTM Prototype
### Automated ICP Enrichment & Scoring Pipeline

Built as Part 2 of the Sharpist GTM Engineer case study.

---

## What This Does

This script automates the research and qualification step of Sharpist's outbound pipeline.
You give it a list of DACH company names. It returns an ICP score, routing decision,
target persona, and a routing-appropriate outreach hook for each one — automatically.

**Pipeline:**

```
Input (companies.json)
    ↓
OpenCorporates API   →  Registration data (jurisdiction, status, company type)
Wikipedia API        →  Business context (industry, size, what they do)
    ↓
Groq LLM             →  ICP score (0-100) + outreach hook (type varies by routing tier)
    ↓
Output (icp_results.json) + colour-coded terminal summary table
```

**How it maps to the real Founder-OS architecture:**

| Prototype component | Real Founder-OS equivalent |
|---------------------|---------------------------|
| OpenCorporates API | Clay waterfall enrichment (Cognism → Apollo → Lusha) |
| Wikipedia API | Pre-Disco Research agent (Langdock) |
| Groq LLM (direct) | ICP Identifier prompt via Langdock → run_agent() |
| Routing logic in Python | Deterministic threshold gate in pipeline script |
| icp_results.json | HubSpot CRM sync via hubspot.py |

> **Note on LLM choice:** Groq was chosen for the prototype because the free tier has
> high rate limits and low latency, making iteration fast. In production, this scoring
> call routes through Langdock via run_agent() — the prototype demonstrates the logic,
> the production implementation uses the approved Founder-OS AI layer.

---

## Setup

### 1. Prerequisites
- Python 3.8 or higher
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 2. Install dependencies

```bash
pip install requests python-dotenv rich
```

### 3. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and paste your Groq key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

Never commit your `.env` file — it is in `.gitignore`.

### 4. Add your target companies (optional)

Edit `input/companies.json`:
```json
[
  { "name": "Siemens AG", "country": "de" },
  { "name": "Voestalpine", "country": "at" },
  { "name": "Nestle", "country": "ch" }
]
```

Country codes: `de` = Germany, `at` = Austria, `ch` = Switzerland

---

## Running the Script

**Batch mode:**
```bash
python main.py
```

**Single company mode:**
```bash
python main.py --company "Henkel" --country de
```

---

## Output

**Terminal:** Colour-coded summary table — scores, routing, persona, outreach hook preview.
The hook preview is labelled `[CALL]` for Priority Dial companies and `[EMAIL]` for
Email Sequence companies, so the routing tier is immediately clear.

**File:** `output/icp_results.json` — auto-created on each run. Example records:

```json
{
  "company_name": "Siemens AG",
  "icp_score": 95,
  "routing": "Priority Dial",
  "target_persona": "CHRO",
  "outreach_hook": "Siemens AG operates across 190 countries with 300,000+ employees — at that scale, standardising leadership development without losing local relevance is one of the hardest problems in HR. Sharpist works with large enterprises to make coaching scalable and measurable across regions.",
  "hook_type": "cold_call_hook",
  "score_rationale": "Large German industrial manufacturer, DACH-based, over 1000 employees. Perfect ICP fit.",
  "routing_reason": "Score 95 meets Priority Dial threshold (>=80). Sent to Dialfire."
}
```

```json
{
  "company_name": "Lidl",
  "icp_score": 72,
  "routing": "Email Sequence",
  "target_persona": "Head of L&D",
  "outreach_hook": "How Lidl is scaling leadership development across 12,000 stores without a unified L&D platform",
  "hook_type": "email_hook",
  "score_rationale": "Large DACH retailer with significant workforce — fits ICP size and region criteria.",
  "routing_reason": "Score 72 meets Email Sequence threshold (60-79). Handed to Emaily agent."
}
```

**Routing logic:**

| Score | Routing | Hook generated | Action |
|-------|---------|----------------|--------|
| >= 80 | Priority Dial | Cold call hook (2 sentences) | Pushed to Dialfire |
| 60–79 | Email Sequence | Email subject line opener | Handed to Emaily agent |
| < 60  | Filter Out | None | Removed from pipeline |

---

## Project Structure

```
sharpist-gtm-prototype/
├── main.py                  # Orchestrator — run this
├── .env.example             # Copy to .env and add your Groq key
├── README.md
├── input/
│   └── companies.json       # Your DACH target companies
├── output/
│   └── icp_results.json     # Auto-generated on run
└── modules/
    ├── company_lookup.py    # API 1: OpenCorporates
    ├── enrichment.py        # API 2: Wikipedia
    ├── ai_scorer.py         # LLM: Groq (llama-3.3-70b-versatile)
    └── exporter.py          # Saves JSON + prints table
```

---

## Error Handling

- **OpenCorporates not found** → empty registration data, pipeline continues
- **Wikipedia not found** → fallback text, pipeline continues
- **Groq rate limit** → waits 10 seconds, returns safe fallback, pipeline continues
- **Invalid API key** → clear error message with setup instructions
- **Malformed JSON from LLM** → caught, safe fallback returned
- **Network timeout** → caught per module, pipeline continues

---

## APIs Used

| API | Purpose | Auth | Cost |
|-----|---------|------|------|
| [OpenCorporates](https://api.opencorporates.com) | Company registration data (DACH) | None | Free |
| [Wikipedia MediaWiki](https://www.mediawiki.org/wiki/API:Main_page) | Business context | None | Free |
| [Groq](https://console.groq.com) | ICP scoring + outreach hook generation | API key | Free tier |
