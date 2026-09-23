"""Behaviour tests for direct idea attachments, linked captures, and prompt ingestion.

Traces INTAKE-05, INTAKE-06, WORKFLOW-07, and MCP-01.
"""

from datetime import datetime, timezone
import io
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node, UnitOfWork, UnitState
from iw.core.store import MarkdownStore
from iw.domain.workflow.context import (
    format_attachments_markdown,
    format_linked_notes_markdown,
    resolve_subject_attachments,
    resolve_subject_linked_notes,
    stage_subject_files_to_unit,
)
from iw.domain.workflow.prompt import compose_full_prompt
from iw.mcp.tools import read_unit_tool
from iw.web.app import create_app


def test_intake_05_direct_file_upload_and_drop_attachment(tmp_path: Path) -> None:
    """INTAKE-05: Direct file upload and drop-file attachment creates ART node and links edge."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Handlebar Navigation Puck",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["bike", "ble"],
        body="A sleek bike computer.",
        state="active",
    )
    store.write_node(idea, author=author)
    client = TestClient(create_app(store))

    # 1. Direct file upload with concept graphic
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1afakeimage")
    resp = client.post(
        "/node/IDEA-A01/attach_file",
        data={"title": "OV-1 Concept Sketch", "relation": "illustrates", "set_concept_graphic": "1"},
        files={"file": ("puck-ov1.png", fake_png, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    reloaded = store.get_node("IDEA-A01")
    assert reloaded is not None
    assert reloaded.attrs.get("concept_graphic") == "attachments/IDEA-A01/puck-ov1.png"
    assert len(reloaded.edges) == 1
    edge = reloaded.edges[0]
    assert edge.relation == "illustrates"
    assert edge.to_id == "ART-A01"

    art = store.get_node("ART-A01")
    assert art is not None
    assert art.type == "artifact"
    assert art.attrs.get("path") == "attachments/IDEA-A01/puck-ov1.png"
    assert (tmp_path / "attachments" / "IDEA-A01" / "puck-ov1.png").exists()

    # 2. Attach from drop folder
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)
    (drop_dir / "notes.txt").write_text("Drop file notes", encoding="utf-8")

    resp2 = client.post(
        "/node/IDEA-A01/attach_file",
        data={"drop_file": "notes.txt", "relation": "evidence_for", "title": "Field Notes"},
        follow_redirects=False,
    )
    assert resp2.status_code == 303
    reloaded2 = store.get_node("IDEA-A01")
    assert reloaded2 is not None
    assert len(reloaded2.edges) == 2
    assert reloaded2.edges[1].to_id == "ART-A02"


def test_intake_06_in_context_linked_note_capture(tmp_path: Path) -> None:
    """INTAKE-06: In-context capturing of linked child idea, observation, and question."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Thermal Harvester",
        created=datetime.now(timezone.utc),
        domain="energy",
        tags=["thermal"],
        body="Harvest energy from heat gradients.",
        state="active",
    )
    store.write_node(idea, author=author)
    client = TestClient(create_app(store))

    # 1. Capture linked observation
    resp_obs = client.post(
        "/node/IDEA-A01/capture_linked",
        data={
            "type": "observation",
            "title": "Seebeck coefficient test",
            "relation": "evidence_for",
            "body": "Tested Bi2Te3 couple at 40C delta.",
            "tags": "test, lab",
        },
        follow_redirects=False,
    )
    assert resp_obs.status_code == 303
    obs = store.get_node("OBS-A01")
    assert obs is not None
    assert obs.type == "observation"
    assert obs.title == "Seebeck coefficient test"

    # 2. Capture linked question
    resp_que = client.post(
        "/node/IDEA-A01/capture_linked",
        data={
            "type": "question",
            "title": "What is heat sink cost?",
            "relation": "questions",
            "body": "Extruded aluminum vs folded fin.",
        },
        follow_redirects=False,
    )
    assert resp_que.status_code == 303
    que = store.get_node("QUE-A01")
    assert que is not None
    assert que.type == "question"

    parent = store.get_node("IDEA-A01")
    assert parent is not None
    edge_targets = [e.to_id for e in parent.edges]
    assert "OBS-A01" in edge_targets
    assert "QUE-A01" in edge_targets


def test_workflow_07_prompt_composition_embeds_file_contents_and_context(tmp_path: Path) -> None:
    """WORKFLOW-07: Prompt composition embeds readable file content and lists linked notes."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    att_dir = tmp_path / "attachments" / "IDEA-A01"
    att_dir.mkdir(parents=True, exist_ok=True)
    spec_file = att_dir / "bench-test.md"
    spec_file.write_text("# Bench Test Results\nPower output: 42mW at 35C delta.\nEfficiency: 4.8%.", encoding="utf-8")

    art_node = Node(
        id="ART-A01",
        type="artifact",
        title="Bench Test Report",
        created=datetime.now(timezone.utc),
        domain="energy",
        tags=["report"],
        body="Lab test markdown file.",
        attrs={"path": "attachments/IDEA-A01/bench-test.md", "file_name": "bench-test.md"},
    )
    store.write_node(art_node, author=author)

    obs_node = Node(
        id="OBS-A01",
        type="observation",
        title="Ambient thermal stability",
        created=datetime.now(timezone.utc),
        domain="energy",
        tags=["thermal"],
        body="Room ambient stayed at 21C throughout run.",
    )
    store.write_node(obs_node, author=author)

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Peltier Energy Harvester",
        created=datetime.now(timezone.utc),
        domain="energy",
        tags=["thermal", "harvesting"],
        body="Thermoelectric generator for remote IoT sensors.",
        state="active",
        edges=[
            Edge(from_id="IDEA-A01", to_id="ART-A01", relation="evidence_for", created=datetime.now(timezone.utc), author=author),
            Edge(from_id="IDEA-A01", to_id="OBS-A01", relation="evidence_for", created=datetime.now(timezone.utc), author=author),
        ],
    )
    store.write_node(idea, author=author)

    full_prompt = compose_full_prompt(
        unit_id="UOW-A01",
        unit_title="Feasibility Assessment",
        task_instructions="Evaluate market and physical feasibility.",
        subject_node=idea,
        store=store,
        vault_dir=tmp_path,
    )

    assert "## 2. Subject Concept Context" in full_prompt
    assert "Peltier Energy Harvester" in full_prompt
    assert "### Attached Reference Files & Deliverables" in full_prompt
    assert "File: `bench-test.md`" in full_prompt
    assert "Power output: 42mW at 35C delta." in full_prompt
    assert "### Linked Notes & Context" in full_prompt
    assert "[OBS-A01] Ambient thermal stability" in full_prompt
    assert "Room ambient stayed at 21C" in full_prompt


def test_mcp_01_read_unit_tool_stages_files_and_returns_full_prompt(tmp_path: Path) -> None:
    """MCP-01: read_unit_tool returns prompt with embedded files and populates input_files."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    att_dir = tmp_path / "attachments" / "IDEA-A01"
    att_dir.mkdir(parents=True, exist_ok=True)
    (att_dir / "circuit.json").write_text('{"resistor": 100, "v_in": 3.3}', encoding="utf-8")

    art_node = Node(
        id="ART-A01",
        type="artifact",
        title="Circuit Schematic",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["schematic"],
        attrs={"path": "attachments/IDEA-A01/circuit.json", "file_name": "circuit.json"},
    )
    store.write_node(art_node, author=author)

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Smart Sensor Node",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["sensor"],
        body="Low power sensor.",
        state="active",
        edges=[
            Edge(from_id="IDEA-A01", to_id="ART-A01", relation="illustrates", created=datetime.now(timezone.utc), author=author),
        ],
    )
    store.write_node(idea, author=author)

    unit = UnitOfWork(
        id="UOW-A01",
        title="Schematic Review",
        activity="architecture-spike",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
        action_guide="Check resistor divider ratios.",
    )
    store.write_unit(unit, author=author)

    result = read_unit_tool(store, "UOW-A01")
    assert result["id"] == "UOW-A01"
    assert "circuit.json" in result["input_files"]
    assert "circuit.json" in result["prompt"]
    assert '{"resistor": 100, "v_in": 3.3}' in result["prompt"]
    staged_file = tmp_path / "work" / "UOW-A01" / "circuit.json"
    assert staged_file.exists()
