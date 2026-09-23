"""Master prompt and Action Guide composer for Units of Work.

Governed by Vision §14.8, DA-09 §08, DA-11, and DA-12.
"""

from pathlib import Path
from typing import Any

from iw.contracts.models import Node, UnitOfWork
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.context import (
    format_attachments_markdown,
    format_linked_notes_markdown,
    resolve_subject_attachments,
    resolve_subject_linked_notes,
)


def get_default_templates_dir() -> Path:
    """Resolve the default directory containing activity and master templates."""
    return Path(__file__).resolve().parent.parent.parent.parent / "content" / "templates"


def load_master_prompt_template(templates_dir: Path | None = None) -> str:
    """Load master prompt Markdown template from disk with safe fallback."""
    if templates_dir is not None:
        custom_file = templates_dir / "master-prompt.md"
        if custom_file.exists():
            try:
                return custom_file.read_text(encoding="utf-8")
            except Exception:
                pass

    default_file = get_default_templates_dir() / "master-prompt.md"
    if default_file.exists():
        try:
            return default_file.read_text(encoding="utf-8")
        except Exception:
            pass

    return (
        "# MISSION: {{ unit_title }} ({{ unit_id }})\n\n"
        "## 1. Operating Posture & Working Rules\n"
        "Adversarial, fact-based engineering scout.\n\n"
        "{{ subject_context }}"
        "## 3. Specific Task Instructions\n{{ task_instructions }}\n\n"
        "{{ custom_notes }}"
        "## 5. Required Deliverable Format & Schema\n```markdown\n<!--\nunit: {{ unit_id }}\nverdict: proceed\n-->\n```\n\n"
        "## 6. Submission Protocol\nPresent draft to Jared in chat before calling submit_result."
    )


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


def _format_subject_context(
    subject_node: Node | None,
    store: StoreProtocol | None = None,
    vault_dir: Path | None = None,
) -> str:
    """Format subject concept context section (Vision §14.8, WORKFLOW-07)."""
    if not subject_node:
        return ""
    tags_str = ", ".join(subject_node.tags) if subject_node.tags else "None"
    body_text = subject_node.body.strip() if subject_node.body else "No description provided."
    graphic_line = (
        f"- **Concept Graphic**: `{subject_node.attrs['concept_graphic']}`\n"
        if subject_node.attrs.get("concept_graphic")
        else ""
    )
    base = (
        "## 2. Subject Concept Context\n"
        f"- **ID**: {subject_node.id}\n"
        f"- **Title**: {subject_node.title}\n"
        f"- **Domain**: {subject_node.domain}\n"
        f"- **Tags**: {tags_str}\n"
        f"{graphic_line}"
        "- **Description**:\n"
        f"{body_text}\n\n"
    )

    if store is not None:
        attachments = resolve_subject_attachments(subject_node, store, vault_dir=vault_dir)
        att_md = format_attachments_markdown(attachments)
        linked_notes = resolve_subject_linked_notes(subject_node, store)
        notes_md = format_linked_notes_markdown(linked_notes)
        if att_md:
            base += att_md
        if notes_md:
            base += notes_md
    return base


def _format_custom_notes(custom_notes: str | None, task_instructions: str) -> str:
    """Format custom focus and constraints section if distinct from task."""
    if not custom_notes or not custom_notes.strip():
        return ""
    if custom_notes.strip() == task_instructions.strip():
        return ""
    return f"## 4. Custom Focus & Constraints\n{custom_notes.strip()}\n\n"


def compose_full_prompt(
    unit_id: str,
    unit_title: str,
    task_instructions: str,
    subject_node: Node | None = None,
    custom_notes: str | None = None,
    templates_dir: Path | None = None,
    store: StoreProtocol | None = None,
    vault_dir: Path | None = None,
) -> str:
    """Compose the master prompt by replacing placeholders in master-prompt.md (WORKFLOW-07)."""
    if "Operating Posture" in task_instructions or "# MISSION:" in task_instructions:
        return task_instructions

    template_str = load_master_prompt_template(templates_dir)
    clean_subj = _format_subject_context(subject_node, store=store, vault_dir=vault_dir)
    clean_notes = _format_custom_notes(custom_notes, task_instructions)
    clean_task = task_instructions.strip() if task_instructions else "Execute assigned research."

    rendered = (
        template_str
        .replace("{{ unit_id }}", unit_id.upper())
        .replace("{{ unit_title }}", unit_title)
        .replace("{{ subject_context }}", clean_subj)
        .replace("{{ task_instructions }}", clean_task)
        .replace("{{ custom_notes }}", clean_notes)
    )
    return rendered.strip()


def attach_full_prompts_to_units(
    units: list[UnitOfWork],
    store: StoreProtocol,
    vault_dir: Path | None = None,
) -> None:
    """Precompute full composed prompts on unit objects for web surfaces (WORKFLOW-07)."""
    for u in units:
        subj = store.get_node(u.subject_ids[0]) if u.subject_ids else None
        setattr(u, "full_prompt", compose_full_prompt(
            unit_id=u.id,
            unit_title=u.title,
            task_instructions=u.action_guide,
            subject_node=subj,
            store=store,
            vault_dir=vault_dir,
        ))
