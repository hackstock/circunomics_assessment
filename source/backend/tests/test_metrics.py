from tests.fakes import FakeProvider, make_commit


def test_metrics_endpoint_lists_catalog_series(client, provider: FakeProvider):
    provider.pages = [[make_commit("aaa")]]
    imported = client.post("/api/repositories", json={"full_name": "octo/hello"})
    assert imported.status_code == 200

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "catalog_sync_total" in body
    assert "catalog_sync_duration_seconds" in body
    assert 'catalog_sync_total{status="success"}' in body
