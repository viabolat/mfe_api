import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.mfe_client import _cache

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cache():
    _cache._store.clear()
    yield
    _cache._store.clear()


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "MFE Funding Programs API"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_program_returns_404() -> None:
    response = client.get("/programs/not-a-real-program")
    assert response.status_code == 404


def test_unknown_taxonomy_returns_404() -> None:
    response = client.get("/taxonomies/not-a-real-taxonomy")
    assert response.status_code == 404


@respx.mock
def test_list_programs_with_counts() -> None:
    respx.get(url__regex=r"https://mfe\.gov\.ro/wp-json/wp/v2/.*").mock(
        return_value=httpx.Response(200, json=[], headers={"X-WP-Total": "42"})
    )
    response = client.get("/programs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    assert all(p["guide_count"] == 42 for p in data)


@respx.mock
def test_get_call_detail_builds_updates_and_taxonomies() -> None:
    guide_payload = {
        "id": 1,
        "date": "2026-08-21T11:18:50",
        "modified": "2026-08-21T13:11:10",
        "slug": "example-guide",
        "link": "https://mfe.gov.ro/ghiduri_pocidif/example-guide/",
        "title": {"rendered": "Example Guide"},
        "content": {
            "rendered": (
                '<p><strong>21 august 2026:</strong> '
                '<a href="https://mfe.gov.ro/wp-content/uploads/2026/08/f.pdf">Doc</a></p>'
            )
        },
        "ghid": [10],
        "regiune": [],
        "tip_ghid_pocidif": [],
    }
    term_payload = {"id": 10, "name": "FEDR", "slug": "fedr", "count": 5}

    respx.get(url__regex=r".*/ghiduri_pocidif/1$").mock(
        return_value=httpx.Response(200, json=guide_payload)
    )
    respx.get(url__regex=r".*/ghid/10$").mock(return_value=httpx.Response(200, json=term_payload))

    response = client.get("/calls/pocidif/1")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Example Guide"
    assert data["taxonomies"]["ghid"][0]["name"] == "FEDR"
    assert len(data["updates"]) == 1
    assert data["updates"][0]["date"] == "2026-08-21"
    assert data["updates"][0]["attachments"][0]["filetype"] == "pdf"


def test_rate_limit_headers_do_not_break_normal_traffic() -> None:
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200
