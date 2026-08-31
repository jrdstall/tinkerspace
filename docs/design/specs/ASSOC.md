# ASSOC — Behaviour Specification

This specification defines the behavior for the Two-Stage Association Pipeline, Activity Template Dispatch, and Adversarial Judge Evaluation in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §13, §14.2, §14.8, §14.17, and `docs/design/DA-14-forward-compatibility.md` Audits 3, 5.

---

## ASSOC — Behaviour

ASSOC-01  An association run processes a candidate pair (`node_a` and `node_b`) through a two-stage creativity synthesis pipeline.
ASSOC-02  **Stage 1 (Mechanism Abstraction)** extracts the core structural mechanism shared between the two nodes in abstract terms belonging to neither domain.
ASSOC-03  **Stage 2 (Third-Domain Transfer)** instantiates the abstract mechanism into a concrete idea proposal within a third domain.
ASSOC-04  The Adversarial Judge evaluates the generated proposal through a refutation lens, outputting a structured verdict (`"keep"` or `"discard"`), confidence score, and the `strongest_objection`.
ASSOC-05  The activity template `association-study@1` in `content/templates/association-study.v1.yaml` specifies prompt instructions and deliverable formatting for AI couriers.
ASSOC-06  Association proposals preserve full provenance metadata (parent node IDs, abstract mechanism, transfer proposal, judge verdict, strongest objection, sampler strategy, distance metric).
ASSOC-07  The association parser extracts structured deliverable fields from result markdown while gracefully handling missing optional fields.
ASSOC-08  Association execution logs audit events with author attribution to `events.jsonl`.
