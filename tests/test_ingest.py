"""Tests for CFPB ingestion."""

from src import ingest


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, payloads: list[dict]):
        self.payloads = payloads
        self.calls: list[dict] = []

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls.append(params.copy())
        return FakeResponse(self.payloads.pop(0))


def make_payload(start: int, count: int) -> dict:
    hits = [
        {
            "_source": {"complaint_id": str(index)},
            "sort": [1_700_000_000_000 - index, str(index)],
        }
        for index in range(start, start + count)
    ]
    return {"hits": {"hits": hits}}


def test_download_uses_sequential_cursor_pagination(monkeypatch) -> None:
    fake_session = FakeSession(
        [
            make_payload(0, 100),
            make_payload(100, 100),
            make_payload(200, 25),
        ]
    )

    monkeypatch.setattr(ingest.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(ingest.time, "sleep", lambda _: None)

    result = ingest.download_cfpb(
        limit=225,
        start_date="2025-01-01",
    )

    assert len(result) == 225
    assert result["complaint_id"].nunique() == 225
    assert len(fake_session.calls) == 3
    assert "search_after" not in fake_session.calls[0]
    assert fake_session.calls[1]["search_after"].endswith("_99")
    assert fake_session.calls[2]["search_after"].endswith("_199")