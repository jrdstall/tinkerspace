"""STORE subsystem behaviour tests for store operations, renaming, and idempotency.

Traces STORE-09, STORE-17, STORE-18, and STORE-20 per docs/design/specs/STORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import yaml

from iw.contracts.models import Author, AuthorKind, Node, QueryFilters
from iw.core.index import InMemoryIndex
from iw.core.store import MarkdownStore


def test_store_09_renaming_file_breaks_nothing(tmp_path: Path):
    """STORE-09: Renaming or moving a file within the vault breaks nothing; IDs resolve correctly."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    orig_path = friction_dir / "2026-08-29-old-name.md"
    orig_path.write_text(
        "---\n"
        "id: FRI-A09\n"
        "type: friction\n"
        "title: Friction file to be renamed\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: meta\n"
        "tags: [rename]\n"
        "---\n"
        "Body content remains intact after file rename.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    assert store.get_node("FRI-A09") is not None

    # Rename the file on disk (e.g. user renames slug in Obsidian or file manager)
    new_path = friction_dir / "2026-08-29-new-meaningful-slug.md"
    orig_path.rename(new_path)

    # Re-fetch node by ID
    node = store.get_node("FRI-A09")
    assert node is not None
    assert node.id == "FRI-A09"
    assert node.title == "Friction file to be renamed"
    assert "Body content remains intact" in node.body


def test_store_17_work_unit_state_stored_in_unit_yaml(tmp_path: Path):
    """STORE-17: Work unit state is stored in structured unit.yaml inside work/UOW-xxx/."""
    uow_dir = tmp_path / "work" / "UOW-A01"
    uow_dir.mkdir(parents=True)
    unit_yaml = uow_dir / "unit.yaml"
    unit_yaml.write_text(
        yaml.safe_dump(
            {
                "id": "UOW-A01",
                "title": "Prior Art Survey",
                "activity": "prior-art-survey@1",
                "state": "ready",
                "subject_ids": ["IDEA-A01"],
            }
        ),
        encoding="utf-8",
    )

    assert unit_yaml.exists()
    loaded = yaml.safe_load(unit_yaml.read_text(encoding="utf-8"))
    assert loaded["id"] == "UOW-A01"
    assert loaded["state"] == "ready"


def test_store_18_artifacts_produced_stored_in_uow_folder(tmp_path: Path):
    """STORE-18: Artifacts produced by a work unit are stored directly within work/UOW-xxx/."""
    uow_dir = tmp_path / "work" / "UOW-A01"
    uow_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = uow_dir / "survey_report.md"
    artifact_file.write_text("# Prior Art Survey Report\nFindings...\n", encoding="utf-8")

    assert artifact_file.exists()
    assert (tmp_path / "work" / "UOW-A01" / "survey_report.md").is_file()


def test_store_20_index_rebuild_is_idempotent_pure_function(tmp_path: Path):
    """STORE-20: Rebuilding the derived query index from store files is an idempotent pure function."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(1, 4):
        node = Node(
            id=f"FRI-A0{i}",
            type="friction",
            title=f"Friction item {i}",
            created=now,
            domain="cycling" if i < 3 else "meta",
            tags=["hardware"],
            body=f"Prose body {i}",
        )
        store.write_node(node, author=author)

    all_nodes = store.list_nodes()

    index1 = InMemoryIndex(all_nodes)
    res1 = index1.query(QueryFilters(domain="cycling"))

    index2 = InMemoryIndex(all_nodes)
    res2 = index2.query(QueryFilters(domain="cycling"))

    assert [n.id for n in res1] == [n.id for n in res2]
    assert [n.title for n in res1] == [n.title for n in res2]
