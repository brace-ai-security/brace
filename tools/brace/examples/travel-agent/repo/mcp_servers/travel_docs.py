"""travel-docs MCP server, run by the platform team inside the company network."""
import httpx

ADVISORY_URL = "https://advisories.gov.example/api"


def lookup_visa_rules(country):
    return httpx.get(f"{ADVISORY_URL}/visa/{country}").json()


def get_advisories(country):
    # Advisory text is written by an outside site and is returned to the agent unchanged.
    return httpx.get(f"{ADVISORY_URL}/advisories/{country}").text
