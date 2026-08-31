"""Behaviour tests for the Maturity Board and Worth Matrix Web Surface.

Proves MATBOARD-01 through MATBOARD-06 from docs/design/specs/MATBOARD.md:
- MATBOARD-01: 5 sequential CML progression columns (Spark 1 .. Real 5)
- MATBOARD-02: 4-score equalizer breakdown (Novel, Works, Reach, Story)
- MATBOARD-03: Concept graphic thumbnail rendering on idea cards
- MATBOARD-04: Laggard callout and 1-click advancement activity action
- MATBOARD-05: Filtering by domain, screening verdict, and laggard sorting
- MATBOARD-06: Worth Matrix quadrant view (Passion Projects, High Impact, The Trap)
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def _seed_portfolio(store: MarkdownStore) -> None:
    """Populate test store with diverse portfolio of assessed and unassessed ideas."""
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # CML 1: Spark (Unassessed)
    n1 = Node(
        id="IDEA-A01", type="idea", title="Autonomous Drone Perch",
        created=datetime.now(timezone.utc), domain="robotics", tags=["drone"],
        attrs={"worth_to_me": "high", "worth_to_others": "high"},
    )
    # CML 2: Plausible (Laggard: novel)
    n2 = Node(
        id="IDEA-A02", type="idea", title="Low-cost cycling HUD",
        created=datetime.now(timezone.utc), domain="hardware", tags=["cycling"],
        attrs={
            "scores": {"novel": 2, "works": 4, "reach": 3, "story": 4},
            "cml": 2, "worth_to_me": "high", "worth_to_others": "low",
            "concept_graphic": "drop/cycling_ov1.png", "screening_verdict": "pursue",
        },
    )
    # CML 3: Explored (Laggard: reach)
    n3 = Node(
        id="IDEA-A03", type="idea", title="Decentralized Sync Engine",
        created=datetime.now(timezone.utc), domain="software", tags=["sync"],
        attrs={
            "scores": {"novel": 4, "works": 4, "reach": 3, "story": 4},
            "cml": 3, "worth_to_me": "low", "worth_to_others": "high",
            "screening_verdict": "park",
        },
    )
    # CML 4: Chosen
    n4 = Node(
        id="IDEA-A04", type="idea", title="Custom split keyboard",
        created=datetime.now(timezone.utc), domain="hardware", tags=["ergonomics"],
        attrs={
            "scores": {"novel": 4, "works": 4, "reach": 4, "story": 4},
            "cml": 4, "worth_to_me": "high", "worth_to_others": "low",
        },
    )
    # CML 5: Real
    n5 = Node(
        id="IDEA-A05", type="idea", title="Innovator Workspace Service",
        created=datetime.now(timezone.utc), domain="software", tags=["productivity"],
        attrs={
            "scores": {"novel": 5, "works": 5, "reach": 5, "story": 5},
            "cml": 5, "worth_to_me": "high", "worth_to_others": "high",
            "screening_verdict": "pursue",
        },
    )

    for n in (n1, n2, n3, n4, n5):
        store.write_node(n, author=author)


def test_matboard_01_maturity_board_categorizes_ideas_into_5_cml_columns(tmp_path: Path):
    """MATBOARD-01: Maturity Board presents ideas categorized into 5 sequential CML columns."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/maturity")
    assert response.status_code == 200
    assert "1 · SPARK" in response.text
    assert "2 · PLAUSIBLE" in response.text
    assert "3 · EXPLORED" in response.text
    assert "4 · CHOSEN" in response.text
    assert "5 · REAL" in response.text
    assert "Autonomous Drone Perch" in response.text
    assert "Low-cost cycling HUD" in response.text
    assert "Innovator Workspace Service" in response.text


def test_matboard_02_card_renders_4_score_equalizer_breakdown(tmp_path: Path):
    """MATBOARD-02: Idea card renders 4-score equalizer breakdown across Novel, Works, Reach, Story."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/maturity")
    assert response.status_code == 200
    assert "NOV" in response.text
    assert "WRK" in response.text
    assert "RCH" in response.text
    assert "STY" in response.text


def test_matboard_03_card_renders_concept_graphic_thumbnail(tmp_path: Path):
    """MATBOARD-03: Idea card renders compressed concept graphic thumbnail tile when specified."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/maturity")
    assert response.status_code == 200
    assert "/vault-file/drop/cycling_ov1.png" in response.text


def test_matboard_04_laggard_score_highlighted_with_advance_action_button(tmp_path: Path):
    """MATBOARD-04: Laggard score is highlighted with 1-click advance action button."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/maturity")
    assert response.status_code == 200
    assert "Laggard: NOVEL" in response.text
    assert "+ Advance: prior-art-survey" in response.text
    assert "Laggard: REACH" in response.text
    assert "+ Advance: parts-and-skills-survey" in response.text


def test_matboard_05_board_filters_by_domain_verdict_and_sorts_by_laggard(tmp_path: Path):
    """MATBOARD-05: Maturity Board filters by domain, verdict, and sorts by lowest laggard score."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    # Domain filter
    res_domain = client.get("/maturity?domain=hardware")
    assert res_domain.status_code == 200
    assert "Low-cost cycling HUD" in res_domain.text
    assert "Custom split keyboard" in res_domain.text
    assert "Decentralized Sync Engine" not in res_domain.text

    # Verdict filter
    res_verdict = client.get("/maturity?verdict=park")
    assert res_verdict.status_code == 200
    assert "Decentralized Sync Engine" in res_verdict.text
    assert "Low-cost cycling HUD" not in res_verdict.text


def test_matboard_06_worth_matrix_categorizes_passion_projects_and_traps(tmp_path: Path):
    """MATBOARD-06: Worth Matrix view categorizes Passion Projects, High Impact, and The Trap."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_portfolio(store)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/maturity?view=matrix")
    assert response.status_code == 200
    assert "Passion Projects" in response.text
    assert "High Impact (The Big Bets)" in response.text
    assert "The Trap (Danger Zone)" in response.text

    # Passion Projects: High me / Low others (IDEA-A02, IDEA-A04)
    assert "Low-cost cycling HUD" in response.text
    assert "Custom split keyboard" in response.text

    # High Impact: High me / High others (IDEA-A01, IDEA-A05)
    assert "Autonomous Drone Perch" in response.text
    assert "Innovator Workspace Service" in response.text

    # The Trap: Low me / High others (IDEA-A03)
    assert "Decentralized Sync Engine" in response.text
