from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.models import Commit, Repository
from app.providers.base import ContributorRow, NormalizedCommit


def _contributor_key_sql():
    return func.coalesce(
        func.nullif(func.lower(Commit.author_email), ""),
        func.lower(Commit.author_name),
    )


class SqlAlchemyCatalogStore:
    def __init__(self, db: Session):
        self.db = db

    def get_repository(self, repository_id: int) -> Repository | None:
        return self.db.get(Repository, repository_id)

    def get_or_create_repository(self, provider: str, owner: str, name: str) -> Repository:
        row = self.db.scalar(
            select(Repository).where(
                Repository.provider == provider,
                Repository.owner == owner,
                Repository.name == name,
            )
        )
        if row is None:
            row = Repository(provider=provider, owner=owner, name=name)
            self.db.add(row)
            self.db.flush()
        return row

    def list_repositories(self) -> list[tuple[Repository, int]]:
        count = func.count(Commit.id)
        return list(
            self.db.execute(
                select(Repository, count.label("commit_count"))
                .outerjoin(Commit, Commit.repository_id == Repository.id)
                .group_by(Repository.id)
                .order_by(Repository.owner, Repository.name)
            ).all()
        )

    def delete_repository(self, repo: Repository) -> None:
        self.db.delete(repo)

    def commit_count(self, repository_id: int) -> int:
        return (
            self.db.scalar(select(func.count(Commit.id)).where(Commit.repository_id == repository_id))
            or 0
        )

    def upsert_commits(self, repo: Repository, commits: list[NormalizedCommit]) -> tuple[int, int]:
        if not commits:
            return 0, 0
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in commits:
            if item.sha in seen:
                continue
            seen.add(item.sha)
            rows.append(
                {
                    "repository_id": repo.id,
                    "sha": item.sha,
                    "author_name": item.author_name,
                    "author_email": item.author_email,
                    "committed_at": item.committed_at,
                    "html_url": item.html_url,
                }
            )
        insert = self._insert()
        stmt = insert(Commit).on_conflict_do_nothing(index_elements=["repository_id", "sha"])
        before = self.commit_count(repo.id)
        self.db.execute(stmt, rows)
        imported = self.commit_count(repo.id) - before
        skipped = len(commits) - imported
        return imported, skipped

    def _insert(self):
        dialect = self.db.get_bind().dialect.name
        if dialect == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            return sqlite_insert
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        return pg_insert

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
    ) -> tuple[list[ContributorRow], int]:
        key = _contributor_key_sql()
        filters = [Commit.repository_id == repository_id]
        if since is not None:
            filters.append(Commit.committed_at >= since)
        if until is not None:
            filters.append(Commit.committed_at <= until)
        if q:
            pattern = f"%{q.lower()}%"
            filters.append(
                (func.lower(Commit.author_name).like(pattern))
                | (func.lower(func.coalesce(Commit.author_email, "")).like(pattern))
            )
        grouped = (
            select(
                key.label("contributor_key"),
                func.max(Commit.author_name).label("name"),
                func.max(Commit.author_email).label("email"),
                func.count(Commit.id).label("commit_count"),
            )
            .where(*filters)
            .group_by(key)
        )
        total = self.db.scalar(select(func.count()).select_from(grouped.subquery())) or 0
        sort_col = func.count(Commit.id) if sort != "name" else func.max(Commit.author_name)
        grouped = grouped.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
        offset = (page - 1) * page_size
        rows = self.db.execute(grouped.offset(offset).limit(page_size)).all()
        items = [
            ContributorRow(
                identity=row.contributor_key,
                name=row.name,
                email=row.email,
                commit_count=row.commit_count,
            )
            for row in rows
        ]
        return items, total

    def list_contributor_commits(
        self, repository_id: int, identity: str, page: int, page_size: int
    ) -> tuple[list[Commit], int]:
        key = _contributor_key_sql()
        filters = [Commit.repository_id == repository_id, key == identity]
        total = self.db.scalar(select(func.count(Commit.id)).where(*filters)) or 0
        offset = (page - 1) * page_size
        rows = list(
            self.db.scalars(
                select(Commit)
                .where(*filters)
                .order_by(Commit.committed_at.desc())
                .offset(offset)
                .limit(page_size)
            ).all()
        )
        return rows, total

    def persist(self) -> None:
        self.db.commit()
