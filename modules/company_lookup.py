"""
company_lookup.py
-----------------
Fetches company registration data from OpenCorporates (free, no API key needed).
Gives us: company status, jurisdiction, company type, registered address.
This mirrors what Clay's enrichment layer does in the real Founder-OS pipeline.
"""

import requests
import time
from rich.console import Console

console = Console()

OPENCORPORATES_BASE = "https://api.opencorporates.com/v0.4/companies/search"

# Map our country codes to OpenCorporates jurisdiction codes
JURISDICTION_MAP = {
    "de": "de",       # Germany
    "at": "at",       # Austria
    "ch": "ch",       # Switzerland
}


def lookup_company(company_name: str, country_code: str = "de") -> dict:
    """
    Search OpenCorporates for a company by name and country.
    Returns a clean dict with the most relevant registration data.
    Falls back gracefully if nothing is found.
    """
    jurisdiction = JURISDICTION_MAP.get(country_code.lower(), "de")

    params = {
        "q": company_name,
        "jurisdiction_code": jurisdiction,
        "per_page": 1,
        "format": "json"
    }

    try:
        console.print(f"  [cyan]→ OpenCorporates:[/cyan] searching for '{company_name}' in {jurisdiction.upper()}...")

        response = requests.get(
            OPENCORPORATES_BASE,
            params=params,
            timeout=10
        )

        time.sleep(0.5)

        if response.status_code == 200:
            data = response.json()
            companies = data.get("results", {}).get("companies", [])

            if not companies:
                console.print(f"  [yellow]⚠ No results found for '{company_name}' in {jurisdiction.upper()}[/yellow]")
                return _empty_result(company_name)

            company = companies[0].get("company", {})

            result = {
                "name": company.get("name", company_name),
                "jurisdiction": company.get("jurisdiction_code", jurisdiction).upper(),
                "status": company.get("current_status", "Unknown"),
                "company_type": company.get("company_type", "Unknown"),
                "incorporation_date": company.get("incorporation_date", "Unknown"),
                "registered_address": _extract_address(company),
                "opencorporates_url": company.get("opencorporates_url", ""),
                "source": "opencorporates"
            }

            console.print(f"  [green]✓ Found:[/green] {result['name']} | {result['status']} | {result['jurisdiction']}")
            return result

        elif response.status_code == 429:
            console.print(f"  [red]✗ Rate limited by OpenCorporates. Waiting 5 seconds...[/red]")
            time.sleep(5)
            return _empty_result(company_name)

        else:
            console.print(f"  [red]✗ OpenCorporates error: HTTP {response.status_code}[/red]")
            return _empty_result(company_name)

    except requests.exceptions.Timeout:
        console.print(f"  [red]✗ OpenCorporates timed out for '{company_name}'[/red]")
        return _empty_result(company_name)

    except requests.exceptions.ConnectionError:
        console.print(f"  [red]✗ No internet connection — skipping OpenCorporates[/red]")
        return _empty_result(company_name)

    except Exception as e:
        console.print(f"  [red]✗ Unexpected error in company_lookup: {e}[/red]")
        return _empty_result(company_name)


def _extract_address(company: dict) -> str:
    address = company.get("registered_address", {})
    if not address:
        return "Unknown"
    parts = [
        address.get("street_address", ""),
        address.get("locality", ""),
        address.get("postal_code", ""),
        address.get("country", "")
    ]
    return ", ".join(part for part in parts if part)


def _empty_result(company_name: str) -> dict:
    return {
        "name": company_name,
        "jurisdiction": "Unknown",
        "status": "Unknown",
        "company_type": "Unknown",
        "incorporation_date": "Unknown",
        "registered_address": "Unknown",
        "opencorporates_url": "",
        "source": "opencorporates_fallback"
    }
