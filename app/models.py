from __future__ import annotations

from pydantic import BaseModel


class ProgramOut(BaseModel):
    slug: str
    code: str
    name: str
    period: str | None
    guides_cpt: str
    guide_count: int | None = None


class AttachmentOut(BaseModel):
    text: str
    url: str
    filetype: str | None


class UpdateOut(BaseModel):
    raw_date: str | None
    date: str | None
    text: str
    attachments: list[AttachmentOut]


class TermOut(BaseModel):
    id: int
    name: str
    slug: str
    count: int


class CallSummaryOut(BaseModel):
    id: int
    program: str
    title: str
    slug: str
    link: str
    date_published: str
    date_modified: str
    excerpt: str


class CallDetailOut(CallSummaryOut):
    taxonomies: dict[str, list[TermOut]]
    updates: list[UpdateOut]


class PaginatedCalls(BaseModel):
    items: list[CallSummaryOut]
    total: int
    total_pages: int
    page: int
    per_page: int
