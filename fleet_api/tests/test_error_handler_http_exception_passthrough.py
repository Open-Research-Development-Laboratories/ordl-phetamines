from __future__ import annotations

from fleet_api.fleet_api import create_app


def test_unknown_route_returns_404_not_500(monkeypatch) -> None:
    monkeypatch.setenv("FLEET_CONNECTIVITY_MONITOR_ENABLED", "false")
    app = create_app()
    client = app.test_client()

    response = client.get("/v1/route-that-does-not-exist")
    assert response.status_code == 404
