import json

INPUT_FILE = "data\\raw\\urls.json"
OUTPUT_FILE = "data\\raw\\filtered_urls.json"


def normalize_url(url: str) -> str:
    return (
        url.replace("/web/guest", "")
        .rstrip("/")
        .lower()
    )


# Customer-support pages we WANT
KEEP = [
    # Main
    "personal",
    "business",
    "support",
    "help",
    "faq",
    "live-chat",
    "contact",
    "branch",
    "branches",

    # Internet
    "internet",
    "home",
    "dsl",
    "fiber",
    "router",
    "wifi",
    "wi-fi",

    # Mobile
    "mobile",
    "voice",
    "landline",
    "fixed",
    "esim",
    "volte",
    "roaming",
    "international",

    # Billing
    "bill",
    "billing",
    "payment",
    "pay",
    "balance",
    "recharge",
    "topup",

    # Services
    "services",
    "service",
    "140-guide",
    "directory",
    "ma3ak",
    "voicemail",
    "caller-id",
    "call-tone",
    "conference-call",
    "follow-me",
    "call-filter",
    "call-waiting",
    "do-not-disturb",
    "favorite-number",
    "contractual-terms",
    "missed-call-keeper",
    "bundle-query",
    "notification-on-reachability",
    "sms-alert",
    "data-transfer",
    "extend-your-line",
    "e-sim",
    "salefny-extra",
    "call-me",
    "auto-call-collect",
    "waiting",
    "hotline",
    "don-t-disturb",
    "abbreviated-numbers",
    "baqaty",
    "receiving-only-calls"

    # Apps
    "my-we",
    "mywe",
    "we-pay",
    "apple-pay",

    # Devices
    "router",
    "modem",

    # Misc
    "complaint",
    "ticket",
]


# Corporate pages we DON'T want
SKIP = [
    "board",
    "director",
    "management",
    "chairman",
    "history",
    "museum",
    "award",
    "press",
    "media",
    "news",
    "career",
    "jobs",
    "vacancy",
    "investor",
    "csr",
    "governance",
    "strategy",
    "financial",
    "finance",
    "report",
    "annual",
    "shareholder",
    "procurement",
    "supplier",
    "tender",
    "sustainability",
    "climate",
]


CATEGORY_RULES = {
    "support": [
        "support",
        "help",
        "faq",
        "contact",
        "live-chat",
        "complaint",
    ],
    "internet": [
        "internet",
        "dsl",
        "fiber",
        "router",
        "wifi",
    ],
    "mobile": [
        "mobile",
        "voice",
        "esim",
        "volte",
        "roaming",
    ],
    "billing": [
        "bill",
        "billing",
        "payment",
        "balance",
        "pay",
        "recharge",
        "topup",
    ],
    "business": [
        "business",
    ],
    "services": [
        "services",
        "service",
        "140-guide",
        "directory",
        "ma3ak",
        "voicemail",
        "call-tone",
        "caller-id",
        "conference-call",
        "follow-me",
        "call-filter",
    ],
    "devices": [
        "router",
        "modem",
    ],
}


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    pages = json.load(f)

unique = {}

for page in pages:

    normalized = normalize_url(page["url"])

    page["url"] = normalized

    # keep first occurrence
    if normalized not in unique:
        unique[normalized] = page

pages = list(unique.values())

filtered = []

for page in pages:

    url = page["url"]

    include = False
    category = "other"

    score = 0

    for word in KEEP:
        if word in url:
            score += 1

    for word in SKIP:
        if word in url:
            score -= 5

    include = score > 0

    if include:

        category = "general"

        for cat, words in CATEGORY_RULES.items():

            if any(word in url for word in words):
                category = cat
                break

    else:

        if any(word in url for word in SKIP):
            category = "corporate"

    page["include"] = include
    page["category"] = category

    filtered.append(page)


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        filtered,
        f,
        indent=4,
        ensure_ascii=False,
    )

included = sum(p["include"] for p in filtered)
excluded = len(filtered) - included

print("=" * 50)
print(f"Total unique pages : {len(filtered)}")
print(f"Included           : {included}")
print(f"Excluded           : {excluded}")
print("=" * 50)