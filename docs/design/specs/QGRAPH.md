# QGRAPH — Behaviour Specification

This specification defines the behavior for the visual Question Graph surface and fast questioning interactions in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §12, §14.2, §14.8, and `docs/design/specs/QSTORM.md`.

---

## QGRAPH — Behaviour

QGRAPH-01  The Question Graph surface (`/question-graph/{subject_id}`) renders an interactive visual DAG of all question nodes attached to the subject.
QGRAPH-02  Question nodes are visually partitioned and categorized by form (Open Questions vs. Closed Questions).
QGRAPH-03  Question nodes reflect importance styling (High: prominent accent/amber, Medium: standard accent, Low: muted).
QGRAPH-04  Directed relationship indicators display question-to-question edge relationships (`broadens`, `narrows`, `presupposes`, `reframes`, `sibling`).
QGRAPH-05  An interactive quick-action interface enables creating new questions with Berger moves, transforming open <-> closed, and linking questions via HTMX without full page reload.
QGRAPH-06  Orphan questions and connected question chains are clearly distinguished in the visual graph layout.
QGRAPH-07  The Question Graph generates a Mermaid visual DAG diagram with view mode switching (Visual Graph, Split View, and Composer & Cards).

