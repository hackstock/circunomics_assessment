from datetime import datetime, timezone

from app.models import Commit, Repository
from tests.fakes import make_commit


def _seed(db):
    repo = Repository(provider="github", owner="octo", name="hello")
    db.add(repo)
    db.flush()
    rows = [
        make_commit("1", name="Ada", email="ada@example.com", when="2024-01-01T00:00:00+00:00"),
        make_commit("2", name="Ada", email="ada@example.com", when="2024-02-01T00:00:00+00:00"),
        make_commit("3", name="Grace", email="grace@example.com", when="2024-03-01T00:00:00+00:00"),
        make_commit("4", name="Ada Alt", email="ada.alt@example.com", when="2024-04-01T00:00:00+00:00"),
    ]
    for item in rows:
        db.add(
            Commit(
                repository_id=repo.id,
                sha=item.sha,
                author_name=item.author_name,
                author_email=item.author_email,
                committed_at=item.committed_at,
                html_url=item.html_url,
            )
        )
    db.commit()
    return repo


def test_contributors_search_sort_filter_and_pagination(client, db):
    repo = _seed(db)

    searched = client.get(f"/api/repositories/{repo.id}/contributors", params={"q": "grace"})
    assert searched.status_code == 200
    assert searched.json()["meta"]["total"] == 1
    assert searched.json()["items"][0]["name"] == "Grace"

    by_name = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"sort": "name", "order": "asc"},
    )
    names = [item["name"] for item in by_name.json()["items"]]
    assert names == sorted(names, key=str.lower)

    since = datetime(2024, 2, 15, tzinfo=timezone.utc).isoformat()
    filtered = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"since": since},
    )
    assert filtered.json()["meta"]["total"] == 2

    page1 = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"page": 1, "page_size": 1, "sort": "name", "order": "asc"},
    )
    page2 = client.get(
        f"/api/repositories/{repo.id}/contributors",
        params={"page": 2, "page_size": 1, "sort": "name", "order": "asc"},
    )
    assert page1.json()["meta"]["total"] == 3
    assert page1.json()["items"][0]["name"] != page2.json()["items"][0]["name"]

    key = page1.json()["items"][0]["key"]
    commits = client.get(f"/api/repositories/{repo.id}/contributors/{key}/commits")
    assert commits.status_code == 200
    assert commits.json()["meta"]["total"] >= 1
    assert "html_url" in commits.json()["items"][0]
