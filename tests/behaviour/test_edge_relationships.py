"""Behaviour tests for typed edge relationships between nodes.

Traces DA-03 §02 edge vocabulary and frontmatter edge serialization.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.core.store import MarkdownStore


def test_node_edges_are_serialized_and_deserialized_correctly(tmp_path: Path):
    """Nodes with typed edges serialize and roundtrip with full attribution."""
    store = MarkdownStore(vault_dir=tmp_path)
    human_author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    agent_author = Author(kind=AuthorKind.AGENT, courier="mcp-pull", declared_model="claude-3-5-sonnet")
    now = datetime.now(timezone.utc)

    edge1 = Edge(
        from_id="IDEA-A01",
        to_id="FRI-A01",
        relation="addresses",
        created=now,
        author=human_author,
        confidence=1.0,
        note="Solves handlebar numbness problem.",
    )
    edge2 = Edge(
        from_id="IDEA-A01",
        to_id="QUE-A01",
        relation="raises",
        created=now,
        author=agent_author,
        confidence=0.9,
        note="Question raised during trade study.",
    )

    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Handlebar concept with edges",
        created=now,
        domain="cycling",
        tags=["hardware"],
        edges=[edge1, edge2],
        body="Prose content",
    )
    store.write_node(node, author=human_author)

    fetched = store.get_node("IDEA-A01")
    assert fetched is not None
    assert len(fetched.edges) == 2

    e1 = fetched.edges[0]
    assert e1.from_id == "IDEA-A01"
    assert e1.to_id == "FRI-A01"
    assert e1.relation == "addresses"
    assert e1.author.kind == AuthorKind.HUMAN
    assert e1.confidence == 1.0
    assert e1.note == "Solves handlebar numbness problem."

    e2 = fetched.edges[1]
    assert e2.from_id == "IDEA-A01"
    assert e2.to_id == "QUE-A01"
    assert e2.relation == "raises"
    assert e2.author.kind == AuthorKind.AGENT
    assert e2.author.declared_model == "claude-3-5-sonnet"
    assert e2.confidence == 0.9
