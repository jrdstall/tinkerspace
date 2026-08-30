# WORKFLOW — Subsystem Behaviour Specifications

WORKFLOW-01  A workflow is a directed acyclic graph (DAG) of dependency-linked units of work stored in structured `work/<WFL-id>/workflow.yaml`.
WORKFLOW-02  Workflow instantiation initializes root units with zero predecessors as `ready` and dependent units as `blocked`.
WORKFLOW-03  `compute_ready_set` evaluates all unblocked units whose predecessors are `accepted` or `skipped`, computed on demand without background watchers.
WORKFLOW-04  Accepting or skipping a predecessor unblocks downstream successors upon subsequent ready-set evaluation.
WORKFLOW-05  Workflow DAG validation detects and rejects cyclic dependencies with a descriptive error.
WORKFLOW-06  Workflow writes and state unblocking require explicit author attribution and emit audit event log records.
