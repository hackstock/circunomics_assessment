from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Protocol

from app.models import Commit, Repository


class ProviderError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class RepositoryNotFound(ProviderError):
    pass


class RateLimited(ProviderError):
    pass


class CatalogNotFound(Exception):
    def __init__(self, message: str = "Repository not found"):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class NormalizedCommit:
    sha: str
    author_name: str
    author_email: str | None
    committed_at: datetime
    html_url: str


class ContributorRow(NamedTuple):
    identity: str
    name: str
    email: str | None
    commit_count: int


class VcsProvider:
    """GitLab/Bitbucket would implement the same methods."""

    name: str

    def iter_recent_commits(
        self, owner: str, name: str, limit: int
    ) -> Iterator[list[NormalizedCommit]]:
        raise NotImplementedError


class CatalogStore(Protocol):
    """Persistence port. SQL lives in the store, not in FastAPI routes."""

    def get_repository(self, repository_id: int) -> Repository | None: ...

    def get_or_create_repository(self, provider: str, owner: str, name: str) -> Repository: ...

    def list_repositories(self) -> list[tuple[Repository, int]]: ...

    def delete_repository(self, repo: Repository) -> None: ...

    def commit_count(self, repository_id: int) -> int: ...

    def upsert_commits(self, repo: Repository, commits: list[NormalizedCommit]) -> tuple[int, int]: ...

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
    ) -> tuple[list[ContributorRow], int]: ...

    def list_contributor_commits(
        self, repository_id: int, identity: str, page: int, page_size: int
    ) -> tuple[list[Commit], int]: ...

    def persist(self) -> None: ...
