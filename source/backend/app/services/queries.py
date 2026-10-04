from datetime import datetime

from app.identity import decode_contributor_key, encode_contributor_key
from app.providers.base import CatalogNotFound, CatalogStore
from app.schemas import CommitOut, CommitPage, ContributorOut, ContributorPage, PageMeta, RepositoryOut
from app.services.import_service import to_repository_out

ALLOWED_SORTS = {"commits", "name"}


class QueryService:
    def __init__(self, store: CatalogStore):
        self.store = store

    def list_repositories(self) -> list[RepositoryOut]:
        return [
            to_repository_out(self.store, repo, count)
            for repo, count in self.store.list_repositories()
        ]

    def get_repository(self, repository_id: int) -> RepositoryOut:
        return to_repository_out(self.store, self._require(repository_id))

    def list_contributors(
        self,
        repository_id: int,
        q: str | None,
        sort: str,
        order: str,
        since: datetime | None,
        until: datetime | None,
        page: int,
        page_size: int,
    ) -> ContributorPage:
        self._require(repository_id)
        if sort not in ALLOWED_SORTS:
            raise ValueError("sort must be 'commits' or 'name'")
        if order not in {"asc", "desc"}:
            raise ValueError("order must be 'asc' or 'desc'")
        rows, total = self.store.list_contributors(
            repository_id, q, sort, order, since, until, page, page_size
        )
        items = [
            ContributorOut(
                key=encode_contributor_key(row.identity),
                name=row.name,
                email=row.email,
                commit_count=row.commit_count,
            )
            for row in rows
        ]
        return ContributorPage(items=items, meta=PageMeta(page=page, page_size=page_size, total=total))

    def list_commits(
        self, repository_id: int, contributor_key: str, page: int, page_size: int
    ) -> CommitPage:
        self._require(repository_id)
        identity = decode_contributor_key(contributor_key)
        rows, total = self.store.list_contributor_commits(
            repository_id, identity, page, page_size
        )
        items = [
            CommitOut(
                sha=row.sha,
                author_name=row.author_name,
                author_email=row.author_email,
                committed_at=row.committed_at,
                html_url=row.html_url,
            )
            for row in rows
        ]
        return CommitPage(items=items, meta=PageMeta(page=page, page_size=page_size, total=total))

    def _require(self, repository_id: int):
        repo = self.store.get_repository(repository_id)
        if repo is None:
            raise CatalogNotFound()
        return repo
