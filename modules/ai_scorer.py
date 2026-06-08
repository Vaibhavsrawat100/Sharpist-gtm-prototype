"""
ai_scorer.py
------------
Sends enriched company data to Groq (llama-3.3-70b) and returns a structured
ICP score, routing decision, target persona, and routing-appropriate outreach hook.

In the real Founder-OS pipeline, this logic lives inside a Langdock Agent and is
called via langdock.py -> run_agent(). The prototype calls Groq directly to
demonstrate the same reasoning — same output structure, same routing logic.

Groq was chosen for the prototype because the free tier has high rate limits
and low latency, which makes iteration fast. In production this call routes
through Langdock anyway, so the LLM provider at the prototype layer does not
affect the architecture.

Routing thresholds (three-tier model):
  >= 80  ->  Priority Dial   (best-fit, sent to Dialfire)
               outreach_hook = cold call hook (rep will actually call)
  60-79  ->  Email Sequence  (mid-fit, handed to Emaily agent)
               outreach_hook = email subject line opener (no call made)
  < 60   ->  Filter Out      (removed from pipeline)
               outreach_hook = "" (no outreach generated)
"""

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
    """
    Send enriched company data to Groq and return a structured ICP scoring result.
    Falls back to a safe error result if anything goes wrong.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment. Check your .env file.")

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
  "outreach_hook": "<see rules below>",
  "hook_type": "<see rules below>",
  "routing": "<one of: Priority Dial, Email Sequence, Filter Out>",
  "routing_reason": "<one sentence explaining the routing decision>"
}}

Rules for outreach_hook and hook_type:
- If icp_score >= 80: outreach_hook = exactly 2 sentences as a cold call hook
  referencing the company specifically (a rep will call this company).
  hook_type = "cold_call_hook"
- If icp_score is 60-79: outreach_hook = a single punchy email subject line opener
  referencing the company specifically (no call will be made, Emaily agent sends email).
  hook_type = "email_hook"
- If icp_score < 60: outreach_hook = "" and hook_type = "none"
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
            # Routing is always enforced deterministically in Python.
            # Groq produces the score; Python applies the threshold.
            # The LLM cannot override business rules.
            scoring = _apply_routing(scoring)
            console.print(f"  [green]OK Score:[/green] {scoring.get('icp_score')}/100 -> {scoring.get('routing')}")
            return scoring

        elif response.status_code == 429:
            console.print(f"  [red]X Rate limit hit. Waiting 10 seconds...[/red]")
            time.sleep(10)
            return _error_result("Rate limited by Groq API")

        elif response.status_code in (401, 403):
            console.print(f"  [red]X Authentication failed — check your GROQ_API_KEY[/red]")
            return _error_result("Authentication failed — invalid API key")

        else:
            console.print(f"  [red]X Groq error: HTTP {response.status_code}[/red]")
            return _error_result(f"HTTP {response.status_code}")

    except json.JSONDecodeError as e:
        console.print(f"  [red]X JSON parse error: {e}[/red]")
        return _error_result("JSON parse error from Groq response")

    except requests.exceptions.Timeout:
        console.print(f"  [red]X Request timed out[/red]")
        return _error_result("Request timed out")

    except requests.exceptions.ConnectionError:
        console.print(f"  [red]X No internet connection[/red]")
        return _error_result("Connection error")

    except Exception as e:
        console.print(f"  [red]X Unexpected error: {e}[/red]")
        return _error_result(str(e))


def _build_briefing(company_name: str, reg: dict, wiki: dict) -> str:
    """Combine registration and Wikipedia data into a single briefing for Groq."""
    return f"""
COMPANY NAME: {company_name}

--- REGISTRATION DATA (OpenCorporates) ---
Official Name: {reg.get('name', 'Unknown')}
Jurisdiction: {reg.get('jurisdiction', 'Unknown')}
Status: {reg.get('status', 'Unknown')}
Company Type: {reg.get('company_type', 'Unknown')}
Incorporation Date: {reg.get('incorporation_date', 'Unknown')}

--- BUSINESS CONTEXT (Wikipedia) ---
{wiki.get('summary', 'No context available.')}
""".strip()


def _apply_routing(scoring: dict) -> dict:
    """
    Apply routing thresholds deterministically.
    Groq produces the ICP score; Python decides the routing bucket.
    This separation ensures business rules can never be overridden by the model.
    """
    score = scoring.get("icp_score", 0)
    if score >= ROUTING_RULES["priority_dial"]:
        scoring["routing"] = "Priority Dial"
        scoring["routing_reason"] = f"Score {score} meets Priority Dial threshold (>=80). Sent to Dialfire."
    elif score >= ROUTING_RULES["email_sequence"]:
        scoring["routing"] = "Email Sequence"
        scoring["routing_reason"] = f"Score {score} meets Email Sequence threshold (60-79). Handed to Emaily agent."
    else:
        scoring["routing"] = "Filter Out"
        scoring["routing_reason"] = f"Score {score} is below minimum threshold (<60). Removed from pipeline."
    return scoring


def _error_result(reason: str) -> dict:
    """Safe fallback result when scoring fails. Pipeline continues without crashing."""
    return {
        "icp_score": 0,
        "score_rationale": f"Scoring failed: {reason}",
        "target_persona": "Unknown",
        "outreach_hook": "",
        "hook_type": "none",
        "routing": "Filter Out",
        "routing_reason": f"Defaulting to Filter Out due to error: {reason}"
    }
