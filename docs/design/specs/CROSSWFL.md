# CROSSWFL — Subsystem Behaviour Specifications

CROSSWFL-01  Workflow steps can declare cross-workflow dependencies on units in other workflows.
CROSSWFL-02  A workflow can declare whole-workflow dependencies on other workflows, blocking all of its steps until the upstream workflow is fully completed.
CROSSWFL-03  Global multi-workflow DAG validation checks for cross-workflow cycles and rejects circular dependency graphs across workflows.
CROSSWFL-04  On-demand ready-set computation evaluates cross-workflow dependencies without background watchers.
CROSSWFL-05  Accepting or skipping prerequisite units in upstream workflows unblocks ready units in downstream workflows.
