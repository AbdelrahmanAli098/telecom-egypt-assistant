import json
import re
import time
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

INPUT_FILE = "data/raw/filtered_urls.json"
OUTPUT_FILE = "data/raw/scraped_pages.json"

# Cleaning title
def clean_soup(soup):
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    return soup

def extract_title(soup):
    selectors = [".we-content-section-title", "h1", "title"]
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                return text
    return ""

def find_best_article(soup, page_title):
    articles = soup.select(".journal-content-article")

    def is_footer_block(article):
            text = article.get_text(" ", strip=True)
            footer_markers = [
                "NTRA", "Copyright ©", "All Rights Reserved",
                "الجهاز القومى لتنظيم الاتصالات",
                "جميع حقوق النشر محفوظة",
            ]
            return any(marker in text for marker in footer_markers)

    candidates = [a for a in articles if not is_footer_block(a)]

    matching = []
    for a in candidates:
        title_el = a.select_one(".we-content-section-title")
        if not title_el:
            continue
        if title_el.get_text(" ", strip=True).strip().lower() == page_title.strip().lower():
            matching.append(a)

    if matching:
        return max(matching, key=lambda a: len(a.get_text(" ", strip=True)))

    if candidates:
        return max(candidates, key=lambda a: len(a.get_text(" ", strip=True)))

    return soup.select_one("main") or soup.body


def has_faq(soup):
    return bool(soup.select(".expandable_question"))

def has_legal(soup):
    return bool(soup.select(".contractual_terms"))

def has_table(soup):
    return bool(soup.select(".journal-content-article table"))

def strip_subsections(soup):
    soup_copy = BeautifulSoup(str(soup), "html.parser")
    for selector in [".expandable_question", ".contractual_terms"]:
        for el in soup_copy.select(selector):
            el.decompose()
    return soup_copy


# Generic / plain content extractor
def extract_content(soup, page_title):
    container = find_best_article(soup, page_title)
    if container is None:
        return ""

    lines = []
    seen = set()

    # h2 excluded on purpose — that's the page title, captured separately by extract_title()
    for element in container.find_all(["p", "li", "h3", "h4", "td", "th"]):
        text = element.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) < 2 or text in seen:
            continue

        seen.add(text)
        lines.append(text)

    return "\n".join(lines)


# FAQ accordion extractor
def extract_faq_accordion(soup, url, language, category, page_title):
    records = []

    for block in soup.select(".expandable_question"):
        question_el = block.select_one(".question_title")
        button = block.select_one("button[aria-controls]")
        if not question_el or not button:
            continue

        collapse_id = button["aria-controls"]
        answer_el = soup.select_one(f"#{collapse_id} .my-1 p") or soup.select_one(f"#{collapse_id} p")
        if not answer_el:
            continue

        records.append({
            "url": url,
            "language": language,
            "category": category,
            "title": page_title,
            "question": question_el.get_text(" ", strip=True),
            "content": answer_el.get_text(" ", strip=True),
            "content_type": "faq",
            "scraped_at": str(date.today()),
        })
    return records


# Legal / contractual terms extractor (recursive nested clauses)
def extract_nested_clauses(li_element, prefix, section=None):
    records = []

    own_text = " ".join(
        t.strip() for t in li_element.find_all(string=True, recursive=False) if t.strip()
    )

    strong = li_element.select_one("strong")
    header_text = strong.get_text(" ", strip=True) if strong else None

    nested_list = li_element.find(["ul", "ol"], recursive=False)

    if own_text:
        records.append({
            "text": own_text,
            "clause_number": prefix,
            "section": section or header_text,
        })

    if nested_list:
        sub_items = nested_list.find_all("li", recursive=False)
        for idx, sub_li in enumerate(sub_items, start=1):
            sub_prefix = f"{prefix}.{idx}"
            records.extend(
                extract_nested_clauses(sub_li, sub_prefix, section=header_text or section)
            )

    return records


def extract_legal_content(soup, url, language, category, page_title):
    container = soup.select_one(".contractual_terms")
    records = []

    # Definition pairs: <p><strong>Term</strong></p> followed by <p>Definition</p>
    if container:
        paragraphs = container.find_all("p", recursive=False)
        i = 0
        while i < len(paragraphs):
            strong = paragraphs[i].select_one("strong")
            if strong and i + 1 < len(paragraphs):
                term = strong.get_text(" ", strip=True)
                definition = paragraphs[i + 1].get_text(" ", strip=True)
                records.append({
                    "url": url, "language": language, "category": category, "title": page_title,
                    "content": f"{term} {definition}",
                    "content_type": "definition",
                    "scraped_at": str(date.today()),
                })
                i += 2
            else:
                i += 1

    # Top-level numbered clauses (recursively expands nested sub-clauses)
    top_level_items = soup.select(".contractual_terms > ol > li")
    for idx, li in enumerate(top_level_items, start=1):
        clause_records = extract_nested_clauses(li, prefix=str(idx))
        for r in clause_records:
            records.append({
                "url": url, "language": language, "category": category, "title": page_title,
                "content": r["text"],
                "clause_number": r["clause_number"],
                "section": r["section"],
                "content_type": "clause",
                "scraped_at": str(date.today()),
            })

    return records

# Main crawl
def run_crawl():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        pages = json.load(f)

    pages = [p for p in pages if p["include"]]
    results = []

    print(f"\nScraping {len(pages)} pages...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1600, "height": 900})

        for i, item in enumerate(pages, start=1):
            url = item["url"]
            print(f"[{i}/{len(pages)}] {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector(".journal-content-article", timeout=15000)
                page.wait_for_timeout(2000)  # Liferay loads content late
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                soup = clean_soup(soup)
                title = extract_title(soup)
                page_has_faq = has_faq(soup)
                page_has_legal = has_legal(soup)
                page_has_table = has_table(soup)
                page_records = []
                content_soup = strip_subsections(soup) if (page_has_faq or page_has_legal) else soup
                content = extract_content(content_soup, title)
                if len(content) >= 30:
                    page_records.append({
                        "url": url,
                        "language": item["language"],
                        "category": item["category"],
                        "title": title,
                        "content": content,
                        "content_type": "table" if page_has_table else "plain",
                        "scraped_at": str(date.today()),
                    })
                # FAQ accordion (independent of primary content) 
                if page_has_faq:
                    page_records.extend(
                        extract_faq_accordion(soup, url, item["language"], item["category"], title)
                    )
                #   Legal / contractual clauses (independent of primary content)
                if page_has_legal:
                    page_records.extend(
                        extract_legal_content(soup, url, item["language"], item["category"], title)
                    )

                if not page_records:
                    print("   Empty page")
                    with open("debug.html", "w", encoding="utf-8") as f:
                        f.write(html)

                results.extend(page_records)
                print(
                    f"   OK ({len(page_records)} record(s) — "
                    f"faq={page_has_faq}, legal={page_has_legal}, table={page_has_table})"
                )

            except Exception as e:
                print("   ERROR:", e)

            time.sleep(0.5)

        browser.close()

    print(f"\nCollected {len(results)} records from {len(pages)} pages")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("Saved to", OUTPUT_FILE)


if __name__ == "__main__":
    run_crawl()