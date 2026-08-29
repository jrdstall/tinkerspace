# STORE — Subsystem Behaviour Specifications

STORE-01  A node is one markdown file. Structured fields are YAML frontmatter; prose is the body.
STORE-02  Reading a node never caches. Every read hits the file on disk.
STORE-03  Writing a node modifies only the frontmatter keys supplied by the operation, preserving untouched frontmatter.
STORE-04  Writing a node preserves the existing markdown body unchanged unless an explicit body replacement is passed.
STORE-05  A write is atomic: write to a temporary file in the same directory/filesystem, then atomic rename into place.
STORE-06  A file whose YAML frontmatter fails to parse is recorded in a needs-attention list, never overwritten or auto-repaired.
STORE-07  A file whose frontmatter parses without an `id` or with an invalid `id` is quarantined in the needs-attention list.
STORE-08  Resolving an entity ID to a file scans frontmatter across the vault, never relying on filename or path patterns.
STORE-09  Renaming or moving a file within the vault breaks nothing, because all internal and external links reference node IDs.
STORE-10  A file arriving via sync or created by an external editor is treated identically to a file created by the IW service.
STORE-11  Every write initiated by the service requires an explicit author attribution structure (`author.kind` required).
STORE-12  Every successful write operation creates a local Git commit in the workstation repository; pushing commits to the remote is performed manually or on-demand.
STORE-13  The store exposes no filesystem watcher or background monitoring daemon; changes on disk are discovered upon read/scan.
STORE-14  ID allocation for a new node scans existing nodes of that prefix and returns the deterministic next sequence (`PREFIX-A01`).
STORE-15  ID allocation never reuses an ID that was previously allocated, even if the node is archived or deleted.
STORE-16  ID lookups are case-insensitive on input (`fri-a01` matches `FRI-A01`) and always formatted uppercase on write.
STORE-17  Work unit state is stored in structured `unit.yaml` inside `work/UOW-xxx/`, not as a markdown node note.
STORE-18  Artifacts produced by a work unit are stored directly within the step's dedicated folder `work/UOW-xxx/`.
STORE-19  Sync conflict duplicate files (e.g., `.sync-conflict-*`) are flagged in the needs-attention list rather than merged silently.
STORE-20  Rebuilding the derived query index from store files is an idempotent, pure function producing identical index states.
