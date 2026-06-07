import os
import json
import time
import requests
from rich.console import Console

console = Console()

SHARPIST_ICP_CONTEXT = """
Sharpist is a B2B SaaS coaching and people development platform.
Their ideal customers are:
- Industries: Industrial Manufacturing, Retail, FMCG, Energy
- Company size: >1,000 employees
- Region: DACH (Germany, Austria, Switzerland)
- Economic Buyer: CHRO
- Champions: Regional VP HR, Head of Talent, Head of L&D
- Pain points: scaling leadership development, measuring L&D ROI,
  retaining talent through personalised learning journeys
"""

ROUTING_RULES = {
    "priority_dial": 80,
    "email_sequence": 60,
    "filter_out": 0
}


def score_company(company_name: str, registration_data: dict, wiki_data: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("API key not found in environment.")

    briefing = _build_briefing(company_name, registration_data, wiki_data)
    console.print(f"  [cyan]-> Groq:[/cyan] scoring '{company_name}'...")

    prompt = f"""
You are a GTM Engineer at Sharpist, a B2B SaaS coaching platform.
Your job is to score inbound company data for ICP fit.

{SHARPIST_ICP_CONTEXT}

Here is the enriched data for the company you need to score:

{briefing}

Return ONLY a valid JSON object with exactly these fields (no markdown, no backticks, just raw JSON):
{{
  "icp_score": <integer 0-100>,
  "score_rationale": "<2-3 sentences explaining why this score>",
  "target_persona": "<the single best persona to contact first>",
  "cold_call_hook": "<exactly 2 sentences referencing the company specifically>",
  "routing": "<one of: Priority Dial, Email Sequence, Filter Out>",
  "routing_reason": "<one sentence explaining the routing decision>"
}}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 600
            },
            timeout=30
        )

        time.sleep(0.5)

        if response.status_code == 200:
            raw = response.json()
            text = raw["choices"][0]["message"]["content"].strip()
            text = text.replace("```json", "").replace("```", "").strip()
            scoring = json.loads(text)
            scoring = _apply_routing(scoring)
            console.print(f"  [green]OK Score:[/green] {scoring.get('icp_score')}/100 -> {scoring.get('routing')}")
            return scoring

        elif response.status_code == 429:
            console.print(f"  [red]X Rate limit hit. Waiting 10 seconds...[/red]")
            time.sleep(10)
            return _error_result("Rate limited")

        else:
            console.print(f"  [red]X Groq error: HTTP {response.status_code} - {response.text[:200]}[/red]")
            return _error_result(f"HTTP {response.status_code}")

    except json.JSONDecodeError as e:
        console.print(f"  [red]X JSON parse error: {e}[/red]")
        return _error_result("JSON parse error")

    except Exception as e:
        console.print(f"  [red]X Unexpected error: {e}[/red]")
        return _error_result(str(e))


def _build_briefing(company_name: str, reg: dict, wiki: dict) -> str:
    return f"""
COMPANY NAME: {company_name}

--- REGISTRATION DATA ---
Official Name: {reg.get('name', 'Unknown')}
Jurisdiction: {reg.get('jurisdiction', 'Unknown')}
Status: {reg.get('status', 'Unknown')}

--- BUSINESS CONTEXT (Wikipedia) ---
{wiki.get('summary', 'No context available.')}
""".strip()


def _apply_routing(scoring: dict) -> dict:
    score = scoring.get("icp_score", 0)
    if score >= ROUTING_RULES["priority_dial"]:
        scoring["routing"] = "Priority Dial"
    elif score >= ROUTING_RULES["email_sequence"]:
        scoring["routing"] = "Email Sequence"
    else:
        scoring["routing"] = "Filter Out"
    return scoring


def _error_result(reason: str) -> dict:
    return {
        "icp_score": 0,
        "score_rationale": f"Scoring failed: {reason}",
        "target_persona": "Unknown",
        "cold_call_hook": "Unable to generate hook due to scoring error.",
        "routing": "Filter Out",
        "routing_reason": f"Defaulting to Filter Out due to error: {reason}"
    }