# Sharpist GTM Prototype
### Automated ICP Enrichment & Scoring Pipeline

Built as Part 2 of the Sharpist GTM Engineer case study.

---

## What This Does

This script automates the research and qualification step of Sharpist's outbound pipeline.
You give it a list of DACH company names. It returns an ICP score, routing decision,
target persona, and a personalised cold call hook for each one — automatically.

**Pipeline:**

```
Input (companies.json)
    ↓
OpenCorporates API        →  Registration data (jurisdiction, status, company type)
Wikipedia API             →  Business context (industry, size, what they do)
    ↓
Groq LLM (llama-3.3-70b) →  ICP score (0-100) + cold call hook + persona
    ↓
Output (icp_results.json) + terminal summary table
```

**How it maps to the real Founder-OS architecture:**

| Prototype | Real Pipeline |
|-----------|---------------|
| OpenCorporates | Clay enrichment waterfall (Cognism → Apollo → Lusha) |
| Wikipedia | Pre-Disco Research agent (Langdock) |
| Groq LLM scoring | Emaily agent + ICP Identifier prompt (Langdock) |
| icp_results.json | HubSpot CRM sync via hubspot.py |

---

## Setup

### 1. Prerequisites
- Python 3.8 or higher
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 2. Install dependencies

```
pip install requests python-dotenv rich
```

### 3. Set up your API key

Copy the example env file:
```
cp .env.example .env
```

Open `.env` in any text editor and paste your Groq key:
```
GEMINI_API_KEY=gsk_your_actual_groq_key_here
```

Note: Never commit your `.env` file. It is listed in `.gitignore` for safety.

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

**Batch mode** — processes all companies in companies.json:
```
python main.py
```

**Single company mode:**
```
python main.py --company "Henkel" --country de
```

---

## Output

**Terminal:** A colour-coded summary table showing scores, routing decisions, and hook previews.

**File:** `output/icp_results.json` is auto-created on each run. Example record:

```json
{
  "company_name": "Siemens AG",
  "icp_score": 95,
  "routing": "Priority Dial",
  "target_persona": "CHRO",
  "cold_call_hook": "Siemens AG operates across 190 countries with 300,000+ employees — at that scale, standardising leadership development without losing local relevance is one of the hardest problems in HR. Sharpist works with large enterprises to make coaching scalable and measurable across regions.",
  "score_rationale": "Large German industrial manufacturer, DACH-based, over 1000 employees. Perfect ICP fit on all dimensions.",
  "routing_reason": "Score 95 exceeds Priority Dial threshold of 80."
}
```

**Routing logic** (mirrors the Founder-OS three-tier model):

| Score | Routing | Action |
|-------|---------|--------|
| >= 80 | Priority Dial | Pushed to Dialfire power dialer |
| 60-79 | Email Sequence | Handed to Emaily agent for outreach |
| < 60 | Filter Out | Removed from pipeline |

---

## Project Structure

```
sharpist-gtm-prototype/
├── main.py                  # Orchestrator — run this
├── .env.example             # Template showing required env variables
├── README.md
├── input/
│   └── companies.json       # Your list of target DACH companies
├── output/
│   └── icp_results.json     # Auto-generated results (created on run)
└── modules/
    ├── company_lookup.py    # Calls OpenCorporates API
    ├── enrichment.py        # Calls Wikipedia API
    ├── ai_scorer.py         # Sends data to Groq LLM, returns ICP score
    └── exporter.py          # Formats output and saves JSON
```

---

## Error Handling

The pipeline keeps running even when individual steps fail:

- **OpenCorporates not found** → returns empty registration data, pipeline continues
- **Wikipedia not found** → returns fallback text, pipeline continues
- **Groq rate limit** → waits 10 seconds, returns safe fallback, pipeline continues
- **Missing API key** → clear error message with setup instructions, exits cleanly
- **Malformed JSON from LLM** → caught and logged, returns safe fallback result

---

## APIs Used

| API | Purpose | Auth | Cost |
|-----|---------|------|------|
| [OpenCorporates](https://api.opencorporates.com) | Company registration data (DACH) | None | Free |
| [Wikipedia MediaWiki](https://www.mediawiki.org/wiki/API:Main_page) | Company business context | None | Free |
| [Groq](https://console.groq.com) | ICP scoring + cold call hook generation | API key | Free tier |
