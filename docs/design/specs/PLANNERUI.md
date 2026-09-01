# PLANNERUI — Behaviour Specification

This specification defines the behavior of the Web UI surfaces for the Maturation Planner and Scout Recommended Activities.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §07, §08, §10, §11, and `docs/design/DA-06-ui-map.md`.

---

## PLANNERUI — Behaviour

PLANUI-01  The Maturation Planner view (`/ideas/{idea_id}/plan`) displays the idea's current CML, four maturity scores, identified laggards, and a target CML selector.
PLANUI-02  Selecting a target CML previews the ordered maturation steps with assignees, sizes, durations, and dependency links.
PLANUI-03  Submitting the plan form instantiates a `WFL-xxx` workflow on disk and redirects to `/workflows/{wfl_id}`.
PLANUI-04  The Recommended Activities panel renders all stale Scout standing interest offers with days-stale counters and direct action buttons.
PLANUI-05  Interacting with a Scout offer provides two one-click actions: "Dismiss" (resets staleness clock) and "Raise Sweep Order" (instantiates an observation sweep workflow and resets the clock).
PLANUI-06  The Custom Plan Builder UI allows Jared to author a plan from scratch, dynamically adding steps from the full activity library or freeform tasks.
PLANUI-07  Custom steps allow configuring title, template/activity ID, assignee (`human`, `agent`, `tool`), estimated hours, size (`small`, `medium`, `large`), and upstream step dependencies.
