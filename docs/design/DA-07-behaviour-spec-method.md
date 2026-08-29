---
id: DOC-DA-07
type: artifact
title: DA-07 · Behaviour Spec Method
date: 2026-08-29
domain: meta
tags: [specs, testing, traceability, acceptance]
---

# DA-07 · Behaviour Spec Method

**The mechanism for lightweight acceptance criteria, AI implementation boundaries, and zero-ceremony traceability.**

---

## 01 · The Purpose

The Innovator's Workspace is built by AI and reviewed by one human (Jared). We deliberately do not write heavy requirements specifications or maintain manual traceability matrices.

Instead, acceptance criteria are captured as **Behaviour Specs** — concise, numbered, testable imperative statements written in plain English.

---

## 02 · Spec Location and Format

1. **Location**: Subsystem specs live in `docs/design/specs/<SUBSYSTEM>.md` (e.g., `STORE.md`, `TRIAGE.md`, `WORKFLOW.md`, `MCP.md`).
2. **Format**: Each requirement is a single line starting with a fixed subsystem prefix and a 2-digit number:
   ```markdown
   ## STORE — Behaviour Specs

   STORE-01  A node is one markdown file. Structured fields are YAML frontmatter; prose is the body.
   STORE-02  Reading a node never caches. Every read hits the file on disk.
   STORE-03  Writing a node modifies only the frontmatter keys supplied by the operation.
   STORE-04  A write is atomic: write to a temp file, then atomic rename into place.
   ```

---

## 03 · The Three Traceability Rules

1. **Exactly Two Places**: Every spec ID appears in exactly two locations:
   - In its subsystem spec file (`docs/design/specs/<SUBSYSTEM>.md`).
   - In the name or docstring of the test proving it (e.g., `def test_store_04_atomic_write_uses_temp_file_rename():`).
2. **The Grep Trace**: Traceability is verified with a single command:
   ```bash
   grep -r "STORE-04" tests/
   ```
   No traceability spreadsheets, no matrix plugins. If grep finds the test, it is traced.
3. **The Scope-Creep Question**: During code review, any implementation code without a backing spec ID, or any spec ID without a test, triggers the question:
   > *"Which spec ID is this?"*
   If there is no spec ID, the code is removed or a spec ID is deliberately added.

---

## 04 · When Specs Are Authored

- Specs are **written per slice**, not all up front.
- Immediately before starting a slice, author the 15–30 behaviour lines for the subsystem.
- This prevents speculative requirement inflation and ensures specs match the immediate build slice.
