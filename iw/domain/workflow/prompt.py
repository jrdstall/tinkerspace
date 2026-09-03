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


def _render_instructions(task_instructions: str, custom_notes: str | None) -> list[str]:
    """Render activity instructions and optional custom focus notes."""
    lines = [
        "## 3. Specific Task Instructions",
        task_instructions.strip() if task_instructions else "Execute the assigned research and analysis.",
        "",
    ]
    if custom_notes and custom_notes.strip() and custom_notes.strip() != task_instructions.strip():
        lines.extend(["## 4. Custom Focus & Constraints", custom_notes.strip(), ""])
    return lines


def _render_deliverable_schema(unit_id: str, unit_title: str) -> list[str]:
    """Render required deliverable format and YAML/comment metadata header block."""
    header_template = build_deliverable_header_template(unit_id)
    return [
        "## 5. Required Deliverable Format & Schema",
        "Author your final report in Markdown. You MUST include the following metadata comment header block at the very top of your deliverable report so Tinkerspace can automatically evaluate findings and advance concept maturity scores:",
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
        "",
    ]


def _render_submission_instructions(unit_id: str) -> list[str]:
    """Render explicit submission instructions for both MCP agents and interactive chat."""
    u_id = unit_id.upper()
    return [
        "## 6. How to Submit Your Results",
        "",
        "### A. If You Have MCP Tool Access (Claude Desktop / Antigravity IDE):",
        f"Once your analysis is complete, submit your work by calling the `submit_result` MCP tool:",
        f"- `unit_id`: \"{u_id}\"",
        "- `deliverable`: The full Markdown report string (including the metadata comment header block at the top).",
        "- `model_name`: Your declared model identifier (e.g. 'claude-3-5-sonnet', 'claude-3-7-sonnet').",
        "- `artifacts`: (Optional) list of companion files as `[{\"filename\": \"data.csv\", \"content\": \"...\"}]`.",
        "",
        f"Calling `submit_result` automatically saves `deliverable.md` into `vault/work/{u_id}/` and moves the unit to `returned` state for Jared's review.",
        "",
        "### B. If You Are in an Interactive Chat (Web Claude / ChatGPT):",
        f"Output the complete Markdown report (with the metadata header block) in your chat response. Jared will save it to `vault/work/{u_id}/deliverable.md` and click [Collect / Complete] on the Work Board.",
    ]


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
    lines.extend(_render_instructions(task_instructions, custom_notes))
    lines.extend(_render_deliverable_schema(unit_id, unit_title))
    lines.extend(_render_submission_instructions(unit_id))
    return "\n".join(lines)
