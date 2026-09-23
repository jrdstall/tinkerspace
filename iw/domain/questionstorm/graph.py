"""Mermaid Question Graph visualizer.

Layer 2 Domain module. Depends only on iw.contracts.models and stdlib.
Governed by Vision §12 and QGRAPH-01.
"""

import textwrap
from iw.contracts.models import Node


def _format_mermaid_text(text: str, max_line_width: int = 36) -> str:
    """Format node text for Mermaid: sanitize quotes and word-wrap without truncation."""
    cleaned = text.replace('"', "'").replace("<", "&lt;").replace(">", "&gt;").strip()
    paragraphs = cleaned.splitlines()
    wrapped_lines: list[str] = []
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        wrapped = textwrap.wrap(p_clean, width=max_line_width, break_long_words=True)
        wrapped_lines.extend(wrapped)
    return "<br/>".join(wrapped_lines) if wrapped_lines else cleaned


def _format_move_label(move: str | None) -> str:
    if not move or str(move).lower() in ("custom", "blank", "none", ""):
        return ""
    labels = {
        "why": "Why", "why_must_it_be": "Why Must It Be",
        "question_the_question": "Assumptions", "constraint_removal": "Constraint",
        "inversion": "Inversion", "how_might_we": "How",
        "dissenter": "Dissenter", "open_closed": "Transform",
    }
    return labels.get(str(move).lower(), str(move).replace("_", " ").title())


def _render_question_nodes(questions: list[Node]) -> tuple[list[str], set[str]]:
    lines: list[str] = []
    has_parent: set[str] = set()
    for q in questions:
        form = q.attrs.get("form", "open")
        move_label = _format_move_label(q.attrs.get("move"))
        move_suffix = f" ({move_label})" if move_label else ""
        icon = "🌌" if form == "open" else "🎯"
        q_title = _format_mermaid_text(q.title, 36)
        node_id = q.id.replace("-", "_")
        css_class = "closedNode" if form == "closed" else "openNode"
        if q.attrs.get("importance") == "high":
            css_class += " highImp"
        lines.append(f'  {node_id}["{icon} <b>{q.id}</b>{move_suffix}<br/>{q_title}"]:::{css_class}')

    for q in questions:
        q_node_id = q.id.replace("-", "_")
        for e in q.edges:
            if e.relation != "questions":
                to_node_id = e.to_id.replace("-", "_")
                has_parent.add(q.id)
                lines.append(f"  {to_node_id} -->|{e.relation}| {q_node_id}")
    return lines, has_parent


def generate_mermaid_graph(subject: Node, questions: list[Node]) -> str:
    """Generate Mermaid flowchart diagram representing the question DAG."""
    sub_title = _format_mermaid_text(subject.title, 36)
    lines = ["graph TD", f'  SUB["💡 <b>{subject.id}</b><br/>{sub_title}"]:::subjectNode']
    if not questions:
        lines.extend(['  EMPTY["No questions in graph yet"]:::emptyNode', "  SUB -.-> EMPTY"])
    else:
        q_lines, has_parent = _render_question_nodes(questions)
        lines.extend(q_lines)
        for q in questions:
            if q.id not in has_parent:
                lines.append(f"  SUB -->|questions| {q.id.replace('-', '_')}")

    lines.extend([
        "  classDef subjectNode fill:#1f293d,stroke:#58a6ff,stroke-width:2px,color:#e6edf3;",
        "  classDef openNode fill:#16243b,stroke:#388bfd,stroke-width:1.5px,color:#e6edf3;",
        "  classDef closedNode fill:#1b2f24,stroke:#3fb950,stroke-width:1.5px,color:#e6edf3;",
        "  classDef highImp stroke:#f0883e,stroke-width:2.5px;",
        "  classDef emptyNode fill:#161b22,stroke:#30363d,stroke-dasharray: 5 5,color:#8b949e;",
    ])
    return "\n".join(lines)
