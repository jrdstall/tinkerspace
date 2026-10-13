"""Tests for taxonomy normalization, tag sanitization, and triage GUI enhancements.

Traces TRIAGE-01, TRIAGE-06, EXPLORE-08 per design specs.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore
from iw.core.triage import CANONICAL_DOMAINS, DOMAIN_SUGGESTED_TAGS, sanitize_tags
from iw.web.app import create_app
from scripts.migrate_taxonomy import run_migration


def test_sanitize_tags_cleans_hashes_spaces_and_redundancies() -> None:
    """TRIAGE-06: sanitize_tags strips hashes, splits tokens, and drops type/domain echoes."""
    # 1. Comma-separated with hashes and type/domain redundancy
    raw = "#ambient-computing, #iot, #hardware, #friction, #computing"
    cleaned = sanitize_tags(raw, domain="Computing & Architecture", node_type="friction")
    assert "friction" not in cleaned
    assert "computing & architecture" not in cleaned
    assert "ambient-computing" in cleaned
    assert "iot" in cleaned

    # 2. Space-separated without commas
    raw_spaced = "cycling consumer safety"
    cleaned_spaced = sanitize_tags(raw_spaced, domain="Mobility & Transportation", node_type="idea")
    assert cleaned_spaced == ["cycling", "consumer", "safety"]

    # 3. Direct domain echo exclusion
    raw_echo = "Space Systems, satellite, smallsat"
    cleaned_echo = sanitize_tags(raw_echo, domain="Space Systems", node_type="question")
    assert "space systems" not in cleaned_echo
    assert "question" not in cleaned_echo
    assert cleaned_echo == ["satellite", "smallsat"]


def test_triage_view_provides_canonical_domains_and_tag_datalists(tmp_path: Path) -> None:
    """TRIAGE-01: Triage view passes canonical domains and tag autocomplete lists to template."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    node = Node(
        id="FRI-A01",
        type="friction",
        title="Existing node",
        created=datetime.now(timezone.utc),
        domain="Space Systems",
        tags=["smallsat", "telemetry"],
    )
    store.write_node(node, author=author)
    store.append_inbox("New un-triaged note")

    app = create_app(store=store)
    client = TestClient(app)

    res = client.get("/triage")
    assert res.status_code == 200
    # Datalist for canonical domains exists
    assert '<datalist id="canonical-domains">' in res.text
    import html
    for dom in CANONICAL_DOMAINS:
        assert f'<option value="{html.escape(dom)}">' in res.text

    # Datalist for vault tags exists
    assert '<datalist id="vault-tags">' in res.text
    assert '<option value="smallsat">' in res.text
    assert '<option value="telemetry">' in res.text

    # Suggested tags pills container exists
    assert 'id="suggested-tags-container"' in res.text


def test_node_edit_view_has_canonical_domains_datalist(tmp_path: Path) -> None:
    """EXPLORE-08: Node detail edit view provides domain and tag datalists without keywords input."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Kitchen eInk Display",
        created=datetime.now(timezone.utc),
        domain="Computing & Architecture",
        tags=["ambient-computing", "e-ink"],
    )
    store.write_node(node, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    res = client.get("/node/IDEA-A01")
    assert res.status_code == 200
    assert '<datalist id="canonical-domains">' in res.text
    assert '<datalist id="vault-tags">' in res.text
    # Keywords input field is removed from edit form
    assert 'name="keywords"' not in res.text


def test_migration_script_cleans_vault_nodes(tmp_path: Path) -> None:
    """STORE-10: run_migration normalizes taxonomy, strips redundant tags, and drops keywords."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    # Node with old domain, redundant domain tag, and legacy keywords attribute
    node = Node(
        id="FRI-A01",
        type="friction",
        title="Recipes on Phone Screens",
        created=datetime.now(timezone.utc),
        domain="compute",
        tags=["compute", "cooking", "smartphones"],
        attrs={"keywords": ["recipe", "kitchen"]},
    )
    store.write_node(node, author=author)

    # 1. Dry run
    run_migration(tmp_path, apply=False)
    dry_node = store.get_node("FRI-A01")
    assert dry_node is not None
    assert dry_node.domain == "compute"

    # 2. Apply migration
    run_migration(tmp_path, apply=True)
    migrated_node = store.get_node("FRI-A01")
    assert migrated_node is not None
    assert migrated_node.domain == "Living & Preparedness"
    assert "compute" not in migrated_node.tags
    assert "keywords" not in migrated_node.attrs
