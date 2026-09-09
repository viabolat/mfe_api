from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

_MONTHS = {
    "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iunie": 6,
    "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
}
_DATE_RE = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})", re.IGNORECASE
)
_DOC_EXTENSIONS = (".pdf", ".zip", ".docx", ".doc", ".xlsx", ".xls", ".pptx")
_HR_RE = re.compile(r"<hr\s*/?>", re.IGNORECASE)


@dataclass
class Attachment:
    text: str
    url: str
    filetype: str | None


@dataclass
class UpdateBlock:
    raw_date: str | None
    date: str | None  # ISO yyyy-mm-dd, best-effort
    text: str
    attachments: list[Attachment] = field(default_factory=list)


def _parse_romanian_date(text: str) -> tuple[str | None, str | None]:
    match = _DATE_RE.search(text)
    if not match:
        return None, None
    day, month_name, year = match.groups()
    month = _MONTHS[month_name.lower()]
    try:
        iso = f"{int(year):04d}-{month:02d}-{int(day):02d}"
    except ValueError:
        return match.group(0), None
    return match.group(0), iso


def _extract_attachments(soup: BeautifulSoup) -> list[Attachment]:
    attachments: list[Attachment] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        lower = href.lower()
        if "/wp-content/uploads/" not in lower and not lower.endswith(_DOC_EXTENSIONS):
            continue
        filetype = next(
            (ext.lstrip(".") for ext in _DOC_EXTENSIONS if lower.endswith(ext)), None
        )
        attachments.append(
            Attachment(text=anchor.get_text(strip=True) or href, url=href, filetype=filetype)
        )
    return attachments


def extract_updates(html: str) -> list[UpdateBlock]:
    """MIPE guide pages are a changelog: dated paragraphs separated by <hr>,
    each usually starting with a bolded Romanian date and linking one or
    more documents. Split on that structure to get a clean timeline.
    """
    if not html:
        return []
    blocks = _HR_RE.split(html)
    updates: list[UpdateBlock] = []
    for block_html in blocks:
        block_html = block_html.strip()
        if not block_html:
            continue
        soup = BeautifulSoup(block_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        if not text:
            continue
        raw_date, iso_date = _parse_romanian_date(text[:200])
        updates.append(
            UpdateBlock(
                raw_date=raw_date,
                date=iso_date,
                text=text,
                attachments=_extract_attachments(soup),
            )
        )
    return updates


def plain_excerpt(html: str, max_length: int = 300) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "…"
