# LinkedIn Lead Finder

Finds **"Open To Work"** AI / LLM / GenAI professionals in India with verified emails.

Uses **one** Apify actor (`apify/google-search-scraper`) to scrape Google for LinkedIn profiles, parses leads directly from search snippets, then finds and verifies emails via **Prospeo.io**.

---

## Project Structure

```
lead-finder/
├── .env                 # API tokens (never commit this)
├── requirements.txt     # Python dependencies
├── main.py              # CLI entry point
├── app.py               # Streamlit web UI
├── pipeline.py          # Shared pipeline logic
├── apify_service.py     # Google search + lead parsing
├── email_service.py     # Prospeo email finding + verification
├── models.py            # Lead dataclass
└── README.md
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | |
| Apify account | Free tier works |
| Prospeo.io account | Free tier — 50 enrich requests/day |

---

## Setup

### 1 — Clone the repo

```bash
git clone <your-repo-url>
cd lead-finder
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Add API keys to `.env`

```
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PROSPEO_API_KEY=pk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- Apify token → https://console.apify.com/account/integrations
- Prospeo key → https://app.prospeo.io/api

---

## Usage

### CLI

```bash
python main.py
```

### Streamlit UI

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Paste your API keys in the sidebar and click **Run Pipeline**. Logs stream live as the pipeline runs.

---

## How It Works

```
pipeline.py
  │
  ├─► search_google()              — Runs apify/google-search-scraper across 10 role queries
  │
  ├─► extract_linkedin_urls()      — Deduplicates /in/ profile URLs from results
  │
  ├─► build_leads_from_results()   — Parses name, headline, company, location from snippets
  │
  ├─► filter_open_to_work()        — Marks all leads as OTW (pre-qualified by search query)
  │
  ├─► find_and_verify_email()      — Calls Prospeo /enrich-person per lead
  │       ├─ Strategy 1: linkedin_url
  │       └─ Strategy 2: full_name + guessed company domain
  │
  └─► Returns up to 10 leads with verified emails
```

No enrichment actor needed — all profile data comes from Google snippets.

---

## Configuration

Search queries live in `apify_service.py` → `SEARCH_QUERIES`. Add or remove lines to target different roles:

```python
SEARCH_QUERIES = [
    'site:linkedin.com/in "Open to Work" "AI Engineer" "India"',
    'site:linkedin.com/in "Open to Work" "LLM Engineer" "India"',
    # add more here
]
```

Target lead count is set in `pipeline.py` → `TARGET_LEADS = 10`.

---

## Rate Limits

Prospeo free tier allows **50 enrich requests/day**. The pipeline stops automatically when the limit is hit and returns however many verified emails were found. The Streamlit UI shows this in the live log.

If you hit the daily limit, wait until midnight UTC (5:30 AM IST) for it to reset.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Empty Google results | Exits gracefully |
| Prospeo rate limit hit | Stops email stage, returns partial results |
| Profile not in Prospeo DB | Skipped silently |
| No company/domain derivable | Falls back to LinkedIn URL strategy |
| Actor run failure | Error logged, exits |

---

## .gitignore

```
.env
__pycache__/
*.pyc
.DS_Store
debug_fields.py
```

---

## Notes

- LinkedIn scraping is subject to LinkedIn's Terms of Service. Use responsibly and only for legitimate lead-generation purposes.
- Never commit `.env` to version control.