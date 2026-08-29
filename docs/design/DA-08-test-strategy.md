---
id: DOC-DA-08
type: artifact
title: DA-08 · Test Strategy and Review Protocol
date: 2026-08-29
domain: meta
tags: [testing, review, protocol, standards]
---

# DA-08 · Test Strategy and Review Protocol

**How code is tested, verified, and reviewed by a Java/C/C++ reader of Python.**

Governed by `docs/DesignPhasePlan_2.md` §09 and `docs/InnovatorsWorkspaceVision_12.md`.

---

## 01 · Test Philosophy

Tests are the primary artifact through which Jared trusts code written by AI agents. The implementation code is secondary.

### Core Testing Rules

1. **Tests Read as English Specifications**:
   - Test names must read as complete, unambiguous sentences:
     `def test_store_creates_file_atomically_using_temp_rename():`
   - If a test name needs a comment to explain what it asserts, the name is wrong.
2. **The Store is Never Mocked**:
   - Store and file tests always write and read real markdown files in temporary directories (`tmp_path`). Mocking filesystem I/O tests a fiction.
3. **Simulate the Other Writer**:
   - The IW service is not the only writer. Files change via tablet sync, external text editors (Obsidian), or git. At least one test per store operation simulates files changing or appearing unexpectedly between operations.
4. **Coverage is Not a Target**:
   - We do not chase percentage coverage metrics.
   - The true target is: **Every Behaviour Spec ID (e.g. `STORE-01`, `TRIAGE-03`) has at least one explicit test.**
5. **Golden-File Fixtures for Store Roundtripping**:
   - A fixture directory of markdown files in → expected node graph out. Catches frontmatter parsing regressions immediately.
6. **Negative Tests Form The Wall (MCP)**:
   - The MCP server tests explicitly assert the wall: exactly 5 exposed tools, zero filesystem paths/table names leaked in responses or errors, refusal of undeclared context IDs.

---

## 02 · The Three Test Tiers

Tests are partitioned strictly into three directories:

```
tests/
  contract/    # Tier 1: Protocol compliance tests (runs against every adapter implementation)
  behaviour/   # Tier 2: Behaviour spec tests (named for and traced to Spec IDs)
  arch/        # Tier 3: Architectural invariant & boundary tests (import graph, size limits, no watchers)
```

| Tier | Directory | Scope & Purpose | Traceability Handle |
|---|---|---|---|
| **Contract** | `tests/contract/` | Validates that concrete implementations satisfy the Python `Protocol` interfaces in `iw/contracts/`. | Named after the interface (e.g. `test_store_contract.py`). |
| **Behaviour** | `tests/behaviour/` | Validates specific subsystem behaviour rules. | Named after Spec ID (e.g. `test_store_04_atomic_write()`). |
| **Architecture** | `tests/arch/` | Static AST checks ensuring layer boundaries, file size limits, and absence of watchers/daemons. | Named after architectural principle. |

---

## 03 · Python Review Protocol for Java/C/C++ Engineers

Built for Jared reviewing high-volume Python code without prior Python expertise:

1. **Run It First**:
   - Before reading code, run `uv run pytest`. If tests fail or the app doesn't start, reject the slice immediately.
2. **Read in Strict Order**:
   - **1. Behaviour Spec** (`docs/design/specs/*.md`)
   - **2. Tests** (`tests/behaviour/` or `tests/contract/`)
   - **3. Protocol / Interface** (`iw/contracts/*.py`)
   - **4. Implementation**
   - *Rule:* If a test does not read as a clear English sentence you agree with, reject the slice before opening the implementation.
3. **Check Layer Boundaries**:
   - Verify changes against the Component Map (`DA-04`). Any layer crossing (`core` importing `web` or `adapters`) is an automatic finding.
4. **Ask for the Java Analogue**:
   - For any unfamiliar Python idiom, ask for the Java/C++ equivalent rather than guessing.
5. **Enforce Size & Complexity Limits**:
   - File size ≤ 200 lines.
   - Function size ≤ 40 lines.
   - Comprehension nesting ≤ 1 level.
6. **Every Slice Handoff Must Include**:
   - What changed.
   - Which Spec IDs are satisfied.
   - Which tests prove them.
   - What was deliberately *not* done (scope-creep check).

---

## 04 · The Python Ban List

To keep Python code readable and maintainable for Java/C/C++ engineers, the following constructs are **strictly forbidden** in all non-test codebase files:

> - No metaclasses.
> - No custom decorators beyond `@property`, `@dataclass`, `@pytest.fixture`, and framework routing decorators.
> - No `__getattr__` or `__setattr__` magic.
> - No dynamic imports or `importlib`.
> - No monkeypatching in code or tests.
> - No `*args` or `**kwargs` passthrough in business logic — spell all parameters out.
> - No list/dict comprehensions nested more than one level.
> - No `functools.partial` where a named function would do.
> - Explicit type hints on all public functions, methods, and classes — no exceptions.
