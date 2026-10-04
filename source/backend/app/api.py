from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.identity import InvalidContributorKey
from app.providers.base import CatalogNotFound, CatalogStore, RepositoryNotFound, VcsProvider
from app.providers.registry import get_provider
from app.schemas import CommitPage, ContributorPage, RepositoryCreate, RepositoryOut, SyncResult
from app.services.import_service import ImportService
from app.services.queries import QueryService
from app.services.store import SqlAlchemyCatalogStore

router = APIRouter()


def get_store(db: Session = Depends(get_db)) -> CatalogStore:
    return SqlAlchemyCatalogStore(db)


def get_import_service(
    store: CatalogStore = Depends(get_store),
    provider: VcsProvider = Depends(get_provider),
) -> ImportService:
    return ImportService(store, provider)


def get_query_service(store: CatalogStore = Depends(get_store)) -> QueryService:
    return QueryService(store)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(queries: QueryService = Depends(get_query_service)):
    return queries.list_repositories()


@router.post("/repositories", response_model=SyncResult)
def add_repository(
    payload: RepositoryCreate,
    service: ImportService = Depends(get_import_service),
):
    return _run_sync(lambda: service.add_and_sync(payload.full_name))


@router.post("/repositories/{repository_id}/sync", response_model=SyncResult)
def sync_repository(
    repository_id: int,
    service: ImportService = Depends(get_import_service),
):
    return _run_sync(lambda: service.sync_by_id(repository_id))


@router.get("/repositories/{repository_id}", response_model=RepositoryOut)
def get_repository(
    repository_id: int,
    queries: QueryService = Depends(get_query_service),
):
    try:
        return queries.get_repository(repository_id)
    except CatalogNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.get("/repositories/{repository_id}/contributors", response_model=ContributorPage)
def list_contributors(
    repository_id: int,
    q: str | None = None,
    sort: str = Query("commits"),
    order: str = Query("desc"),
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    queries: QueryService = Depends(get_query_service),
):
    try:
        return queries.list_contributors(
            repository_id=repository_id,
            q=q,
            sort=sort,
            order=order,
            since=since,
            until=until,
            page=page,
            page_size=page_size,
        )
    except CatalogNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/repositories/{repository_id}/contributors/{contributor_key}/commits",
    response_model=CommitPage,
)
def list_contributor_commits(
    repository_id: int,
    contributor_key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    queries: QueryService = Depends(get_query_service),
):
    try:
        return queries.list_commits(repository_id, contributor_key, page, page_size)
    except (CatalogNotFound, InvalidContributorKey) as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


def _run_sync(action) -> SyncResult:
    try:
        return action()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CatalogNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except RepositoryNotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
