# NS Arts Funding Crawler

A web crawler that finds **grants**, **residencies**, and **open calls / gallery submissions** for digital artists in Nova Scotia.

## Live site

👉 **[jonathaniscarroll.github.io/ns-arts-funding-crawler](https://jonathaniscarroll.github.io/ns-arts-funding-crawler)**

The site reads from `docs/data.json`, which is regenerated weekly by GitHub Actions.

## Sources tracked

- Arts Nova Scotia (grants to individuals, all programs)
- Canada Council for the Arts (deadlines, Digital Now)
- NS Creative Industries Fund / Support4Culture
- Canada Media Fund – Innovation & Experimentation
- Halifax Regional Municipality arts grants
- Visual Arts Nova Scotia, NS Funding directory
- Banff Centre programs
- Artist Communities Alliance open calls directory
- Res Artis residency listings
- Studio H Canada residency
- Creative West / CaFÉ open calls portal
- Khyber Centre for the Arts, Eyelevel Gallery, Centre for Art Tapes, Anna Leonowens Gallery (Halifax)

## Running locally

```bash
pip install requests beautifulsoup4
python funding_crawler.py
# → writes docs/data.json and docs/report.md
```

Open `index.html` in a browser (or `python -m http.server`) to view the site locally.

## Scheduling

GitHub Actions runs the crawler every Monday at 08:00 UTC and commits updated `docs/data.json` back to `main`. The GitHub Pages site reflects the new data automatically.

Trigger a manual run from **Actions → Crawl Arts Funding Sources → Run workflow**.

## Extending

Add entries to the `SOURCES` list in `funding_crawler.py`. Each entry needs a `name`, `url`, and `tags` list. Tag with `"grant"`, `"residency"`, or `"open-call"` to ensure correct classification.
