"""Round-trip persistence tests for all 8 node types.

Traces STORE-01, STORE-03, STORE-04, and DA-02 frontmatter schemas.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore


def test_all_eight_node_types_roundtrip_cleanly(tmp_path: Path):
    """All 8 node types write and read back their specific frontmatter fields intact."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    now = datetime.now(timezone.utc)

    nodes_to_test = [
        Node(
            id="FRI-A01",
            type="friction",
            title="Handlebars too wide for urban riding",
            created=now,
            domain="cycling",
            tags=["ergonomics", "urban"],
            attrs={"stem": "There has to be a better way to...", "source": {"inlet": "quick-capture"}},
            body="Prose for friction node.",
        ),
        Node(
            id="OBS-A01",
            type="observation",
            title="Most riders keep hands on hoods 90% of time",
            created=now,
            domain="cycling",
            tags=["ergonomics", "field-data"],
            attrs={"origin": "observed"},
            body="Prose for observation node.",
        ),
        Node(
            id="IDEA-A01",
            type="idea",
            title="Narrow flared endurance handlebar",
            created=now,
            domain="cycling",
            tags=["hardware", "handlebar"],
            attrs={
                "worth_me": "high",
                "worth_others": "medium",
                "scores": {"novel": 3, "works": 4, "reach": 2, "story": 3},
                "screening_verdict": "pursue",
                "screening_reason": "Clear personal need and simple prototype path.",
            },
            body="Prose for idea node.",
        ),
        Node(
            id="QUE-A01",
            type="question",
            title="What is minimum comfortable hood width?",
            created=now,
            domain="cycling",
            tags=["ergonomics", "inquiry"],
            attrs={"form": "open", "importance": "high", "held_open": True},
            body="Prose for question node.",
        ),
        Node(
            id="EXP-A01",
            type="experiment",
            title="Test 36cm hoods on 50km gravel route",
            created=now,
            domain="cycling",
            tags=["trial", "ergonomics"],
            body="Prose for experiment node.",
        ),
        Node(
            id="AST-A01",
            type="asset",
            title="Carbon fiber layup kit and vacuum pump",
            created=now,
            domain="fabrication",
            tags=["equipment", "composites"],
            state="have",
            attrs={"kind": "equipment"},
            body="Prose for asset node.",
        ),
        Node(
            id="ART-A01",
            type="artifact",
            title="Handlebar aero drag test report",
            created=now,
            domain="cycling",
            tags=["report", "data"],
            attrs={
                "role": "report",
                "produced_by": "UOW-A01",
                "input_to": ["UOW-A02"],
                "source_file": "work/UOW-A01/report.md",
                "rendered_file": None,
            },
            body="Prose for artifact node.",
        ),
        Node(
            id="SRC-A01",
            type="source",
            title="Wind tunnel CFD study on cockpit width",
            created=now,
            domain="cycling",
            tags=["paper", "aerodynamics"],
            attrs={
                "inlet": "file-drop",
                "original_file": "cfd_cockpit_study_2025.pdf",
                "mime_type": "application/pdf",
            },
            body="Prose for source node.",
        ),
    ]

    for original in nodes_to_test:
        written = store.write_node(original, author=author)
        fetched = store.get_node(original.id)

        assert fetched is not None
        assert fetched.id == original.id
        assert fetched.type == original.type
        assert fetched.title == original.title
        assert fetched.domain == original.domain
        assert fetched.tags == original.tags
        assert fetched.body == original.body

        # Check type-specific attributes
        for k, v in original.attrs.items():
            assert fetched.attrs.get(k) == v


def test_idea_cml_is_derived_and_materialized_on_write(tmp_path: Path):
    """Idea CML score is calculated as min(novel, works, reach, story) and saved to disk."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea_node = Node(
        id="IDEA-A02",
        type="idea",
        title="Sunlight readable handlebar puck",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["display", "ble"],
        attrs={
            "worth_me": "high",
            "worth_others": "low",
            "scores": {"novel": 4, "works": 3, "reach": 2, "story": 5},
        },
        body="Prose body",
    )
    store.write_node(idea_node, author=author)

    # Re-read raw file to ensure cml is materialized in YAML frontmatter (DA-03 §03 / V§14.15)
    idea_file = next(tmp_path.rglob("*.md"))
    content = idea_file.read_text(encoding="utf-8")
    assert "cml: 2" in content

    fetched = store.get_node("IDEA-A02")
    assert fetched is not None
    assert fetched.attrs["cml"] == 2
