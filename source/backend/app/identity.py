from __future__ import annotations

import base64
import binascii
import re


FULL_NAME_RE = re.compile(r"^([^/]+)/([^/]+)$")


class InvalidContributorKey(Exception):
    def __init__(self, message: str = "Contributor not found"):
        super().__init__(message)
        self.message = message


def parse_full_name(full_name: str) -> tuple[str, str]:
    match = FULL_NAME_RE.match(full_name.strip())
    if not match:
        raise ValueError("Repository must be in the form owner/repo")
    return match.group(1), match.group(2)


def contributor_identity(email: str | None, name: str) -> str:
    email_key = (email or "").strip().lower()
    if email_key:
        return email_key
    return (name or "unknown").strip().lower()


def encode_contributor_key(key: str) -> str:
    return base64.urlsafe_b64encode(key.encode()).decode().rstrip("=")


def decode_contributor_key(encoded: str) -> str:
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(encoded + padding).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidContributorKey() from exc
