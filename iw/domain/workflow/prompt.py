"""Master prompt and Action Guide composer for Units of Work.

Governed by Vision §14.8, DA-09 §08, DA-11, and DA-12.
"""

from typing import Any
from iw.contracts.models import Node, UnitOfWork


def build_deliverable_header_template(unit_id: str) -> str:
    """Construct the required deliverable metadata header template."""
    return (
        "<!--\n"
        f"unit: {unit_id.upper()}\n"
        'summary: "<1-2 sentence core finding: key discovery, trade-off, or verdict>"\n'
        "verdict: proceed\n"
        "scores:\n"
        "  novel: 3\n"
        "  works: 3\n"
        "-->"
    )


def _render_header_and_rules(unit_id: str, unit_title: str) -> list[str]:
    """Render mission header and operational rules for the agent."""
    return [
        f"# MISSION: {unit_title} ({unit_id.upper()})",
        "",
        "## 1. Operating Posture & Working Rules",
        "You are an expert technology scout, systems architect, and senior engineering partner assisting Jared in his personal innovation workspace (Tinkerspace).",
        "- **Adversarial & Objective**: Do not act as a cheerleader. Stress-test assumptions, search for genuine blockers, and identify prior art or failure modes.",
        "- **Fact-Based & Verifiable**: Cite real patent numbers (USPTO/EPO/WIPO), commercial product models, component datasheets, or academic papers. Never fabricate citations.",
        "- **Cheap & Decisive**: Aim for high information gain per unit of effort.",
        "",
    ]


def _render_subject_context(subject_node: Node | None) -> list[str]:
    """Render subject node metadata and description block."""
    if not subject_node:
        return []
    tags_str = ", ".join(subject_node.tags) if subject_node.tags else "None"
    body_text = subject_node.body.strip() if subject_node.body else "No description provided."
    return [
        "## 2. Subject Concept Context",
        f"- **ID**: {subject_node.id}",
        f"- **Title**: {subject_node.title}",
        f"- **Domain**: {subject_node.domain}",
        f"- **Tags**: {tags_str}",
        "- **Description**:",
        body_text,
        "",
    ]


def _render_instructions_and_schema(
    unit_id: str,
    unit_title: str,
    task_instructions: str,
    custom_notes: str | None,
) -> list[str]:
    """Render activity instructions, custom focus, and deliverable format schema."""
    lines = [
        "## 3. Specific Task Instructions",
        task_instructions.strip() if task_instructions else "Execute the assigned research and analysis.",
        "",
    ]
    if custom_notes and custom_notes.strip() and custom_notes.strip() != task_instructions.strip():
        lines.extend(["## 4. Custom Focus & Constraints", custom_notes.strip(), ""])

    header_template = build_deliverable_header_template(unit_id)
    lines.extend([
        "## 5. Required Deliverable Format & Schema",
        "Author your final report in Markdown. You MUST include the following metadata comment header block at the top so Tinkerspace can automatically evaluate findings and advance concept maturity scores:",
        "",
        "```markdown",
        header_template,
        "",
        f"# {unit_title}",
        "",
        "## Executive Summary",
        "...",
        "",
        "## Detailed Analysis & Findings",
        "...",
        "",
        "## Recommendations & Next Steps",
        "...",
        "```",
    ])
    return lines


def compose_full_prompt(
    unit_id: str,
    unit_title: str,
    task_instructions: str,
    subject_node: Node | None = None,
    custom_notes: str | None = None,
) -> str:
    """Compose the master prompt containing general guidance, subject context, and task schema."""
    if "Operating Posture" in task_instructions or "# MISSION:" in task_instructions:
        return task_instructions

    lines = _render_header_and_rules(unit_id, unit_title)
    lines.extend(_render_subject_context(subject_node))
    lines.extend(_render_instructions_and_schema(unit_id, unit_title, task_instructions, custom_notes))
    return "\n".join(lines)
