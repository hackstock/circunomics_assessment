from app.identity import (
    InvalidContributorKey,
    contributor_identity,
    decode_contributor_key,
    encode_contributor_key,
    parse_full_name,
)
from app.providers.base import CatalogNotFound, VcsProvider


def test_parse_full_name():
    assert parse_full_name(" octo/hello ") == ("octo", "hello")
    try:
        parse_full_name("not-a-repo")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_contributor_identity_email_then_name():
    assert contributor_identity("Ada@Example.com", "Ada") == "ada@example.com"
    assert contributor_identity("", "Ada Lovelace") == "ada lovelace"
    assert contributor_identity(None, "") == "unknown"


def test_contributor_key_roundtrip_and_invalid():
    encoded = encode_contributor_key("ada@example.com")
    assert decode_contributor_key(encoded) == "ada@example.com"
    try:
        decode_contributor_key("_w")
        raised = False
    except InvalidContributorKey:
        raised = True
    assert raised
    assert InvalidContributorKey().message == "Contributor not found"


def test_catalog_not_found_default_message():
    assert CatalogNotFound().message == "Repository not found"


def test_vcs_provider_base_is_abstract():
    try:
        list(VcsProvider().iter_recent_commits("o", "r", 1))
        raised = False
    except NotImplementedError:
        raised = True
    assert raised
