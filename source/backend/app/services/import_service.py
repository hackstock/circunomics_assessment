from datetime import datetime, timezone
import time

import structlog

from app.config import settings
from app.identity import parse_full_name
from app.metrics import observe_sync
from app.models import Repository
from app.providers.base import CatalogNotFound, CatalogStore, ProviderError, RateLimited, RepositoryNotFound, VcsProvider
from app.schemas import RepositoryOut, SyncResult

log = structlog.get_logger("app.import")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def to_repository_out(
    store: CatalogStore, repo: Repository, commit_count: int | None = None
) -> RepositoryOut:
    return RepositoryOut(
        id=repo.id,
        provider=repo.provider,
        owner=repo.owner,
        name=repo.name,
        full_name=f"{repo.owner}/{repo.name}",
        commit_count=store.commit_count(repo.id) if commit_count is None else commit_count,
        last_sync_attempted_at=repo.last_sync_attempted_at,
        last_sync_succeeded_at=repo.last_sync_succeeded_at,
        last_sync_status=repo.last_sync_status,
        last_sync_error=repo.last_sync_error,
    )


class ImportService:
    def __init__(self, store: CatalogStore, provider: VcsProvider, commit_limit: int | None = None):
        self.store = store
        self.provider = provider
        self.commit_limit = commit_limit if commit_limit is not None else settings.commit_import_limit

    def add_and_sync(self, full_name: str) -> SyncResult:
        owner, name = parse_full_name(full_name)
        repo = self.store.get_or_create_repository(self.provider.name, owner, name)
        self.store.persist()
        return self.sync(repo)

    def sync_by_id(self, repository_id: int) -> SyncResult:
        repo = self.store.get_repository(repository_id)
        if repo is None:
            raise CatalogNotFound()
        return self.sync(repo)

    def sync(self, repo: Repository) -> SyncResult:
        started = time.perf_counter()
        repo.last_sync_attempted_at = _now()
        repo.last_sync_error = None
        self.store.persist()
        log.info("sync.started", owner=repo.owner, name=repo.name, limit=self.commit_limit)

        imported = 0
        skipped = 0
        try:
            for page in self.provider.iter_recent_commits(repo.owner, repo.name, self.commit_limit):
                page_imported, page_skipped = self.store.upsert_commits(repo, page)
                imported += page_imported
                skipped += page_skipped
                self.store.persist()
        except RateLimited as exc:
            return self._finish_partial(repo, imported, skipped, exc.message, started)
        except RepositoryNotFound as exc:
            deleted = self.store.commit_count(repo.id) == 0
            if deleted:
                self.store.delete_repository(repo)
                self.store.persist()
            else:
                repo.last_sync_status = "failed"
                repo.last_sync_error = exc.message
                self.store.persist()
            self._log_finished(
                repo,
                imported,
                skipped,
                status="failed",
                started=started,
                error=exc.message,
                deleted=deleted,
            )
            raise
        except ProviderError as exc:
            return self._finish_partial(repo, imported, skipped, exc.message, started)

        repo.last_sync_status = "success"
        repo.last_sync_succeeded_at = _now()
        repo.last_sync_error = None
        self.store.persist()
        self._log_finished(repo, imported, skipped, status="success", started=started)
        return SyncResult(
            repository=to_repository_out(self.store, repo),
            imported=imported,
            skipped=skipped,
        )

    def _finish_partial(
        self,
        repo: Repository,
        imported: int,
        skipped: int,
        message: str,
        started: float,
    ) -> SyncResult:
        repo.last_sync_status = "partial" if imported or skipped else "failed"
        repo.last_sync_error = message
        self.store.persist()
        self._log_finished(
            repo, imported, skipped, status=repo.last_sync_status, started=started, error=message
        )
        return SyncResult(
            repository=to_repository_out(self.store, repo),
            imported=imported,
            skipped=skipped,
            message=message,
        )

    def _log_finished(
        self,
        repo: Repository,
        imported: int,
        skipped: int,
        status: str,
        started: float,
        error: str | None = None,
        deleted: bool = False,
    ) -> None:
        duration = time.perf_counter() - started
        observe_sync(status, duration)
        log.info(
            "sync.finished",
            owner=repo.owner,
            name=repo.name,
            imported=imported,
            skipped=skipped,
            status=status,
            duration_ms=int(duration * 1000),
            error=error,
            deleted=deleted,
        )
