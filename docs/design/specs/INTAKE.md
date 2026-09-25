# INTAKE — Subsystem Behaviour Specifications

INTAKE-01  Files dropped into `iw-vault/drop/` (e.g. tablet sketches, PDFs) are discovered on request without background watchers.
INTAKE-02  Intake creates stub nodes with dropped files moved to `attachments/{node_id}/` and markdown embed links populated.
INTAKE-03  Intake attaches dropped files to existing mature nodes by moving files to `attachments/{node_id}/` and appending reference links to node body text.
INTAKE-04  The web intake interface lists dropped assets and provides workflows for stub creation, node attachment, and file discard.
INTAKE-05  Direct attachment of uploaded files or dropped files to a subject node creates an ART-xxx node with relative vault path in `attachments/{node_id}/` (moving any drop files) and links via directional edge.
INTAKE-06  In-context capturing of linked child ideas, observations, frictions, questions, and sources directly from a subject node surface with automatic ID allocation and graph relationship creation.
