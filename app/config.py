from __future__ import annotations

BASE_URL = "https://mfe.gov.ro/wp-json/wp/v2"

# mfe.gov.ro sits behind a WAF that 403s requests without a browser-like
# User-Agent (bare curl / default httpx UA get rejected). The WordPress
# REST API itself is public and unauthenticated.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 mfe-api/1.0"
)

REQUEST_TIMEOUT = 15.0
CACHE_TTL_SECONDS = 300

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 50

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
