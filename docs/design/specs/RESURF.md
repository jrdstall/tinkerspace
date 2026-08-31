# RESURF — Behaviour Specification

This specification defines the behavior for the Resurfacer Engine, Dormant Node Scoring, and Observation Sweep Workflows in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §13, §14.2, §14.8, §14.17, and `docs/design/DA-14-forward-compatibility.md`.

---

## RESURF — Behaviour

RESURF-01  The Resurfacer calculates a dormancy score based on time elapsed since `last_touched`, edge degree (unlinked/low-connectivity penalty), and domain neglect.
RESURF-02  Observation Sweep workflow (`observation-sweep@1`) aggregates unlinked observations and recommends cross-observation syntheses or links to known frictions.
RESURF-03  Dormant node scoring surfaces valuable assets, parked ideas, and isolated observations without manual tagging.
RESURF-04  The activity template `observation-sweep@1` in `content/templates/observation-sweep.v1.yaml` defines the structured deliverable schema for observation clustering.
RESURF-05  Resurfaced nodes support 1-click transition into active workflows or questionstorm sessions.
RESURF-06  Resurfacer sweeps and recommendation generation append audit events with author attribution to `events.jsonl`.
