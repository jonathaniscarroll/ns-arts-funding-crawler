"""
funding_crawler.py
Crawls arts-funding, residency, and open-call pages relevant to a
Nova Scotia-based digital / media artist. Outputs:
  - docs/data.json   (consumed by the GitHub Pages site)
  - docs/report.md   (human-readable summary)

Run locally:  python funding_crawler.py
Scheduled:    GitHub Actions (.github/workflows/crawl.yml) — weekly + manual
"""

import re, csv, json, sys, time, datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SOURCES = [
    # ── Grants ──────────────────────────────────────────────────────────────
    {
        "name": "Arts Nova Scotia – Grants to Individuals",
        "url": "https://artsns.ca/programs/grants-individuals",
        "tags": ["grant", "provincial", "ns", "individual"],
    },
    {
        "name": "Arts Nova Scotia – All Programs",
        "url": "https://artsns.ca/programs",
        "tags": ["grant", "provincial", "ns", "overview"],
    },
    {
        "name": "Canada Council for the Arts – Deadlines",
        "url": "https://canadacouncil.ca/funding/grants/deadlines",
        "tags": ["grant", "federal", "canada", "deadlines"],
    },
    {
        "name": "Canada Council – Digital Now",
        "url": "https://canadacouncil.ca/funding/strategic-funds/digital-now",
        "tags": ["grant", "federal", "digital", "media"],
    },
    {
        "name": "NS Creative Industries Fund",
        "url": "https://cch.novascotia.ca/support4culture",
        "tags": ["grant", "provincial", "ns", "creative-industries"],
    },
    {
        "name": "Canada Media Fund – Innovation & Experimentation",
        "url": "https://cmf-fmc.ca/program/innovation-and-experimentation-program/",
        "tags": ["grant", "federal", "interactive", "XR", "games"],
    },
    {
        "name": "Halifax Regional Municipality – Arts Grants",
        "url": "https://www.halifax.ca/about-halifax/regional-community-planning/arts-culture/grants",
        "tags": ["grant", "municipal", "halifax", "ns"],
    },
    {
        "name": "Visual Arts Nova Scotia – Funding Resources",
        "url": "https://visualarts.ns.ca/resource-funding/",
        "tags": ["grant", "provincial", "ns", "visual-art"],
    },
    {
        "name": "NS Funding – Arts, Culture & Heritage",
        "url": "https://www.nsfunding.ca/category/arts-culture-and-heritage/",
        "tags": ["grant", "provincial", "ns", "overview"],
    },
    {
        "name": "GrantCompass – Digital & Media Arts Canada",
        "url": "https://grantcompass.ca/arts/media-arts-grants.html",
        "tags": ["grant", "federal", "digital", "media", "directory"],
    },
    # ── Residencies ─────────────────────────────────────────────────────────
    {
        "name": "Banff Centre – Programs",
        "url": "https://www.banffcentre.ca/programs",
        "tags": ["residency", "national", "digital-media", "XR"],
    },
    {
        "name": "Artist Communities Alliance – Open Calls",
        "url": "https://artistcommunities.org/directory/open-calls",
        "tags": ["residency", "international", "directory"],
    },
    {
        "name": "Res Artis – Opportunities",
        "url": "https://resartis.org/opportunities/",
        "tags": ["residency", "international", "directory"],
    },
    {
        "name": "Studio H Canada – Artist Residency",
        "url": "https://studiohcanadaresidency.ca/",
        "tags": ["residency", "canada", "all-media"],
    },
    {
        "name": "NSCAD – Research & Opportunities",
        "url": "https://nscad.ca/research/",
        "tags": ["residency", "academic", "MFA", "ns"],
    },
    # ── Open Calls / Gallery ────────────────────────────────────────────────
    {
        "name": "Creative West Opportunities Portal (CaFÉ)",
        "url": "https://opportunities.wearecreativewest.org/",
        "tags": ["open-call", "exhibition", "international", "digital-art"],
    },
    {
        "name": "Khyber Centre for the Arts – Halifax",
        "url": "https://khyberarts.ca/",
        "tags": ["open-call", "gallery", "halifax", "ns"],
    },
    {
        "name": "Eyelevel Gallery – Halifax",
        "url": "https://eyelevel.ca/",
        "tags": ["open-call", "gallery", "halifax", "ns"],
    },
    {
        "name": "Centre for Art Tapes – Halifax (media arts)",
        "url": "https://centreforarttapes.ca/",
        "tags": ["open-call", "gallery", "halifax", "ns", "media-art"],
    },
    {
        "name": "Anna Leonowens Gallery – NSCAD",
        "url": "https://analeonowensgallery.com/",
        "tags": ["open-call", "gallery", "halifax", "ns", "nscad"],
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NSArtsFundingCrawler/2.0; +https://jonathaniscarroll.github.io/ns-arts-funding-crawler)"}

DATE_PATTERNS = [
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]

KEYWORDS = [
    "digital", "media art", "new media", "interactive", "augmented reality",
    "AR", "VR", "XR", "immersive", "game", "technology", "installation",
    "spatial", "geolocation", "extended reality", "3D", "web-based",
    "electronic", "sound art", "performance", "video art",
]

OPPORTUNITY_TYPE_KEYWORDS = {
    "grant":     ["grant", "funding", "fund", "award", "bursary", "subsidy"],
    "residency": ["residency", "residencies", "artist-in-residence", "AIR"],
    "open-call": ["open call", "call for entry", "call for entries", "submission",
                  "juried", "exhibition", "call for proposals", "call for applications"],
}


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[warn] {url}: {e}", file=sys.stderr)
        return ""


def extract_deadlines(text):
    found = set()
    for pat in DATE_PATTERNS:
        found.update(re.findall(pat, text, re.IGNORECASE))
    current_year = datetime.date.today().year
    filtered = [d for d in found if str(current_year) in d or str(current_year + 1) in d]
    return sorted(filtered) if filtered else sorted(found)[:5]


def score_relevance(text):
    t = text.lower()
    return sum(1 for kw in KEYWORDS if kw.lower() in t)


def classify(text, tags):
    tag_str = " ".join(tags).lower()
    for label in ("grant", "residency", "open-call"):
        if label in tag_str:
            return label
    t = text.lower()
    scores = {
        label: sum(t.count(kw.lower()) for kw in kws)
        for label, kws in OPPORTUNITY_TYPE_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def crawl():
    rows = []
    for src in SOURCES:
        html = fetch(src["url"])
        if not html:
            rows.append({
                "name": src["name"], "url": src["url"],
                "tags": src["tags"], "type": classify("", src["tags"]),
                "deadlines": [], "relevance": 0,
                "snippet": "Could not fetch page.",
                "checked_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            })
            time.sleep(0.5)
            continue

        soup = BeautifulSoup(html, "html.parser")
        for el in soup.select("nav, footer, script, style"):
            el.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))

        rows.append({
            "name": src["name"],
            "url": src["url"],
            "tags": src["tags"],
            "type": classify(text, src["tags"]),
            "deadlines": extract_deadlines(text),
            "relevance": score_relevance(text),
            "snippet": text[:350].strip(),
            "checked_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        })
        time.sleep(1)
    return rows


def save_json(rows, path="docs/data.json"):
    Path(path).parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "opportunities": rows
        }, f, indent=2, ensure_ascii=False)


def save_markdown(rows, path="docs/report.md"):
    Path(path).parent.mkdir(exist_ok=True)
    sections = {"grant": "Grants", "residency": "Residencies", "open-call": "Open Calls & Gallery Submissions", "other": "Other"}
    lines = [f"# NS Arts Funding – Opportunities Report\n_Generated: {datetime.datetime.utcnow().strftime('%B %d, %Y')}_\n"]
    for key, title in sections.items():
        group = sorted([r for r in rows if r["type"] == key], key=lambda r: -r["relevance"])
        if not group:
            continue
        lines.append(f"\n## {title}\n")
        for r in group:
            dl = ", ".join(r["deadlines"]) if r["deadlines"] else "check page"
            lines.append(f"### [{r['name']}]({r['url']})")
            lines.append(f"- **Tags:** {', '.join(r['tags'])}")
            lines.append(f"- **Deadlines found:** {dl}")
            lines.append(f"- **Relevance score:** {r['relevance']}")
            lines.append(f"- {r['snippet']}…\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    print("Crawling sources…")
    results = crawl()
    save_json(results)
    save_markdown(results)
    print(f"Done. {len(results)} sources checked.")
    print("Outputs: docs/data.json, docs/report.md")
