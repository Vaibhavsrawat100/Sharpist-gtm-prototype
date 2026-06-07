import requests
import time
from rich.console import Console

console = Console()

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKIPEDIA_SEARCH_API = "https://en.wikipedia.org/w/api.php"


def get_company_context(company_name: str) -> dict:
    console.print(f"  [cyan]-> Wikipedia:[/cyan] fetching context for '{company_name}'...")
    result = _direct_lookup(company_name)
    if not result["found"]:
        result = _search_and_fetch(company_name)
    if result["found"]:
        console.print(f"  [green]OK Wikipedia:[/green] found '{result['title']}'")
    else:
        console.print(f"  [yellow]! Wikipedia:[/yellow] no article found for '{company_name}'")
    time.sleep(0.3)
    return result


def _direct_lookup(company_name: str) -> dict:
    page_title = company_name.replace(" ", "_")
    try:
        response = requests.get(
            WIKIPEDIA_API + page_title,
            headers={"User-Agent": "SharpistGTMPrototype/1.0"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("type") == "disambiguation":
                return _not_found()
            return {
                "found": True,
                "title": data.get("title", company_name),
                "summary": data.get("extract", "No summary available."),
                "description": data.get("description", ""),
                "wikipedia_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "source": "wikipedia"
            }
        return _not_found()
    except Exception:
        return _not_found()


def _search_and_fetch(company_name: str) -> dict:
    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": company_name + " company",
            "srlimit": 1,
            "format": "json",
            "origin": "*"
        }
        search_response = requests.get(
            WIKIPEDIA_SEARCH_API,
            params=search_params,
            headers={"User-Agent": "SharpistGTMPrototype/1.0"},
            timeout=10
        )
        if search_response.status_code != 200:
            return _not_found()
        search_data = search_response.json()
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            return _not_found()
        top_title = search_results[0]["title"]
        time.sleep(0.2)
        return _direct_lookup(top_title)
    except Exception:
        return _not_found()


def _not_found() -> dict:
    return {
        "found": False,
        "title": "",
        "summary": "No Wikipedia article found for this company.",
        "description": "",
        "wikipedia_url": "",
        "source": "wikipedia_fallback"
    }