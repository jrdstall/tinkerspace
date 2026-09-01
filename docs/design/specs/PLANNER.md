# PLANNER — Behaviour Specification

This specification defines the behavior of the Maturation Planner domain service in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §05, §06, §10, §11, and `docs/design/DA-09-uow-lifecycle.md`.

---

## PLANNER — Behaviour

PLANNER-01  The Planner supports both automated baseline plan generation and custom human plan authoring from scratch for an idea.
PLANNER-02  Automated step sequencing strictly enforces "cheap and decisive first" (e.g., prior-art surveys and screening catecheses precede trade studies; trade studies precede detailed point designs).
PLANNER-03  Every proposed plan step is sized for single-session execution (1–2 hours) with explicit size tags (`small` or `medium`).
PLANNER-04  Steps declare upstream dependencies (`depends_on`), generating a clean directed acyclic graph (DAG).
PLANNER-05  The Planner directly targets identified score laggards (`novel`, `works`, `reach`, `story`) to lift the idea's Concept Maturity Level (`min(scores)`).
PLANNER-06  A drafted maturation plan is a proposal that can be edited (steps added, customized, reordered, or removed) prior to execution.
PLANNER-07  Instantiating a plan creates a structured `Workflow` (`WFL-xxx`) containing concrete `UnitOfWork` entities (`UOW-xxx`) with on-disk `unit.yaml` and `workflow.yaml` state.
PLANNER-08  Target CML 5 plans include empirical validation activities (`experiment-design@1`, `prototype-and-measure@1`) with advance kill criteria.
PLANNER-09  The Planner exposes the full library of available activity templates (`content/templates/`) and generic `freeform@1` activities as selectable building blocks for custom plan construction.
PLANNER-10  A custom maturation plan can be assembled directly by the human user with custom step titles, activity selection, assignees (`human`, `agent`, `tool`), durations, and dependency sequences.
