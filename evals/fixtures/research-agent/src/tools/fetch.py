import httpx
from bs4 import BeautifulSoup


def fetch_page(url: str) -> str:
    resp = httpx.get(url, follow_redirects=True, timeout=20, headers={"User-Agent": "NorthwindResearch/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)
