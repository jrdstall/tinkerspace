# AGENTS.md — Canonical AI Engineering Guidelines

This repository is **Tinkerspace (Innovator's Workspace)**, a personal idea maturation tool for Jared.
Jared is the project lead (experienced Java/C/C++ engineer). AI agents author Python code under his review.

---

## 01 · Core Operating Posture
- **Personal Tool, Usability First**: Design for frictionless single-user daily use, clear UI (HTMX/Jinja2), and fast desktop performance. Avoid premature enterprise multi-user abstractions.
- **Push Back Proactively**: If an instruction is inefficient, over-complicated, or if there is a cleaner/better pattern, explicitly propose it. The quality and usability of the tool takes precedence over agreement.
- **Task Status Rule**: AI may set tasks to `in work`. **Only Jared sets a task to `done`** after reviewing running output.

---

## 02 · Python Coding Standards & Ban List
Jared reads Python through a Java/C/C++ lens. Code must be explicit, typed, and structured:
- **Explicit Type Hints**: Required on every public function, method, and return value.
- **No Metaclasses or Dynamic Magic**: No `__getattr__`/`__setattr__` tricks, no `importlib` or dynamic imports.
- **No Monkeypatching**: In production code and tests. Real files in `tmp_path`, never mock the Store.
- **No Passthrough Args**: Spell out function parameters explicitly; avoid `*args` and `**kwargs`.
- **Allowed Decorators Only**: `@property`, `@dataclass`, `@pytest.fixture`, and framework routing decorators.
- **Size Limits**: Max 200 lines per file; max 40 lines per function; max 1 level of comprehension nesting.

---

## 03 · Architecture & Layer Invariants
- **Four Layers**:
  - `iw/contracts/`: Python `Protocol` classes only. Zero implementation logic.
  - `iw/core/` & `iw/domain/`: Business logic. Depends ONLY on contracts and stdlib/yaml. Never import `adapters`, `web`, or `mcp`.
  - `iw/adapters/`: Outer connectors (capture inlets, couriers, extractors, storage).
  - `iw/web/` & `iw/mcp/`: Surfaces.
- **No Background Engines / Watchers**: No background daemon threads, schedulers, or file system watchers (V§14.4).
- **The Service is Never the Only Writer**: Files arrive via tablet sync or direct editing in Obsidian. Reads hit disk; writes are atomic (`tempfile` + rename).

---

## 04 · ID Scheme & Behaviour Specs
- **IDs**: Format `PREFIX-A01` (e.g., `FRI-A01`, `IDEA-A01`, `UOW-A01`). Sequential, case-insensitive on input, uppercase on write, never reused, letters `I` and `O` excluded.
- **Specs**: Authored per subsystem in `docs/design/specs/<SUBSYSTEM>.md`.
- **Traceability**: Every spec ID appears in its spec file and in test names/docstrings (`grep -r STORE-04 tests/`).

---

## 05 · Slice Delivery Handoff
Every completed slice or code change must hand back:
1. **What changed** (concise summary of files and components).
2. **Which Spec IDs were satisfied**.
3. **Which tests prove them** (`pytest` command and passing results).
4. **What was deliberately not done** (to highlight scope boundaries).
