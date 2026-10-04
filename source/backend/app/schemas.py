from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    full_name: str = Field(..., examples=["octocat/Hello-World"])


class RepositoryOut(BaseModel):
    id: int
    provider: str
    owner: str
    name: str
    full_name: str
    commit_count: int
    last_sync_attempted_at: datetime | None
    last_sync_succeeded_at: datetime | None
    last_sync_status: str | None
    last_sync_error: str | None


class SyncResult(BaseModel):
    repository: RepositoryOut
    imported: int
    skipped: int
    message: str | None = None


class ContributorOut(BaseModel):
    key: str
    name: str
    email: str | None
    commit_count: int


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class ContributorPage(BaseModel):
    items: list[ContributorOut]
    meta: PageMeta


class CommitOut(BaseModel):
    sha: str
    author_name: str
    author_email: str | None
    committed_at: datetime
    html_url: str


class CommitPage(BaseModel):
    items: list[CommitOut]
    meta: PageMeta
