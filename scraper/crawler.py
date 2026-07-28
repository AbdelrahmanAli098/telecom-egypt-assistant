import json
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://te.eg"

START_URLS = [
    "https://te.eg/en/web/guest/personal",
    "https://te.eg/en/about-te/live-chat",
    "https://te.eg/web/te-business",
    "https://te.eg/en/about-te/live-chat",
    "https://te.eg/en/about-te/Ma3ak",
    "https://te.eg/en/about-te/faq",
    "https://te.eg/en/about-te/request-detailed-bill",
    "https://te.eg/en/about-te/140-guide",
    "https://te.eg/en/about-te/other-payment-channels",
    "https://te.eg/en/about-te/Contractual-Terms",
    "https://te.eg/ar/web/guest/personal",
    "https://te.eg/ar/about-te/live-chat",
    "https://te.eg/ar/web/te-business",
    "https://te.eg/ar/about-te/live-chat",
    "https://te.eg/ar/about-te/Ma3ak",
    "https://te.eg/ar/about-te/faq",
    "https://te.eg/ar/about-te/request-detailed-bill",
    "https://te.eg/ar/about-te/140-guide",
    "https://te.eg/ar/about-te/other-payment-channels",
    "https://te.eg/ar/about-te/Contractual-Terms",   
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )
}

visited = set()
queue = deque(START_URLS)

all_pages = []


def normalize(url: str):
    """Normalize URL and remove fragments."""
    parsed = urlparse(url)

    clean = parsed._replace(
        fragment="",
        query=""
    )

    return clean.geturl().rstrip("/")


def is_valid(url: str):

    parsed = urlparse(url)

    if parsed.netloc != "te.eg":
        return False

    if not (
        parsed.path.startswith("/en")
        or parsed.path.startswith("/ar")
    ):
        return False

    return True


while queue:

    url = normalize(queue.popleft())

    if url in visited:
        continue

    visited.add(url)

    print("Visiting:", url)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            continue

    except Exception as e:
        print(e)
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else ""
    language = "ar" if "/ar/" in url else "en"
    all_pages.append({
        "url": url,
        "title": title,
        "language": language
    })

    for a in soup.find_all("a", href=True):

        href = a["href"]

        absolute = urljoin(BASE_URL, href)

        absolute = normalize(absolute)

        if is_valid(absolute):

            if absolute not in visited:
                queue.append(absolute)

print(f"\nFound {len(all_pages)} pages")

with open("urls.json", "w", encoding="utf-8") as f:
    json.dump(
        all_pages,
        f,
        indent=4,
        ensure_ascii=False
    )

print("Saved urls.json")