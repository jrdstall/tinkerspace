"""Behaviour tests for Idea Maturity Assessment, CML Calculation, and Concept Graphics.

Proves ASSESS-01 through ASSESS-08 from docs/design/specs/ASSESS.md:
- ASSESS-01: Maturity scores (novel, works, reach, story) 1-5
- ASSESS-02: CML is minimum of four scores
- ASSESS-03: Unassessed ideas default to CML 1
- ASSESS-04: Independent worth ratings (worth_to_me, worth_to_others)
- ASSESS-05: Worth ratings never modify or drag down CML
- ASSESS-06: Screening verdicts (pursue, park, let_go) with reasons
- ASSESS-07: Laggard score identification and activity recommendation
- ASSESS-08: Concept graphic designation and rendering on node detail
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.assessor.cml import (
    apply_assessment_to_node,
    compute_cml,
    identify_laggards,
    recommend_activity_for_laggard,
)
from iw.web.app import create_app


def test_assess_01_maturity_scores_record_integer_ratings_1_to_5():
    """ASSESS-01: An assessment records 4 maturity scores (novel, works, reach, story) 1 to 5."""
    scores = {"novel": 4, "works": 3, "reach": 2, "story": 5}
    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Low-cost road cycling HUD",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling", "display"],
    )
    assessed = apply_assessment_to_node(node, scores=scores)
    assert assessed.attrs["scores"]["novel"] == 4
    assert assessed.attrs["scores"]["works"] == 3
    assert assessed.attrs["scores"]["reach"] == 2
    assert assessed.attrs["scores"]["story"] == 5


def test_assess_02_cml_is_integer_minimum_of_maturity_scores():
    """ASSESS-02: An idea's CML is the integer minimum of its four maturity scores."""
    scores_1 = {"novel": 4, "works": 3, "reach": 2, "story": 5}
    assert compute_cml(scores_1) == 2

    scores_2 = {"novel": 4, "works": 4, "reach": 4, "story": 4}
    assert compute_cml(scores_2) == 4

    scores_3 = {"novel": 5, "works": 5, "reach": 5, "story": 5}
    assert compute_cml(scores_3) == 5


def test_assess_03_unassessed_idea_defaults_to_cml_1_without_scores():
    """ASSESS-03: An unassessed idea cleanly defaults to CML 1 without requiring score fields."""
    node = Node(
        id="IDEA-A02",
        type="idea",
        title="Raw Spark Idea",
        created=datetime.now(timezone.utc),
        domain="software",
        tags=["unassessed"],
    )
    assert compute_cml(node.attrs.get("scores")) == 1
    assessed = apply_assessment_to_node(node)
    assert assessed.attrs["cml"] == 1


def test_assess_04_worth_ratings_recorded_independently():
    """ASSESS-04: An assessment records two independent worth ratings (worth_to_me, worth_to_others)."""
    node = Node(
        id="IDEA-A03",
        type="idea",
        title="Bespoke Mechanical Keyboard",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["hobby"],
    )
    assessed = apply_assessment_to_node(
        node,
        worth_to_me="high",
        worth_to_others="low",
    )
    assert assessed.attrs["worth_to_me"] == "high"
    assert assessed.attrs["worth_to_others"] == "low"


def test_assess_05_worth_ratings_never_modify_or_lower_cml():
    """ASSESS-05: Worth ratings never modify or drag down the CML level."""
    node = Node(
        id="IDEA-A04",
        type="idea",
        title="Advanced Niche Point Design",
        created=datetime.now(timezone.utc),
        domain="software",
        tags=["niche"],
    )
    scores = {"novel": 4, "works": 4, "reach": 4, "story": 4}
    assessed = apply_assessment_to_node(
        node,
        scores=scores,
        worth_to_me="low",
        worth_to_others="low",
    )
    assert assessed.attrs["cml"] == 4
    assert assessed.attrs["worth_to_me"] == "low"


def test_assess_06_screening_verdicts_and_reasons_recorded():
    """ASSESS-06: A screening verdict is one of pursue, park, or let_go with a text reason."""
    node = Node(
        id="IDEA-A05",
        type="idea",
        title="Alternative Storage Engine",
        created=datetime.now(timezone.utc),
        domain="infrastructure",
        tags=["storage"],
    )
    assessed = apply_assessment_to_node(
        node,
        verdict="park",
        reason="Promising mechanism, but current sync solution is working well.",
    )
    assert assessed.attrs["screening_verdict"] == "park"
    assert assessed.attrs["screening_reason"] == "Promising mechanism, but current sync solution is working well."


def test_assess_07_laggard_scores_identified_and_mapped_to_activities():
    """ASSESS-07: Laggard scores are identified as the minimum score keys and map to activities."""
    scores = {"novel": 3, "works": 4, "reach": 2, "story": 4}
    laggards = identify_laggards(scores)
    assert laggards == ["reach"]
    assert recommend_activity_for_laggard(laggards[0]) == "parts-and-skills-survey@1"

    tied_scores = {"novel": 1, "works": 2, "reach": 1, "story": 3}
    tied_laggards = identify_laggards(tied_scores)
    assert tied_laggards == ["novel", "reach"]
    assert recommend_activity_for_laggard("novel") == "prior-art-survey@1"
    assert recommend_activity_for_laggard("works") == "feasibility-spike@1"
    assert recommend_activity_for_laggard("story") == "pitch-draft@1"


def test_assess_08_concept_graphic_designated_and_rendered_on_node(tmp_path: Path):
    """ASSESS-08: An idea specifies concept_graphic which renders as hero graphic on node detail."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    drop_dir = vault_dir / "drop"
    drop_dir.mkdir()
    img_file = drop_dir / "cycling_ov1.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_content")

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="IDEA-A06",
        type="idea",
        title="HUD Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling"],
        attrs={
            "concept_graphic": "drop/cycling_ov1.png",
            "scores": {"novel": 3, "works": 3, "reach": 3, "story": 3},
            "worth_to_me": "high",
            "screening_verdict": "pursue",
        },
    )
    store.write_node(node, author=author)

    loaded = store.get_node("IDEA-A06")
    assert loaded is not None
    assert loaded.attrs["concept_graphic"] == "drop/cycling_ov1.png"
    assert loaded.attrs["cml"] == 3

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/node/IDEA-A06")
    assert response.status_code == 200
    assert "Concept Graphic" in response.text
    assert "drop/cycling_ov1.png" in response.text
    assert "CML 3" in response.text
    assert "PURSUE" in response.text

    media_resp = client.get("/vault-file/drop/cycling_ov1.png")
    assert media_resp.status_code == 200
    assert media_resp.content == b"\x89PNG\r\n\x1a\nfake_image_content"
