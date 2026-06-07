"""
main.py
-------
The orchestrator. Run this file and it handles everything:
  1. Loads target companies from input/companies.json
  2. Fetches registration data from OpenCorporates (API 1)
  3. Fetches business context from Wikipedia (API 2)
  4. Sends combined data to Gemini for ICP scoring + hook generation (LLM)
  5. Saves structured results to output/icp_results.json
  6. Prints a summary table to the terminal

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

# Load environment variables from .env file before anything else
load_dotenv()

from modules.company_lookup import lookup_company
from modules.enrichment import get_company_context
from modules.ai_scorer import score_company
from modules.exporter import save_results, print_summary_table

console = Console()


def process_company(company_name: str, country_code: str) -> dict:
    """
    Run the full enrichment + scoring pipeline for a single company.
    Returns one complete result record.
    """
    console.print(f"\n[bold white]Processing:[/bold white] [bold cyan]{company_name}[/bold cyan]")
    console.print("─" * 50)

    # Step 1: Registration data from OpenCorporates
    registration_data = lookup_company(company_name, country_code)

    # Step 2: Business context from Wikipedia
    wiki_data = get_company_context(company_name)

    # Step 3: AI scoring via Gemini
    scoring = score_company(company_name, registration_data, wiki_data)

    # Step 4: Combine everything into one clean record
    result = {
        "company_name": company_name,
        "country_code": country_code.upper(),
        # Scoring output (top-level for easy filtering in HubSpot)
        "icp_score": scoring.get("icp_score", 0),
        "routing": scoring.get("routing", "Filter Out"),
        "target_persona": scoring.get("target_persona", "Unknown"),
        "cold_call_hook": scoring.get("cold_call_hook", ""),
        "score_rationale": scoring.get("score_rationale", ""),
        "routing_reason": scoring.get("routing_reason", ""),
        # Raw enrichment data (for audit trail / Langdock agent handoff)
        "enrichment": {
            "opencorporates": registration_data,
            "wikipedia": wiki_data
        }
    }

    return result


def run_batch(companies: list) -> list:
    """Process a list of companies from the input JSON file."""
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
    """Process a single company passed via command-line arguments."""
    result = process_company(company_name, country_code)
    return [result]


def validate_environment():
    """Check that required environment variables are present before running."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        console.print(Panel(
            "[red]GEMINI_API_KEY is missing or not set.[/red]\n\n"
            "1. Copy [bold].env.example[/bold] to [bold].env[/bold]\n"
            "2. Replace [bold]your_gemini_api_key_here[/bold] with your actual key\n"
            "3. Get a free key at: [link]https://aistudio.google.com[/link]",
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

    # Check environment before doing anything
    validate_environment()

    console.print(Panel(
        "[bold blue]Sharpist GTM Prototype[/bold blue]\n"
        "Automated ICP Enrichment & Scoring Pipeline\n\n"
        "[dim]APIs: OpenCorporates + Wikipedia → Gemini LLM[/dim]",
        border_style="blue"
    ))

    # Single company mode (via --company flag) or batch mode (from companies.json)
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

    # Save to JSON
    output_path = save_results(results)

    # Print terminal summary table
    print_summary_table(results)

    console.print(f"\n[bold green]✓ Done.[/bold green] {len(results)} companies processed.")
    console.print(f"[dim]Full results: {output_path}[/dim]\n")


if __name__ == "__main__":
    main()
