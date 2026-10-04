from tests.fakes import FakeProvider, make_commit


def test_reimport_does_not_duplicate_commits(client, provider: FakeProvider, db):
    provider.pages = [
        [
            make_commit("aaa"),
            make_commit("bbb", name="Grace", email="grace@example.com"),
        ]
    ]

    first = client.post("/api/repositories", json={"full_name": "octo/hello"})
    second = client.post("/api/repositories", json={"full_name": "octo/hello"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["imported"] == 2
    assert second.json()["imported"] == 0
    assert second.json()["skipped"] == 2
    assert second.json()["repository"]["commit_count"] == 2

    from app.models import Commit, Repository

    repos = db.query(Repository).all()
    commits = db.query(Commit).all()
    assert len(repos) == 1
    assert len(commits) == 2
    assert {c.sha for c in commits} == {"aaa", "bbb"}


def test_invalid_full_name_is_rejected(client):
    response = client.post("/api/repositories", json={"full_name": "not-a-repo"})
    assert response.status_code == 422
