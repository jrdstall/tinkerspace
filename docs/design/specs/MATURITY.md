# MATURITY — Behaviour Specification

This specification defines the complete Concept Maturity Level (CML 1 to 5) advancement lifecycle, A-Team study discipline, and end-to-end maturation verification in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §06, §11, §14.8, §14.15, §16, and `docs/design/DA-03-data-model.md`.

---

## MATURITY — Behaviour

MATURITY-01  Every idea enters the store at CML 1 (Spark) and cleanly defaults to CML 1 even before explicit multi-criteria scores are recorded.
MATURITY-02  Advancing to CML 2 (Plausible) proves initial feasibility through prior-art landscape surveying (`prior-art-survey@1`) and DARPA Heilmeier catechism screening (`heilmeier-screening@1`).
MATURITY-03  Advancing to CML 3 (Explored) enforces JPL A-Team discipline: divergent generation of multiple candidate architectures without filtering (`divergent-generation@1`), pre-declared rejection criteria screening (`convergent-screening@1`), and recording `rejected_because` edges for screened-out options.
MATURITY-04  Advancing to CML 4 (Chosen) requires an architecture trade study with sensitivity analysis (`trade-study@1`), parts and skills survey against owned assets (`parts-and-skills-survey@1`), point design costing (`point-design@1`), and narrative pitch storytelling (`story-draft@1`).
MATURITY-05  Advancing to CML 5 (Real) requires decisive empirical verification: hypothesis and test design with advance kill criteria (`experiment-design@1`) followed by minimal prototype build and measurement (`prototype-and-measure@1`).
MATURITY-06  At every advancement gate, scores and derived CML (`min(novel, works, reach, story)`) are atomically persisted to note YAML frontmatter on disk with immutable author attribution and event log records.
