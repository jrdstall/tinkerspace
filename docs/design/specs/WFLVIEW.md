# WFLVIEW — Subsystem Behaviour Specifications

WFLVIEW-01  The Workflow View (`/workflow/{workflow_id}`) renders a visual dependency DAG diagram of all units in the workflow.
WFLVIEW-02  Workflow step nodes display explicit lifecycle status color-coding (ready = green, dispatched = blue, returned = orange, accepted = slate, blocked = dimmed).
WFLVIEW-03  Step nodes render dependency connectors showing predecessor-to-successor execution flow.
WFLVIEW-04  Each step node provides interactive action controls (Dispatch, Skip, Park, Reset) and links to subject nodes.
