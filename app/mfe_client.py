from __future__ import annotations

import httpx
from fastapi import HTTPException

from .cache import TTLCache
from .config import BASE_URL, CACHE_TTL_SECONDS, REQUEST_TIMEOUT, USER_AGENT

_cache = TTLCache(CACHE_TTL_SECONDS)


class MfeClient:
    """Thin async wrapper around the mfe.gov.ro WordPress REST API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(
        self, path: str, params: dict[str, str | int] | None = None
    ) -> tuple[list | dict, dict[str, str]]:
        params = params or {}
        cache_key = f"{path}?{sorted(params.items())}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"mfe.gov.ro upstream error: {exc}"
            ) from exc

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Resource not found on mfe.gov.ro")
        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"mfe.gov.ro returned unexpected status {response.status_code}",
            )

        data = response.json()
        headers = {
            "x_wp_total": response.headers.get("X-WP-Total", "0"),
            "x_wp_totalpages": response.headers.get("X-WP-TotalPages", "0"),
        }
        result = (data, headers)
        _cache.set(cache_key, result)
        return result


mfe_client = MfeClient()
