from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import (
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)
from .mfe_client import mfe_client
from .models import (
    CallDetailOut,
    CallSummaryOut,
    PaginatedCalls,
    ProgramOut,
    TermOut,
)
from .parsing import extract_updates, plain_excerpt
from .registry import ALL_TAXONOMIES, PROGRAMS, taxonomies_for_program


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await mfe_client.aclose()


app = FastAPI(
    title="MFE Funding Programs API",
    description=(
        "Unofficial read-only API wrapping mfe.gov.ro's public WordPress data "
        "into clean, structured endpoints for Romania's 2021-2027 EU funding "
        "programs and their calls/guides (ghiduri de finanțare)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- naive fixed-window per-IP rate limit, to be a considerate upstream client ---
_request_log: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"

    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = [t for t in _request_log.get(client_ip, []) if t > window_start]

    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again shortly."},
        )

    timestamps.append(now)
    _request_log[client_ip] = timestamps
    return await call_next(request)


def _program_or_404(program: str) -> None:
    if program not in PROGRAMS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown program '{program}'. See GET /programs for valid values.",
        )


def _build_summary(item: dict, program: str) -> CallSummaryOut:
    content_html = item.get("content", {}).get("rendered", "")
    return CallSummaryOut(
        id=item["id"],
        program=program,
        title=item.get("title", {}).get("rendered", "").strip(),
        slug=item["slug"],
        link=item["link"],
        date_published=item["date"],
        date_modified=item["modified"],
        excerpt=plain_excerpt(content_html),
    )


async def _resolve_terms(taxonomy: str, term_ids: list[int]) -> list[TermOut]:
    if not term_ids:
        return []
    results = await asyncio.gather(
        *(mfe_client.get(f"/{taxonomy}/{tid}") for tid in term_ids)
    )
    return [
        TermOut(id=data["id"], name=data["name"], slug=data["slug"], count=data.get("count", 0))
        for data, _ in results
    ]


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": "MFE Funding Programs API",
        "docs": "/docs",
        "programs": "/programs",
        "calls": "/calls",
        "source": "https://mfe.gov.ro/",
    }


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/programs", response_model=list[ProgramOut], tags=["programs"])
async def list_programs(with_counts: bool = Query(default=True)) -> list[ProgramOut]:
    async def build(slug: str) -> ProgramOut:
        meta = PROGRAMS[slug]
        count = None
        if with_counts:
            _, headers = await mfe_client.get(f"/{meta.guides_cpt}", {"per_page": 1})
            count = int(headers.get("x_wp_total", 0))
        return ProgramOut(
            slug=meta.slug,
            code=meta.code,
            name=meta.name,
            period=meta.period,
            guides_cpt=meta.guides_cpt,
            guide_count=count,
        )

    return await asyncio.gather(*(build(slug) for slug in PROGRAMS))


@app.get("/programs/{program}", response_model=ProgramOut, tags=["programs"])
async def get_program(program: str) -> ProgramOut:
    _program_or_404(program)
    meta = PROGRAMS[program]
    _, headers = await mfe_client.get(f"/{meta.guides_cpt}", {"per_page": 1})
    return ProgramOut(
        slug=meta.slug,
        code=meta.code,
        name=meta.name,
        period=meta.period,
        guides_cpt=meta.guides_cpt,
        guide_count=int(headers.get("x_wp_total", 0)),
    )


@app.get("/taxonomies/{taxonomy}", response_model=list[TermOut], tags=["taxonomies"])
async def list_taxonomy_terms(
    taxonomy: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
) -> list[TermOut]:
    if taxonomy not in ALL_TAXONOMIES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown taxonomy '{taxonomy}'. Valid values: {sorted(ALL_TAXONOMIES)}",
        )
    data, _ = await mfe_client.get(f"/{taxonomy}", {"page": page, "per_page": per_page})
    return [
        TermOut(id=t["id"], name=t["name"], slug=t["slug"], count=t.get("count", 0))
        for t in data
    ]


@app.get("/calls", response_model=PaginatedCalls, tags=["calls"])
async def list_calls(
    program: str | None = Query(default=None, description="Filter to one program slug"),
    q: str | None = Query(default=None, description="Free-text search"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    order: Literal["date_desc", "date_asc"] = "date_desc",
) -> PaginatedCalls:
    wp_order = "desc" if order == "date_desc" else "asc"

    if program is not None:
        _program_or_404(program)
        meta = PROGRAMS[program]
        params: dict[str, str | int] = {
            "page": page,
            "per_page": per_page,
            "orderby": "date",
            "order": wp_order,
        }
        if q:
            params["search"] = q
        data, headers = await mfe_client.get(f"/{meta.guides_cpt}", params)
        items = [_build_summary(item, program) for item in data]
        return PaginatedCalls(
            items=items,
            total=int(headers.get("x_wp_total", len(items))),
            total_pages=int(headers.get("x_wp_totalpages", 1)),
            page=page,
            per_page=per_page,
        )

    # No program filter: fan out across every program's guide CPT and merge.
    # Pagination here applies to the merged pool of the top `per_page` items
    # per program, not a global offset -- exact for typical per_page sizes,
    # approximate for deep paging across thousands of historical guides.
    async def fetch(slug: str) -> list[CallSummaryOut]:
        meta = PROGRAMS[slug]
        params: dict[str, str | int] = {
            "page": 1,
            "per_page": per_page,
            "orderby": "date",
            "order": wp_order,
        }
        if q:
            params["search"] = q
        data, _ = await mfe_client.get(f"/{meta.guides_cpt}", params)
        return [_build_summary(item, slug) for item in data]

    results = await asyncio.gather(*(fetch(slug) for slug in PROGRAMS))
    merged = [item for sublist in results for item in sublist]
    merged.sort(key=lambda c: c.date_published, reverse=(order == "date_desc"))

    start = (page - 1) * per_page
    page_items = merged[start : start + per_page]
    return PaginatedCalls(
        items=page_items,
        total=len(merged),
        total_pages=max(1, -(-len(merged) // per_page)),
        page=page,
        per_page=per_page,
    )


@app.get("/calls/{program}/{call_id}", response_model=CallDetailOut, tags=["calls"])
async def get_call(program: str, call_id: int) -> CallDetailOut:
    _program_or_404(program)
    meta = PROGRAMS[program]
    item, _ = await mfe_client.get(f"/{meta.guides_cpt}/{call_id}")

    content_html = item.get("content", {}).get("rendered", "")
    summary = _build_summary(item, program)

    taxonomies: dict[str, list[TermOut]] = {}
    for taxonomy in taxonomies_for_program(program):
        term_ids = item.get(taxonomy) or []
        terms = await _resolve_terms(taxonomy, term_ids)
        if terms:
            taxonomies[taxonomy] = terms

    updates = [
        {
            "raw_date": u.raw_date,
            "date": u.date,
            "text": u.text,
            "attachments": [a.__dict__ for a in u.attachments],
        }
        for u in extract_updates(content_html)
    ]

    return CallDetailOut(**summary.model_dump(), taxonomies=taxonomies, updates=updates)
