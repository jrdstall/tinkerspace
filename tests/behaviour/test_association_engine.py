"""Behaviour tests for Association Pipeline, Adversarial Judge, and Template Dispatch.

Proves ASSOC-01 through ASSOC-08 from docs/design/specs/ASSOC.md:
- ASSOC-01: Two-stage creativity synthesis over candidate pairs
- ASSOC-02: Stage 1 Mechanism Abstraction
- ASSOC-03: Stage 2 Third-Domain Transfer
- ASSOC-04: Adversarial Judge refutation pass and strongest objection
- ASSOC-05: Association-study activity template schema
- ASSOC-06 & ASSOC-07: Deliverable markdown parsing and metadata preservation
- ASSOC-08: Idea creation with derived_from lineage and event audit logging
"""

from datetime import datetime, timezone
from pathlib import Path
import yaml

from iw.contracts.association import DistilledRecord, PairCandidate
from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.association.judge import build_association_prompt, parse_deliverable_to_proposal
from iw.domain.association.pipeline import AssociationPipeline


def _setup_engine_store(tmp_path: Path) -> tuple[MarkdownStore, AssociationPipeline, PairCandidate]:
    """Setup store, pipeline, and test candidate pair."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    pipeline = AssociationPipeline(store=store)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    f1 = Node(
        id="FRI-A01", type="friction", title="Bike computer battery freezes",
        created=datetime.now(timezone.utc), domain="hardware", tags=["cycling"],
    )
    a1 = Node(
        id="AST-A01", type="asset", title="Ultrasonic transducer rig",
        created=datetime.now(timezone.utc), domain="acoustics", tags=["audio"],
    )
    store.write_node(f1, author=author)
    store.write_node(a1, author=author)

    rec_a = DistilledRecord(id="FRI-A01", title=f1.title, type="friction", domain="hardware", tags=["cycling"])
    rec_b = DistilledRecord(id="AST-A01", title=a1.title, type="asset", domain="acoustics", tags=["audio"])
    candidate = PairCandidate(pair_id="PAIR-01", node_a=rec_a, node_b=rec_b, strategy="anti_similar", distance_metric=0.85)

    return store, pipeline, candidate


def test_assoc_01_two_stage_pipeline_synthesizes_proposal(tmp_path: Path):
    """ASSOC-01: Two-stage creativity synthesis over pair candidate."""
    _, pipeline, candidate = _setup_engine_store(tmp_path)
    proposal = pipeline.synthesize_proposal(candidate)

    assert proposal.id.startswith("PROP-")
    assert proposal.node_a_id == "FRI-A01"
    assert proposal.node_b_id == "AST-A01"
    assert proposal.sampler_strategy == "anti_similar"
    assert proposal.distance_metric == 0.85


def test_assoc_02_and_03_stage1_abstraction_and_stage2_transfer(tmp_path: Path):
    """ASSOC-02 & ASSOC-03: Stage 1 Abstract Mechanism and Stage 2 Third-Domain Transfer."""
    _, pipeline, candidate = _setup_engine_store(tmp_path)
    proposal = pipeline.synthesize_proposal(candidate)

    assert len(proposal.abstract_mechanism) > 10
    assert len(proposal.transfer_proposal) > 10
    assert proposal.target_domain != ""


def test_assoc_04_adversarial_judge_verdict_and_strongest_objection(tmp_path: Path):
    """ASSOC-04: Adversarial Judge evaluates proposal with verdict and strongest objection."""
    _, pipeline, candidate = _setup_engine_store(tmp_path)
    deliverable = (
        "---\n"
        "proposal_title: \"Acoustic boundary layer de-icer\"\n"
        "target_domain: \"aerospace\"\n"
        "abstract_mechanism: \"High-frequency vibration to prevent crystalline ice adhesion\"\n"
        "transfer_proposal: \"Apply ultrasonic surface waves to wing leading edges.\"\n"
        "strongest_objection: \"Power consumption of ultrasonic transducers exceeds thermal foil in flight.\"\n"
        "judge_verdict: \"keep\"\n"
        "confidence: 0.82\n"
        "---\n"
    )

    proposal = pipeline.synthesize_proposal(candidate, deliverable_text=deliverable)
    assert proposal.proposal_title == "Acoustic boundary layer de-icer"
    assert proposal.target_domain == "aerospace"
    assert proposal.judge_verdict == "keep"
    assert "Power consumption" in proposal.strongest_objection
    assert proposal.confidence == 0.82


def test_assoc_05_association_study_template_exists():
    """ASSOC-05: association-study@1 template exists and specifies required sections."""
    template_path = Path(__file__).resolve().parent.parent.parent / "content" / "templates" / "association-study.v1.yaml"
    assert template_path.is_file()

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "association-study@1"
    assert data["category"] == "generation"
    assert "abstract_mechanism" in data["deliverable_schema"]["required_sections"]
    assert "transfer_proposal" in data["deliverable_schema"]["required_sections"]
    assert "adversarial_judgment" in data["deliverable_schema"]["required_sections"]


def test_assoc_06_and_07_prompt_formatting_and_parsing(tmp_path: Path):
    """ASSOC-06 & ASSOC-07: Prompt generation and robust deliverable parsing."""
    _, _, candidate = _setup_engine_store(tmp_path)
    prompt = build_association_prompt(candidate)
    assert "PARENT A: [FRI-A01]" in prompt
    assert "PARENT B: [AST-A01]" in prompt
    assert "anti_similar" in prompt

    raw_text = "Plain text proposal with no yaml frontmatter describing a cross-domain acoustic thermal device."
    proposal = parse_deliverable_to_proposal("PROP-A99", raw_text, candidate)
    assert proposal.id == "PROP-A99"
    assert proposal.judge_verdict in ("keep", "discard")


def test_assoc_08_converting_kept_proposal_creates_idea_with_edges_and_events(tmp_path: Path):
    """ASSOC-08: Kept proposal promotes to Idea node with derived_from edges and event logging."""
    store, pipeline, candidate = _setup_engine_store(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    proposal = pipeline.synthesize_proposal(candidate, author=author)

    idea = pipeline.convert_proposal_to_idea(proposal, author=author)
    assert idea.id.startswith("IDEA-")
    assert idea.type == "idea"
    assert idea.attrs["derived_from"] == ["FRI-A01", "AST-A01"]

    # Verify derived_from edges
    derived_edges = [e for e in idea.edges if e.relation == "derived_from"]
    assert len(derived_edges) == 2
    target_ids = {e.to_id for e in derived_edges}
    assert target_ids == {"FRI-A01", "AST-A01"}

    # Verify event audit log
    events = store.event_log.read_events()
    proposed_evts = [e for e in events if e.kind == "association_proposed"]
    assert len(proposed_evts) >= 1
