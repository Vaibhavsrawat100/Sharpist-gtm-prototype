"""
main.py
-------
The orchestrator. Run this file and it handles everything:
  1. Loads target companies from input/companies.json
  2. Fetches registration data from OpenCorporates API (API 1)
  3. Fetches business context from Wikipedia API (API 2)
  4. Sends combined data to Groq LLM for ICP scoring + routing-aware hook generation
  5. Saves structured results to output/icp_results.json
  6. Prints a colour-coded summary table to the terminal

Usage:
  python main.py
  python main.py --company "Henkel" --country de   (single company mode)
"""

import json
import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

from modules.company_lookup import lookup_company
from modules.enrichment import get_company_context
from modules.ai_scorer import score_company
from modules.exporter import save_results, print_summary_table

console = Console()


def process_company(company_name: str, country_code: str) -> dict:
    console.print(f"\n[bold white]Processing:[/bold white] [bold cyan]{company_name}[/bold cyan]")
    console.print("─" * 50)

    registration_data = lookup_company(company_name, country_code)
    wiki_data = get_company_context(company_name)
    scoring = score_company(company_name, registration_data, wiki_data)

    result = {
        "company_name": company_name,
        "country_code": country_code.upper(),
        "icp_score": scoring.get("icp_score", 0),
        "routing": scoring.get("routing", "Filter Out"),
        "target_persona": scoring.get("target_persona", "Unknown"),
        "outreach_hook": scoring.get("outreach_hook", ""),
        "hook_type": scoring.get("hook_type", "none"),
        "score_rationale": scoring.get("score_rationale", ""),
        "routing_reason": scoring.get("routing_reason", ""),
        "enrichment": {
            "opencorporates": registration_data,
            "wikipedia": wiki_data
        }
    }

    return result


def run_batch(companies: list) -> list:
    results = []
    for i, company in enumerate(companies, 1):
        name = company.get("name", "").strip()
        country = company.get("country", "de").strip()
        if not name:
            console.print(f"[yellow]⚠ Skipping entry {i} — no company name provided[/yellow]")
            continue
        result = process_company(name, country)
        results.append(result)
    return results


def run_single(company_name: str, country_code: str) -> list:
    return [process_company(company_name, country_code)]


def validate_environment():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        console.print(Panel(
            "[red]GROQ_API_KEY is missing or not set.[/red]\n\n"
            "1. Copy [bold].env.example[/bold] to [bold].env[/bold]\n"
            "2. Paste your Groq API key (starts with gsk_...)\n"
            "3. Get a free key at: [link]https://console.groq.com[/link]",
            title="⚠ Missing API Key",
            border_style="red"
        ))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Sharpist GTM Prototype — ICP enrichment and scoring pipeline"
    )
    parser.add_argument("--company", type=str, help="Single company name to process")
    parser.add_argument("--country", type=str, default="de", help="Country code: de, at, ch (default: de)")
    args = parser.parse_args()

    validate_environment()

    console.print(Panel(
        "[bold blue]Sharpist GTM Prototype[/bold blue]\n"
        "Automated ICP Enrichment & Scoring Pipeline\n\n"
        "[dim]APIs: OpenCorporates + Wikipedia → Groq LLM (llama-3.3-70b)[/dim]",
        border_style="blue"
    ))

    if args.company:
        console.print(f"\n[bold]Mode:[/bold] Single company — '{args.company}'")
        results = run_single(args.company, args.country)
    else:
        input_file = "input/companies.json"
        if not os.path.exists(input_file):
            console.print(f"[red]✗ Input file not found: {input_file}[/red]")
            sys.exit(1)
        with open(input_file, "r", encoding="utf-8") as f:
            companies = json.load(f)
        console.print(f"\n[bold]Mode:[/bold] Batch — {len(companies)} companies from {input_file}")
        results = run_batch(companies)

    if not results:
        console.print("[red]No results generated. Check your input file.[/red]")
        sys.exit(1)

    output_path = save_results(results)
    print_summary_table(results)

    console.print(f"\n[bold green]✓ Done.[/bold green] {len(results)} companies processed.")
    console.print(f"[dim]Full results: {output_path}[/dim]\n")


if __name__ == "__main__":
    main()
