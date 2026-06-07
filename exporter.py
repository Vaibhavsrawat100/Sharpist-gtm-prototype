"""
exporter.py
-----------
Formats and saves the final results to output/icp_results.json.
"""

import json
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "icp_results.json")


def save_results(results: list) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "total_companies": len(results),
        "pipeline_summary": _build_summary(results),
        "companies": results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]✓ Results saved to:[/green] {OUTPUT_FILE}")
    return OUTPUT_FILE


def print_summary_table(results: list):
    table = Table(title="\n🎯 Sharpist ICP Scoring Results", show_header=True, header_style="bold blue")

    table.add_column("Company", style="white", min_width=20)
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Routing", min_width=16)
    table.add_column("Target Persona", min_width=18)
    table.add_column("Hook (preview)", min_width=40)

    sorted_results = sorted(results, key=lambda x: x.get("icp_score", 0), reverse=True)

    for r in sorted_results:
        score = r.get("icp_score", 0)
        routing = r.get("routing", "Unknown")

        if routing == "Priority Dial":
            routing_display = f"[green]{routing}[/green]"
        elif routing == "Email Sequence":
            routing_display = f"[yellow]{routing}[/yellow]"
        else:
            routing_display = f"[red]{routing}[/red]"

        hook = r.get("cold_call_hook", "")
        hook_preview = hook[:60] + "..." if len(hook) > 60 else hook

        table.add_row(
            r.get("company_name", "Unknown"),
            str(score),
            routing_display,
            r.get("target_persona", "Unknown"),
            hook_preview
        )

    console.print(table)


def _build_summary(results: list) -> dict:
    priority_dial = [r for r in results if r.get("routing") == "Priority Dial"]
    email_sequence = [r for r in results if r.get("routing") == "Email Sequence"]
    filter_out = [r for r in results if r.get("routing") == "Filter Out"]
    scored = [r for r in results if r.get("icp_score", 0) > 0]

    avg_score = round(sum(r.get("icp_score", 0) for r in scored) / len(scored), 1) if scored else 0

    return {
        "priority_dial_count": len(priority_dial),
        "email_sequence_count": len(email_sequence),
        "filter_out_count": len(filter_out),
        "average_icp_score": avg_score,
        "routing_breakdown": {
            "Priority Dial (>=80)": len(priority_dial),
            "Email Sequence (60-79)": len(email_sequence),
            "Filter Out (<60)": len(filter_out)
        }
    }