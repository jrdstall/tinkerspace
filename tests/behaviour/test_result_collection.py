"""Behaviour tests for Human Step Templates and Result Collection Pipeline.

Traces COLLECT-01 through COLLECT-08 per docs/design/specs/COLLECT.md.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient
import yaml

from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState, Workflow
from iw.core.store import MarkdownStore
from iw.domain.workflow.collection import (
    collect_unit_results,
    generate_human_starter_template,
    parse_deliverable_text,
)
from iw.domain.workflow.runtime import WorkflowRuntime
from iw.web.app import create_app


def _sample_human_unit(unit_id: str = "UOW-A01") -> UnitOfWork:
    return UnitOfWork(
        id=unit_id,
        title="Display Sunlight Readability Trade Study",
        activity="trade-study@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
        assignee={"kind": "human", "name": "Jared"},
    )


def _sample_idea_node(node_id: str = "IDEA-A01") -> Node:
    from datetime import datetime, timezone
    return Node(
        id=node_id,
        type="idea",
        title="Sunlight Readable Handlebar Computer",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display", "handlebar"],
        body="Low-power bike computer for outdoor riding.",
        attrs={"scores": {"novel": 4, "works": 1, "reach": 1, "story": 1}, "cml": 1},
    )


def test_collect_01_human_dispatch_generates_starter_template(tmp_path: Path):
    """COLLECT-01: Dispatching a human unit generates starter deliverable.md with headings."""
    store = MarkdownStore(vault_dir=tmp_path)
    unit = _sample_human_unit("UOW-A01")
    store.write_unit(unit, author=Author(kind=AuthorKind.HUMAN, courier="web-ui"))

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)

    # Dispatch via web endpoint
    res = client.post("/board/dispatch", data={"unit_id": "UOW-A01"})
    assert res.status_code == 303

    starter_file = tmp_path / "work" / "UOW-A01" / "deliverable.md"
    assert starter_file.exists()

    content = starter_file.read_text(encoding="utf-8")
    assert "Display Sunlight Readability Trade Study" in content
    assert "## Executive Summary" in content
    assert "## Options & Trade-Offs" in content
    assert "## Recommendation" in content


def test_collect_02_parses_yaml_and_html_comment_headers_and_zero_header():
    """COLLECT-02: Parsing deliverable extracts metadata from YAML, HTML comments, and zero-header."""
    # 1. YAML frontmatter
    yaml_text = "---\nunit: UOW-A01\nsummary: MIP chosen\nverdict: pass\nscores:\n  works: 3\n---\n# Findings\nProse"
    h1, b1 = parse_deliverable_text(yaml_text, "UOW-A01")
    assert h1.summary == "MIP chosen"
    assert h1.verdict == "pass"
    assert h1.scores == {"works": 3}
    assert "# Findings" in b1

    # 2. HTML comment
    comment_text = "<!--\nunit: UOW-A01\nsummary: Comment header\nscores:\n  works: 4\n-->\n# Obsidian Notes\nProse"
    h2, b2 = parse_deliverable_text(comment_text, "UOW-A01")
    assert h2.summary == "Comment header"
    assert h2.scores == {"works": 4}
    assert "# Obsidian Notes" in b2

    # 3. Zero-header
    zero_text = "# Plain Notes\nJust raw thoughts and drawings."
    h3, b3 = parse_deliverable_text(zero_text, "UOW-A01")
    assert h3.unit == "UOW-A01"
    assert h3.summary == ""
    assert b3 == zero_text


def test_collect_03_malformed_yaml_header_gracefully_degrades_without_error():
    """COLLECT-03: Malformed headers gracefully degrade without exceptions, preserving all text."""
    bad_yaml = "---\nunit: UOW-BAD\nscores: [invalid: yaml: syntax\n---\n# Real Work Output\nCritical data."
    header, body = parse_deliverable_text(bad_yaml, "UOW-BAD")

    assert header.unit == "UOW-BAD"
    assert header.parse_warning is not None
    assert "# Real Work Output" in body
    assert "Critical data." in body


def test_collect_04_open_hospitality_registers_all_discovered_files_as_artifacts(tmp_path: Path):
    """COLLECT-04: Collection scans work folder and registers ART-xxx nodes for all files found."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea = _sample_idea_node("IDEA-A01")
    unit = _sample_human_unit("UOW-A04")
    store.write_node(idea, author=author)
    store.write_unit(unit, author=author)

    work_folder = tmp_path / "work" / "UOW-A04"
    work_folder.mkdir(parents=True, exist_ok=True)
    (work_folder / "deliverable.md").write_text("# Report\nMain report prose.", encoding="utf-8")
    (work_folder / "sketch.svg").write_text("<svg>sketch</svg>", encoding="utf-8")
    (work_folder / "bench-data.csv").write_text("power,current\n10,20", encoding="utf-8")

    unit, created_arts = collect_unit_results(store=store, unit_id="UOW-A04", author=author)

    assert len(created_arts) == 3
    art_ids = {a.id for a in created_arts}
    assert all(a.startswith("ART-") for a in art_ids)

    # Check artifacts in store
    all_arts = store.list_nodes(type_filter="artifact")
    assert len(all_arts) == 3


def test_collect_05_attribution_stamped_with_courier_and_author(tmp_path: Path):
    """COLLECT-05: Attribution is stamped on collection with observed courier and author."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea = _sample_idea_node("IDEA-A01")
    unit = _sample_human_unit("UOW-A05")
    store.write_node(idea, author=author)
    store.write_unit(unit, author=author)

    work_folder = tmp_path / "work" / "UOW-A05"
    work_folder.mkdir(parents=True, exist_ok=True)
    (work_folder / "deliverable.md").write_text("# Report\nContent.", encoding="utf-8")

    unit, created_arts = collect_unit_results(store=store, unit_id="UOW-A05", author=author)

    for art in created_arts:
        reloaded = store.get_node(art.id)
        assert reloaded.author is not None and reloaded.author.courier == "web-ui"


def test_collect_06_materializes_scores_and_recomputes_cml_on_subject_node(tmp_path: Path):
    """COLLECT-06: Evaluated scores materialize into subject node and recompute derived CML."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # Initial Idea node: novel=4, works=1, reach=1, story=1 -> cml=1
    idea = _sample_idea_node("IDEA-A01")
    unit = _sample_human_unit("UOW-A06")
    store.write_node(idea, author=author)
    store.write_unit(unit, author=author)

    work_folder = tmp_path / "work" / "UOW-A06"
    work_folder.mkdir(parents=True, exist_ok=True)
    deliverable_content = (
        "---\n"
        "unit: UOW-A06\n"
        "summary: Bench tests show working MIP display and validated user reach\n"
        "scores:\n"
        "  works: 4\n"
        "  reach: 3\n"
        "  story: 3\n"
        "---\n"
        "# Maturation Trade Study\n"
        "Detailed bench test analysis."
    )
    (work_folder / "deliverable.md").write_text(deliverable_content, encoding="utf-8")

    collect_unit_results(store=store, unit_id="UOW-A06", author=author)

    updated_idea = store.get_node("IDEA-A01")
    assert updated_idea is not None
    scores = updated_idea.attrs.get("scores", {})
    assert scores["novel"] == 4
    assert scores["works"] == 4
    assert scores["reach"] == 3
    assert scores["story"] == 3
    # cml = min(4, 4, 3, 3) = 3
    assert updated_idea.attrs.get("cml") == 3


def test_collect_07_materializes_verdict_and_summary_on_subject_node(tmp_path: Path):
    """COLLECT-07: Screening verdicts and summary materialize into subject node frontmatter."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea = _sample_idea_node("IDEA-A01")
    unit = _sample_human_unit("UOW-A07")
    store.write_node(idea, author=author)
    store.write_unit(unit, author=author)

    work_folder = tmp_path / "work" / "UOW-A07"
    work_folder.mkdir(parents=True, exist_ok=True)
    deliverable_content = (
        "<!--\n"
        "unit: UOW-A07\n"
        "summary: Display feasibility screening passed\n"
        "verdict: pass\n"
        "-->\n"
        "# Feasibility Notes\n"
    )
    (work_folder / "deliverable.md").write_text(deliverable_content, encoding="utf-8")

    collect_unit_results(store=store, unit_id="UOW-A07", author=author)

    updated_idea = store.get_node("IDEA-A01")
    assert updated_idea is not None
    assert updated_idea.attrs.get("screening_verdict") == "pass"
    history = updated_idea.attrs.get("activity_log", [])
    assert any("Display feasibility screening passed" in entry for entry in history)


def test_collect_08_collection_sets_unit_to_accepted_and_unblocks_successors(tmp_path: Path):
    """COLLECT-08: Successful collection transitions unit to accepted and unblocks downstream steps."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea = _sample_idea_node("IDEA-A01")
    store.write_node(idea, author=author)

    wfl = Workflow(
        id="WFL-A08",
        title="2-Step Maturation Pipeline",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02"],
        dependencies={"UOW-A02": ["UOW-A01"]},
    )
    u1 = _sample_human_unit("UOW-A01")
    u2 = UnitOfWork(id="UOW-A02", title="Step 2", activity="trade-study@1", state=UnitState.BLOCKED, subject_ids=["IDEA-A01"])
    runtime.create_workflow(wfl, [u1, u2], author=author)

    # Dispatch UOW-A01
    work_folder = tmp_path / "work" / "UOW-A01"
    work_folder.mkdir(parents=True, exist_ok=True)
    (work_folder / "deliverable.md").write_text("<!--\nunit: UOW-A01\nsummary: Step 1 completed\n-->\n# Step 1", encoding="utf-8")

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)

    # Click Attach Result via POST /board/collect
    res = client.post("/board/collect", data={"unit_id": "UOW-A01"})
    assert res.status_code == 303

    # UOW-A01 is now ACCEPTED
    reloaded_u1 = store.get_unit("UOW-A01")
    assert reloaded_u1 is not None
    assert reloaded_u1.state == UnitState.ACCEPTED

    # Re-evaluating ready set unblocks UOW-A02
    ready_units = runtime.compute_ready_set("WFL-A08")
    assert [u.id for u in ready_units] == ["UOW-A02"]
