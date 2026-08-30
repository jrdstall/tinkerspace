"""Deliverable parsing, result collection pipeline, and subject fact materialization.

Implements DA-12 deliverable parsing with graceful degradation and V§14.15 subject note materialization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
import yaml

from iw.contracts.models import Author, Edge, Node, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.state import transition_unit_state

YAML_FM_REGEX = re.compile(r"^---\s*\r?\n(.*?)\r?\n(?:---|\.\.\.)\s*\r?\n(.*)$", re.DOTALL)
HTML_COMMENT_REGEX = re.compile(r"^\s*<!--\s*\r?\n(.*?)\r?\n-->\s*\r?\n(.*)$", re.DOTALL)


@dataclass
class ArtifactRef:
    """Reference to an artifact declared in deliverable header."""
    file: str
    role: str = "output"
    description: str = ""


@dataclass
class DeliverableHeader:
    """Parsed structured metadata from deliverable header."""
    unit: str
    summary: str = ""
    verdict: str | None = None
    scores: dict[str, int] = field(default_factory=dict)
    recommendation: str | None = None
    artifacts: list[ArtifactRef] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    parse_warning: str | None = None


def parse_artifact_entries(raw_arts: Any) -> list[ArtifactRef]:
    """Parse list of strings or dicts into ArtifactRef objects."""
    result: list[ArtifactRef] = []
    if isinstance(raw_arts, list):
        for item in raw_arts:
            if isinstance(item, str) and item.strip():
                result.append(ArtifactRef(file=item.strip(), role="output", description=""))
            elif isinstance(item, dict) and "file" in item:
                result.append(ArtifactRef(
                    file=str(item["file"]).strip(),
                    role=str(item.get("role", "output")).lower().strip(),
                    description=str(item.get("description", "")).strip(),
                ))
    return result


def parse_deliverable_text(raw_text: str, default_unit_id: str) -> tuple[DeliverableHeader, str]:
    """Parse header and body from deliverable markdown text with zero exceptions (COLLECT-02, 03)."""
    match_yaml = YAML_FM_REGEX.match(raw_text)
    match_comment = HTML_COMMENT_REGEX.match(raw_text) if not match_yaml else None
    if match_yaml:
        header_raw, body = match_yaml.group(1), match_yaml.group(2)
    elif match_comment:
        header_raw, body = match_comment.group(1), match_comment.group(2)
    else:
        return DeliverableHeader(unit=default_unit_id.upper()), raw_text

    try:
        data = yaml.safe_load(header_raw)
        if not isinstance(data, dict):
            return DeliverableHeader(unit=default_unit_id.upper(), parse_warning="Header not dict"), raw_text
    except Exception as exc:
        return DeliverableHeader(unit=default_unit_id.upper(), parse_warning=str(exc)), raw_text

    scores: dict[str, int] = {}
    if isinstance(data.get("scores"), dict):
        for k, v in data["scores"].items():
            if isinstance(v, (int, str)) and str(v).isdigit() and 1 <= int(v) <= 5:
                scores[str(k).lower()] = int(v)

    header = DeliverableHeader(
        unit=str(data.get("unit", default_unit_id)).upper(),
        summary=str(data.get("summary", "")).strip(),
        verdict=str(data["verdict"]).lower().strip() if data.get("verdict") is not None else None,
        scores=scores,
        recommendation=str(data.get("recommendation", "")).strip() if data.get("recommendation") else None,
        artifacts=parse_artifact_entries(data.get("artifacts")),
        tags=[str(t).strip() for t in data.get("tags", []) if isinstance(t, str)],
    )
    return header, body


def generate_human_starter_template(unit: UnitOfWork, folder_path: Path) -> Path:
    """Generate starter deliverable.md with headings and action instructions (COLLECT-01)."""
    folder_path.mkdir(parents=True, exist_ok=True)
    target_file = folder_path / "deliverable.md"
    if target_file.exists():
        return target_file

    header_block = (
        f"<!--\nunit: {unit.id.upper()}\nsummary: \"\"\nscores:\n  works: 1\n-->\n\n"
        f"# {unit.title}\n\n## Executive Summary\n\n## Options & Trade-Offs\n\n## Recommendation\n"
    )
    target_file.write_text(header_block, encoding="utf-8")
    return target_file


def _register_folder_artifacts(folder: Path, unit: UnitOfWork, body: str, store: StoreProtocol, author: Author) -> list[Node]:
    """Scan folder and register all output files as ART-xxx nodes (COLLECT-04, 05)."""
    arts: list[Node] = []
    now = datetime.now(timezone.utc)
    for item in folder.iterdir():
        if item.name.lower() == "unit.yaml":
            continue
        art_id = store.allocate_id("ART")
        edge = Edge(from_id=art_id, to_id=unit.id, relation="produced_by", created=now, author=author, note=item.name)
        art_node = Node(
            id=art_id,
            type="artifact",
            title=f"{item.name} for {unit.id}",
            created=now,
            domain="artifacts",
            tags=["artifact"],
            body=body if item.name.lower() == "deliverable.md" else f"File output: `work/{unit.id}/{item.name}`",
            edges=[edge],
            attrs={"file_name": item.name, "path": f"work/{unit.id}/{item.name}", "unit": unit.id},
        )
        arts.append(store.write_node(art_node, author=author))
    return arts


def _materialize_to_subject(store: StoreProtocol, subject_id: str, header: DeliverableHeader, art_nodes: list[Node], unit: UnitOfWork, author: Author) -> None:
    """Materialize evaluated scores, CML, verdicts, and artifact edges onto subject note (COLLECT-06, 07)."""
    subject = store.get_node(subject_id)
    if not subject:
        return
    now = datetime.now(timezone.utc)

    if header.scores:
        subject.attrs.setdefault("scores", {}).update(header.scores)
        vals = [int(v) for v in subject.attrs["scores"].values() if isinstance(v, (int, float))]
        if vals:
            subject.attrs["cml"] = min(vals)

    if header.verdict:
        subject.attrs["screening_verdict"] = header.verdict
    if header.summary:
        history = list(subject.attrs.get("activity_log", []))
        history.append(f"{now.date()}: {unit.activity} ({unit.id}) - {header.summary}")
        subject.attrs["activity_log"] = history

    edge_targets = {e.to_id.upper() for e in subject.edges}
    for art in art_nodes:
        if art.id.upper() not in edge_targets:
            edge = Edge(from_id=subject.id, to_id=art.id.upper(), relation="illustrates", created=now, author=author, note=f"Produced by {unit.id}")
            subject.edges.append(edge)

    store.write_node(subject, author=author)


def collect_unit_results(store: StoreProtocol, unit_id: str, author: Author) -> tuple[UnitOfWork, list[Node]]:
    """Scan work folder, parse deliverable, register artifacts, materialize facts, and accept unit (COLLECT-04..08)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        raise ValueError(f"Unit '{clean_id}' does not exist")

    vault_dir = getattr(store, "vault_dir", None)
    unit_folder = (vault_dir / "work" / clean_id) if vault_dir else None
    if not unit_folder or not unit_folder.exists():
        raise ValueError(f"Work folder for '{clean_id}' does not exist")

    deliverable_file = unit_folder / "deliverable.md"
    raw_text = deliverable_file.read_text(encoding="utf-8") if deliverable_file.exists() else ""
    header, body = parse_deliverable_text(raw_text, default_unit_id=clean_id)

    created_artifacts = _register_folder_artifacts(unit_folder, unit, body, store, author)

    for sub_id in unit.subject_ids:
        _materialize_to_subject(store, sub_id, header, created_artifacts, unit, author)

    if unit.state != UnitState.ACCEPTED:
        unit = transition_unit_state(unit, UnitState.ACCEPTED, author=author, store=store)

    return unit, created_artifacts
