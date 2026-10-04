from datetime import datetime, timezone

from app.providers.base import NormalizedCommit, RateLimited, VcsProvider


def make_commit(
    sha: str,
    name: str = "Ada",
    email: str | None = "ada@example.com",
    when: str = "2024-01-01T12:00:00+00:00",
    url: str | None = None,
) -> NormalizedCommit:
    return NormalizedCommit(
        sha=sha,
        author_name=name,
        author_email=email,
        committed_at=datetime.fromisoformat(when),
        html_url=url or f"https://github.com/example/repo/commit/{sha}",
    )


class FakeProvider(VcsProvider):
    name = "github"

    def __init__(
        self,
        pages: list[list[NormalizedCommit]] | None = None,
        error_on_page: int | None = None,
        fail_with: Exception | None = None,
    ):
        self.pages = pages or []
        self.error_on_page = error_on_page
        self.fail_with = fail_with
        self.calls = 0

    def iter_recent_commits(self, owner: str, name: str, limit: int):
        if self.fail_with is not None:
            raise self.fail_with
        for index, page in enumerate(self.pages):
            self.calls += 1
            if self.error_on_page is not None and index == self.error_on_page:
                raise RateLimited("rate limited in test")
            yield page[: max(0, limit)]
