"""Tests for CFPB API pagination."""

from src import ingest


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payloads: list[dict]):
        self.payloads = payloads
        self.calls: list[dict] = []

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls.append(params.copy())
        return FakeResponse(self.payloads.pop(0))


def make_page(page_index: int) -> dict:
    start = page_index * 25
    hits = [
        {"_source": {"complaint_id": str(complaint_id)}}
        for complaint_id in range(start, start + 25)
    ]
    next_page = page_index + 2

    return {
        "hits": {"hits": hits},
        "_meta": {
            "break_points": {
                str(next_page): [1700000000000 - page_index, str(start + 24)]
            }
        },
    }


def test_download_cfpb_uses_cursor_pagination(monkeypatch) -> None:
    fake_session = FakeSession([make_page(index) for index in range(9)])

    monkeypatch.setattr(ingest.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(ingest.time, "sleep", lambda _: None)

    result = ingest.download_cfpb(limit=225, start_date="2025-01-01")

    assert len(result) == 225
    assert result["complaint_id"].nunique() == 225
    assert len(fake_session.calls) == 9

    assert "search_after" not in fake_session.calls[0]
    assert fake_session.calls[1]["page"] == 2
    assert fake_session.calls[1]["frm"] == 25
    assert fake_session.calls[-1]["page"] == 9
    assert fake_session.calls[-1]["frm"] == 200