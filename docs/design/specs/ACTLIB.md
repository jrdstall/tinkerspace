# ACTLIB — Behaviour Specification

This specification defines the schema, requirements, and library standards for Activity Templates in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §06, §10, §11, §14.7, and `docs/design/DA-11-activity-templates.md`.

---

## ACTLIB — Behaviour

ACTLIB-01  Each activity template is a versioned YAML document containing `id`, `title`, `version`, `category`, `target_output`, `description`, `prompt_instructions`, and `deliverable_schema`.
ACTLIB-02  The divergent generation template (`divergent-generation@1`) explicitly instructs workers to produce candidate architecture options without filtering or premature convergence.
ACTLIB-03  The convergent screening template (`convergent-screening@1`) requires rejection criteria to be established prior to evaluating candidates, and mandates recording a `rejected_because` edge for every screened-out option.
ACTLIB-04  The trade study template (`trade-study@1`) specifies weighted evaluation criteria, normalized option scoring, a sensitivity pass over the criteria weights, and a definitive recommendation.
ACTLIB-05  The point design (`point-design@1`) and parts-and-skills survey (`parts-and-skills-survey@1`) templates require costing in parts, hours, schedule, and currency, cross-referencing owned assets (`AST-xxx`).
ACTLIB-06  Discovery-driven and empirical templates (`assumption-audit@1`, `experiment-design@1`, `prototype-and-measure@1`, `heilmeier-screening@1`) require stating explicit test parameters, measurable metrics, and advance kill criteria.
ACTLIB-07  The prior-art survey template (`prior-art-survey@1`) and questionstorm template (`questionstorm@1`) define adversarial patent search and Berger inquiry arc instructions.

