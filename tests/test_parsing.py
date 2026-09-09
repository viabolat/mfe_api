from app.parsing import extract_updates, plain_excerpt

SAMPLE_HTML = """
<p><strong>21 august 2026:</strong>
<a href="https://mfe.gov.ro/wp-content/uploads/2026/08/answers.zip">Centralizator</a></p>
<hr />
<p><strong>23 iunie 2026: </strong>
<a href="https://mfe.gov.ro/wp-content/uploads/2026/06/order.pdf">Ordinul MIPE nr. 965</a>
pentru aprobarea ghidului.</p>
"""


def test_extract_updates_splits_on_hr_and_parses_dates() -> None:
    updates = extract_updates(SAMPLE_HTML)

    assert len(updates) == 2
    assert updates[0].date == "2026-08-21"
    assert updates[0].attachments[0].url.endswith("answers.zip")
    assert updates[0].attachments[0].filetype == "zip"

    assert updates[1].date == "2026-06-23"
    assert updates[1].attachments[0].filetype == "pdf"


def test_extract_updates_empty_input() -> None:
    assert extract_updates("") == []
    assert extract_updates(None) == []  # type: ignore[arg-type]


def test_plain_excerpt_strips_tags_and_truncates() -> None:
    html = "<p>" + ("word " * 100) + "</p>"
    excerpt = plain_excerpt(html, max_length=20)
    assert "<p>" not in excerpt
    assert len(excerpt) <= 21  # +1 for ellipsis char
    assert excerpt.endswith("…")


def test_plain_excerpt_short_text_untouched() -> None:
    assert plain_excerpt("<p>Hello world</p>", max_length=50) == "Hello world"
