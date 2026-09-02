"""Mermaid Question Graph visualizer.

Layer 2 Domain module. Depends only on iw.contracts.models and stdlib.
Governed by Vision §12 and QGRAPH-01.
"""

from iw.contracts.models import Node


def _sanitize(text: str, max_len: int = 40) -> str:
    cleaned = text.replace('"', "'").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;").strip()
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "..."
    return cleaned


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
        q_title = _sanitize(q.title, 35)
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
    lines = ["graph TD", f'  SUB["💡 <b>{subject.id}</b><br/>{_sanitize(subject.title, 45)}"]:::subjectNode']
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
