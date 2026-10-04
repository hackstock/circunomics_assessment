from datetime import datetime, timezone
from types import SimpleNamespace

from app.identity import encode_contributor_key
from app.models import Commit, Repository
from app.providers.base import ProviderError, RepositoryNotFound
from app.services.store import SqlAlchemyCatalogStore
from tests.fakes import FakeProvider, make_commit
from tests.test_contributors import _seed


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_repositories_empty(client):
    assert client.get("/api/repositories").json() == []


def test_list_and_get_repository_after_import(client, provider: FakeProvider):
    provider.pages = [[make_commit("aaa")]]
    created = client.post("/api/repositories", json={"full_name": "octo/hello"})
    assert created.status_code == 200
    repo_id = created.json()["repository"]["id"]

    listed = client.get("/api/repositories")
    assert listed.status_code == 200
    assert listed.json()[0]["full_name"] == "octo/hello"

    detail = client.get(f"/api/repositories/{repo_id}")
    assert detail.status_code == 200
    assert detail.json()["commit_count"] == 1

    missing = client.get("/api/repositories/999")
    assert missing.status_code == 404


def test_resync_unknown_repository(client):
    response = client.post("/api/repositories/999/sync")
    assert response.status_code == 404


def test_resync_existing_repository(client, provider: FakeProvider):
    provider.pages = [[make_commit("aaa")]]
    created = client.post("/api/repositories", json={"full_name": "octo/hello"})
    repo_id = created.json()["repository"]["id"]
    provider.pages = [[make_commit("aaa"), make_commit("bbb")]]
    synced = client.post(f"/api/repositories/{repo_id}/sync")
    assert synced.status_code == 200
    assert synced.json()["imported"] == 1
    assert synced.json()["repository"]["commit_count"] == 2


def test_contributors_unknown_repo(client):
    assert client.get("/api/repositories/999/contributors").status_code == 404


def test_contributors_invalid_sort_and_order(client, db):
    repo = _seed(db)
    bad_sort = client.get(
        f"/api/repositories/{repo.id}/contributors", params={"sort": "stars"}
    )
    assert bad_sort.status_code == 422
    bad_order = client.get(
        f"/api/repositories/{repo.id}/contributors", params={"order": "sideways"}
    )
    assert bad_order.status_code == 422


def test_contributor_commits_invalid_key(client, db):
    repo = _seed(db)
    response = client.get(f"/api/repositories/{repo.id}/contributors/_w/commits")
    assert response.status_code == 404


def test_contributor_commits_unknown_repo(client):
    key = encode_contributor_key("ada@example.com")
    assert client.get(f"/api/repositories/999/contributors/{key}/commits").status_code == 404


def test_github_missing_repo_deletes_empty_row(client, provider: FakeProvider, db):
    provider.fail_with = RepositoryNotFound("gone")
    response = client.post("/api/repositories", json={"full_name": "octo/missing"})
    assert response.status_code == 404
    assert db.query(Repository).count() == 0


def test_github_missing_repo_keeps_existing_commits(client, provider: FakeProvider, db):
    provider.pages = [[make_commit("aaa")]]
    created = client.post("/api/repositories", json={"full_name": "octo/hello"})
    repo_id = created.json()["repository"]["id"]
    provider.fail_with = RepositoryNotFound("gone")
    response = client.post(f"/api/repositories/{repo_id}/sync")
    assert response.status_code == 404
    repo = db.get(Repository, repo_id)
    assert repo is not None
    assert repo.last_sync_status == "failed"


def test_provider_error_is_partial_success(client, provider: FakeProvider):
    provider.fail_with = ProviderError("upstream down")
    response = client.post("/api/repositories", json={"full_name": "octo/hello"})
    assert response.status_code == 200
    assert response.json()["repository"]["last_sync_status"] == "failed"
    assert "upstream down" in response.json()["message"]


def test_until_filter_and_name_only_author(client, db):
    repo = _seed(db)
    until = datetime(2024, 2, 15, tzinfo=timezone.utc).isoformat()
    filtered = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"until": until},
    )
    assert filtered.status_code == 200
    assert filtered.json()["meta"]["total"] == 1


def test_store_empty_and_duplicate_sha_upsert(db):
    store = SqlAlchemyCatalogStore(db)
    repo = store.get_or_create_repository("github", "octo", "hello")
    store.persist()
    assert store.upsert_commits(repo, []) == (0, 0)
    commit = make_commit("dup")
    imported, skipped = store.upsert_commits(repo, [commit, commit])
    store.persist()
    assert imported == 1
    assert skipped == 1


def test_store_postgres_insert_dialect(db, monkeypatch):
    store = SqlAlchemyCatalogStore(db)
    monkeypatch.setattr(
        store.db,
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    insert_fn = store._insert()
    assert "postgresql" in insert_fn.__module__


def test_name_only_author_is_searchable(client, db):
    repo = Repository(provider="github", owner="octo", name="hello")
    db.add(repo)
    db.flush()
    db.add(
        Commit(
            repository_id=repo.id,
            sha="solo",
            author_name="No Mail",
            author_email=None,
            committed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            html_url="https://example.test/solo",
        )
    )
    db.commit()
    searched = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"q": "no mail"},
    )
    assert searched.status_code == 200
    assert searched.json()["meta"]["total"] == 1
    assert searched.json()["items"][0]["email"] is None
