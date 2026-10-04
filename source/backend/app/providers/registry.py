from functools import lru_cache

from app.config import settings
from app.providers.base import VcsProvider
from app.providers.github import GitHubProvider


@lru_cache
def get_provider() -> VcsProvider:
    return GitHubProvider(token=settings.github_token, api_base=settings.github_api_base)
