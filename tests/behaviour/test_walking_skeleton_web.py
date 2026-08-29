"""Walking Skeleton end-to-end web behaviour tests.

Proves that a hand-authored friction file in the vault is listed in the Explore view
and rendered in full detail on the Node detail view.
"""

from pathlib import Path
from starlette.testclient import TestClient

from iw.core.store import MarkdownStore
from iw.web.app import create_app


def test_hand_authored_friction_file_appears_on_explore_list_page(tmp_path: Path):
    """A hand-typed friction note in the vault appears on the web explore list page."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    note_file = friction_dir / "2026-08-29-noisy-chain.md"
    note_file.write_text(
        "---\n"
        "id: FRI-A01\n"
        "type: friction\n"
        "title: Chain rubbing front derailleur cage\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: cycling\n"
        "tags: [hardware, drivetrain]\n"
        "state: active\n"
        "---\n"
        "Rubbing occurs only under load in highest gear.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "FRI-A01" in response.text
    assert "Chain rubbing front derailleur cage" in response.text
    assert "cycling" in response.text
    assert "#drivetrain" in response.text


def test_node_detail_view_renders_frontmatter_and_prose(tmp_path: Path):
    """The node detail page renders frontmatter fields and prose body accurately."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    note_file = friction_dir / "2026-08-29-saddle-pain.md"
    note_file.write_text(
        "---\n"
        "id: FRI-A02\n"
        "type: friction\n"
        "title: Saddle causes numbness after 2 hours\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: cycling\n"
        "tags: [ergonomics, bike-fit]\n"
        "state: active\n"
        "author:\n"
        "  kind: human\n"
        "  courier: manual\n"
        "---\n"
        "Pressure point seems located right on the perineal cut-out edge.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/node/FRI-A02")
    assert response.status_code == 200
    assert "FRI-A02" in response.text
    assert "Saddle causes numbness after 2 hours" in response.text
    assert "human (manual)" in response.text
    assert "Pressure point seems located right on the perineal cut-out edge." in response.text


def test_node_detail_view_returns_404_for_unknown_id(tmp_path: Path):
    """Requesting an unknown node ID returns HTTP 404."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/node/FRI-NONEXISTENT")
    assert response.status_code == 404
    assert "404 Not Found" in response.text
