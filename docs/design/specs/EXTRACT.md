# EXTRACT — Behaviour Specification

This specification defines the behavior of pluggable content and format extractors in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §10, §14.14, and `docs/design/DA-04-components.md`.

---

## EXTRACT — Behaviour

EXTRACT-01  The text extractor parses plain text, markdown, CSV, and YAML/JSON data into normalized text with structural metadata.
EXTRACT-02  The HTML extractor parses HTML content, strips script and style tags, extracts title/heading metadata, and outputs clean readable text.
EXTRACT-03  The PDF extractor extracts textual content and metadata from PDF files, degrading gracefully if text extraction is partial or unsupported.
EXTRACT-04  The image extractor extracts dimension and format metadata from image files (PNG, JPEG, SVG, WebP) and extracts readable text from SVGs.
EXTRACT-05  The extractor registry routes extraction requests by MIME type or file extension to the most specific registered extractor.
EXTRACT-06  Unsupported or unparseable binary formats return a structured extraction result with raw metadata and warnings without throwing unhandled exceptions.
