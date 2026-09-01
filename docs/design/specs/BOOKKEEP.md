# BOOKKEEP — Behaviour Specification

This specification defines the behavior of the Bookkeeper content-addressed storage (CAS) adapter in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §10, §14.14, §14.18, and `docs/design/DA-04-components.md`.

---

## BOOKKEEP — Behaviour

BOOKKEEP-01  Raw source files and binary artifacts are stored content-addressably by their SHA-256 hash digest.
BOOKKEEP-02  Storage is idempotent and immutable; storing identical content returns the same content ID without rewriting or corrupting the existing file.
BOOKKEEP-03  Retrieval by content ID returns the exact byte payload, metadata (size, MIME type, original filename), and readable file path.
BOOKKEEP-04  Derived renditions (e.g., extracted plain text, preview thumbnails, compressed variants) can be registered against a primary content ID and retrieved by rendition name.
BOOKKEEP-05  Accessing non-existent content IDs or renditions raises a clear `KeyError` or returns `None` without file system leaks.
