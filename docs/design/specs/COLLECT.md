# COLLECT — Subsystem Behaviour Specifications

COLLECT-01  Dispatching a human unit of work generates starter `deliverable.md` in `work/<UOW-id>/` with instruction comments and expected section headings.
COLLECT-02  Parsing deliverable extracts structured metadata from YAML frontmatter (`---`) or HTML comment blocks (`<!--`), and supports zero-header fallback.
COLLECT-03  Malformed headers gracefully degrade without raising unhandled exceptions, preserving the entire raw text as artifact prose and recording an attention notice.
COLLECT-04  Collection scans the unit folder and registers `ART-xxx` artifact nodes for all discovered files (Open Hospitality rule).
COLLECT-05  Attribution is stamped on collection with observed courier (`web-ui`) and asserted author details.
COLLECT-06  Evaluated scores in deliverable materialize into subject node `attrs['scores']` and recompute the derived `cml`.
COLLECT-07  Screening verdicts and summary materialize into subject node frontmatter and activity history.
COLLECT-08  Successful collection transitions unit state to `accepted`, unblocking ready successors in the workflow DAG.
