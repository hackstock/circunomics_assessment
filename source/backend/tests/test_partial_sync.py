from tests.fakes import FakeProvider, make_commit


def test_partial_import_keeps_commits_already_fetched(client, provider: FakeProvider, db):
    provider.pages = [
        [make_commit("page1")],
        [make_commit("page2")],
    ]
    provider.error_on_page = 1

    response = client.post("/api/repositories", json={"full_name": "octo/hello"})
    body = response.json()

    assert response.status_code == 200
    assert body["imported"] == 1
    assert body["repository"]["commit_count"] == 1
    assert body["repository"]["last_sync_status"] == "partial"
    assert body["repository"]["last_sync_succeeded_at"] is None
    assert "rate limited" in (body["message"] or "")

    from app.models import Commit

    assert db.query(Commit).count() == 1
    assert db.query(Commit).one().sha == "page1"
