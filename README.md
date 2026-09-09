# MFE Funding Programs API

Unofficial, read-only REST API wrapping the public WordPress data behind
[mfe.gov.ro](https://mfe.gov.ro/) (Romania's Ministry of Investments and
European Projects) into clean, structured JSON endpoints for the
2021-2027 EU funding programs and their calls/guides (*ghiduri de
finanțare*).

mfe.gov.ro already exposes a full WordPress REST API at
`/wp-json/wp/v2/`, but the funding-guide content is unstructured HTML
(dated changelog paragraphs with embedded document links, no clean
"deadline"/"status" fields). This service fetches that data, extracts a
structured update timeline (dates + attached PDFs/ZIPs/DOCX) from each
guide's HTML, resolves taxonomy term IDs to names, and serves it as a
documented, cacheable, rate-limited API.

## Programs covered

`pocidif`, `peos`, `pids`, `poats`, `ptj`, `pdds`, `ghiduri-ms` — see
`GET /programs` for full names and live guide counts.

## Endpoints

- `GET /programs` — all programs, with live guide counts (`?with_counts=false` to skip)
- `GET /programs/{program}` — one program's detail
- `GET /calls` — list funding-call guides
  - `?program=pocidif` — filter to one program (omit to search across all)
  - `?q=digitalizare` — free-text search
  - `?page=1&per_page=20` (max 50)
  - `?order=date_desc|date_asc`
  - Note: without `program`, pagination applies to the merged pool of the
    top `per_page` results from *each* program — exact for typical page
    sizes, approximate for deep paging across the full historical archive.
- `GET /calls/{program}/{id}` — full detail: parsed update timeline
  (`raw_date`, ISO `date`, text, attachments) and resolved taxonomy terms
- `GET /taxonomies/{taxonomy}` — list terms for `ghid`, `regiune`,
  `prioritate`, `obiectiv`, or a program-specific `tip_ghid_*` taxonomy
- `GET /health`
- `GET /docs` — interactive OpenAPI docs (Swagger UI)

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open http://127.0.0.1:8000/docs.

## Tests

```bash
pip install pytest respx
pytest -q
ruff check .
```

## Design notes

- **WAF-friendly requests**: mfe.gov.ro's WAF 403s bare/non-browser User-Agents;
  the upstream client (`app/mfe_client.py`) sends a normal browser UA. No
  authentication is used or required — the data is public.
- **Caching**: a 5-minute in-process TTL cache (`app/cache.py`) avoids hammering
  the government server on repeat requests. It's per-instance (not shared
  across serverless replicas), which is an acceptable tradeoff for this
  read-only mirror.
- **Rate limiting**: a naive per-IP fixed-window limiter (60 req/min) protects
  the upstream site from being pounded through this proxy.
- **No database**: everything is fetched live and cached in memory — the
  smallest viable stack for a stateless read-through API. Add persistence
  (e.g. Supabase) only if you need history mfe.gov.ro itself doesn't retain.

## Deploying to Vercel

The project is laid out for Vercel's zero-config Python support
(`api/index.py` exports the FastAPI `app`; `vercel.json` routes all paths
to it):

```bash
npm i -g vercel   # if not already installed
vercel deploy
```
