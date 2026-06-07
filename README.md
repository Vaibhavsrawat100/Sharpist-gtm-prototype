# Sharpist GTM Prototype
### Automated ICP Enrichment & Scoring Pipeline

Built as Part 2 of the Sharpist GTM Engineer case study.

---

## What This Does

This script automates the research and qualification step of Sharpist's outbound pipeline. You give it a list of DACH company names. It returns an ICP score, routing decision, target persona, and a personalised cold call hook for each one — automatically.

**Pipeline:**
```
Input (companies.json)
    ↓
OpenCorporates API  →  Registration data (jurisdiction, status, company type)
Wikipedia API       →  Business context (industry, size, what they do)
    ↓
Google Gemini LLM   →  ICP score (0–100) + cold call hook + persona
    ↓
Output (icp_results.json) + terminal summary table
```

**How it maps to the real Founder-OS architecture:**
| Prototype | Real Pipeline |
|-----------|--------------|
| OpenCorporates | Clay enrichment waterfall (Cognism → Apollo → Lusha) |
| Wikipedia | Pre-Disco Research agent (Langdock) |
| Gemini scoring | Emaily agent + ICP Identifier prompt (Langdock) |
| icp_results.json | HubSpot CRM sync via hubspot.py |

---

## Setup

### 1. Prerequisites
- Python 3.8 or higher
- A free Google Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### 2. Install dependencies
```bash
pip install requests google-generativeai python-dotenv rich
```

### 3. Set up your API key
```bash
cp .env.example .env
```
Open `.env` and replace `your_gemini_api_key_here` with your actual key:
```
GEMINI_API_KEY=AIzaSy...your_key_here
```

### 4. Add your target companies (optional)
Edit `input/companies.json` with the companies you want to score:
```json
[
  { "name": "Siemens AG", "country": "de" },
  { "name": "Voestalpine", "country": "at" },
  { "name": "Nestlé", "country": "ch" }
]
```
Country codes: `de` = Germany, `at` = Austria, `ch` = Switzerland

---

## Running the Script

### Batch mode (from companies.json):
```bash
python main.py
```

### Single company mode:
```bash
python main.py --company "Henkel" --country de
```

---

## Output

**Terminal:** A colour-coded summary table with scores, routing, and hook previews.

**File:** `output/icp_results.json` — one record per company:
```json
{
  "company_name": "Siemens AG",
  "icp_score": 88,
  "routing": "Priority Dial",
  "target_persona": "CHRO",
  "cold_call_hook": "Siemens AG operates across 190 countries with 300,000+ employees — at that scale, standardising leadership development without losing local relevance is one of the hardest problems in HR. Sharpist works with large enterprises to make coaching scalable and measurable across regions.",
  "score_rationale": "Siemens AG is a large industrial manufacturer headquartered in Germany with a global workforce, placing it squarely in Sharpist's ICP. Scale and industry are both strong fits.",
  "enrichment": { ... }
}
```

**Routing logic** (mirrors the Founder-OS three-tier model):
| Score | Routing | Action |
|-------|---------|--------|
| ≥ 80 | Priority Dial | Pushed to Dialfire power dialer |
| 60–79 | Email Sequence | Handed to Emaily agent for outreach |
| < 60 | Filter Out | Removed from pipeline |

---

## Project Structure
```
sharpist-gtm-prototype/
├── main.py                  # Orchestrator — run this
├── .env                     # Your API key (never commit this)
├── .env.example             # Safe template to share
├── .gitignore
├── README.md
├── input/
│   └── companies.json       # Target companies
├── output/
│   └── icp_results.json     # Generated results
└── modules/
    ├── company_lookup.py    # OpenCorporates API
    ├── enrichment.py        # Wikipedia API
    ├── ai_scorer.py         # Gemini LLM scoring
    └── exporter.py          # Output formatting
```

---

## Error Handling

The pipeline is designed to keep running even when individual steps fail:
- **OpenCorporates not found** → returns empty registration data, pipeline continues
- **Wikipedia not found** → returns fallback text, pipeline continues
- **Gemini rate limit** → waits 10 seconds and returns error result, pipeline continues
- **Missing API key** → clear error message with setup instructions, exits cleanly
- **Malformed JSON from LLM** → caught, logs error, returns safe fallback

---

## APIs Used

| API | Purpose | Auth | Cost |
|-----|---------|------|------|
| [OpenCorporates](https://api.opencorporates.com) | Company registration data | None (free tier) | Free |
| [Wikipedia MediaWiki](https://www.mediawiki.org/wiki/API:Main_page) | Company business context | None | Free |
| [Google Gemini](https://aistudio.google.com) | ICP scoring + hook generation | API key | Free tier (15 req/min) |
