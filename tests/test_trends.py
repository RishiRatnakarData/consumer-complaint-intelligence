"""Tests for official CFPB monthly trends."""

from src import trends


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "aggregations": {
                "dateRangeArea": {
                    "dateRangeArea": {
                        "buckets": [
                            {
                                "key_as_string": "2025-01-01T00:00:00.000Z",
                                "doc_count": 100,
                            },
                            {
                                "key_as_string": "2025-02-01T00:00:00.000Z",
                                "doc_count": 125,
                            },
                        ]
                    }
                }
            }
        }


class FakeSession:
    def __init__(self) -> None:
        self.params: dict | None = None

    def get(
        self,
        url: str,
        params: dict,
        timeout: int,
    ) -> FakeResponse:
        self.params = params
        return FakeResponse()


def test_download_monthly_counts(monkeypatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(
        trends.requests,
        "Session",
        lambda: fake_session,
    )

    result = trends.download_monthly_counts(
        "2025-01-01",
        "2025-12-31",
    )

    assert len(result) == 2
    assert result["official_complaint_count"].sum() == 225
    assert result["received_month"].is_monotonic_increasing
    assert fake_session.params is not None
    assert fake_session.params["trend_interval"] == "month"