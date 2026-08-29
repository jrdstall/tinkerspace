---
id: DOC-DA-01
type: artifact
title: DA-01 · Glossary and ID Register
date: 2026-08-29
domain: meta
tags: [glossary, ids, naming, data-model]
---

# DA-01 · Glossary and ID Register

**Innovator's Workspace (IW) — Unified vocabulary and authoritative ID specification.**

Governed by `docs/InnovatorsWorkspaceVision_12.md` and `docs/DesignPhasePlan_2.md`. This document establishes the single source of truth for terminology and identifier allocation across all documentation, tests, and code.

---

## 01 · System Vocabulary

Every term below has exactly one meaning. Terms not listed here must not be introduced into code or documentation without updating this register.

### Core Entities

| Term | Precise Meaning | File / Storage Representation |
|---|---|---|
| **Node** | A primary typed entity in the corpus. Holds structured properties in YAML frontmatter and unstructured thoughts in the markdown body. | Exactly one `.md` file in `iw-vault/<type>/YYYY-MM-DD-slug.md`. |
| **Edge** | A typed, directed relationship between two nodes (e.g., `derived_from`, `raises`, `enables`, or custom user relations). | Stored as structured items in frontmatter `edges[]` or derived index. |
| **Record** | An immutable timestamped event or historical entry (e.g., an event log line, a maturity assessment pass, a screening verdict). | Appended to `events.jsonl` or stored in a node's frontmatter history array. |
| **Artifact** | A concrete file or digital object (e.g., a written report, a trade study matrix, an SVG diagram, a datasheet, a code snippet) that acts as an **input** to, or an **output** produced by, a work unit or node. | Node file in `iw-vault/artifact/` or file in `work/UOW-xxx/` / `drop/`. |
| **Asset** | A node representing a standing capability Jared owns, built, or knows how to do (e.g., 3D printer, soldering rig, trail-camera system, Java programming). | Node file in `iw-vault/asset/` at capability-grain. |
| **Work Unit (UOW)** | A single, atomic, dispatchable task step with defined input artifacts, deliverable specifications, assignee, and state. | Dedicated folder `iw-vault/work/UOW-xxx/` containing `unit.yaml` and associated input/output files. |
| **Workflow (WFL)** | An ordered or dependency-linked graph of Work Units attached to a subject node. | Managed via domain workflow service; composed of UOWs. |
| **Activity** | A named class of maturation work from the catalogue (e.g., `trade-study`, `prior-art-survey`, `questionstorm`). Content, not code. | Defined in activity template files. |
| **Template** | A reusable specification file for an activity, workflow, or human step. | Stored in `content/activities/` or `content/workflows/` in the codebase. |

---

### The Critical Distinctions

#### 1. Asset vs. Artifact
- **`Asset`** (`AST`): Something Jared **owns, has built, or knows how to do**. It represents standing capability that makes future ideas reachable (`enables` relationship). Captured at capability grain (e.g., *"Jeep trail-camera rig"* or *"I can write Java"*), never fine-grained consumable inventory.
- **`Artifact`** (`ART`): A **concrete file or digital deliverable** (e.g. report, block diagram, code snippet, datasheet, survey findings). An artifact can serve as an **input** to a step, an **output** produced by a step, or both (where step 1's output artifact becomes step 2's input artifact).

#### 2. Templates: Activity vs. Workflow
- **`Activity Template`**: A reusable specification for a **single task/activity step** (e.g., `trade-study@1`, `prior-art-survey@1`). Defines expected inputs, deliverable structure, prompt/instructions, and size hint.
- **`Workflow Template`**: A reusable pre-defined **sequence or graph of steps** (e.g., `cml-2-to-4-maturation@1`, `a-team-study@1`). When instantiated for an idea, it creates a set of connected Work Units (`UOW-xxx`).

#### 3. View vs. Reading a Note
- **`View`**: A purpose-built, interactive screen in the IW web application (e.g., **Explore**, **Work board**, **Node view**, **Workflow diagram**). Available on the **Workstation** and **Laptop**.
- **`Reading a Note`**: Opening a raw markdown file in any standard text/markdown editor (e.g., **Obsidian** on Workstation/Laptop/Tablet, VS Code, or Notepad) against the synced store. Requires **no IW service running**.
- *Rule:* Neither term is ever used for the other. Every node must be fully legible and convey all its state (scores, links, CML) when *reading a note* in Obsidian without an active *view*.

#### 4. Assignee, Author, and Worker
- **`Assignee`**: The entity tasked with completing a Work Unit. Stored explicitly as `assignee: { kind: human | agent | tool, tier: subscription | local | api, model: string | null }`.
- **`Author`**: The entity that wrote or modified a node or edge. Stored explicitly as `author: { kind: human | agent | tool | external, courier: string, requested_model: string, declared_model: string }`.
- **`Worker`**: Informal English word for whoever is performing work. *Never a stored value or enum in code.*

---

### Architecture & Runtime Terms

| Term | Precise Meaning |
|---|---|
| **Component** | A modular architectural unit in Layers 1–4 behind a Python `Protocol` interface. |
| **Store** | Layer 1 component responsible for reading and writing markdown files, frontmatter, and work unit folders. |
| **Index** | Layer 1 derived, disposable query accelerator (in-memory scan in Phase 1, SQLite in Phase 2). |
| **Courier** | Layer 3 adapter that transports a Work Unit order to a worker and retrieves results (MCP pull, file handoff, human file template). |
| **Inlet** | Layer 3 adapter that accepts raw text, files, or sketches into the inbox. |
| **Surface** | Layer 4 external interface exposed by the system (Web UI, MCP server). |
| **The Wall** | The architectural boundary enforced by the MCP server: agents receive declared context only; agents never receive filesystem paths, database tables, search tools, or store exploration primitives. |

---

## 02 · ID Specification & Prefix Register

Identifiers are designed to be **read, spoken, and typed aloud by a human** (e.g., *"U-O-W A zero one"*). Memorability, brevity, and phonetics supersede timestamps and UUIDs.

### Standard Format: `PREFIX-A01`

```
  [PREFIX] - [LETTER(S)] [DIGITS]
    │           │           │
   FRI    -     A          01
```

- **Prefix**: 3 to 4 uppercase letters defining the entity type.
- **Letter Position**: Uppercase letter(s) defining the alphabetical series (`A` through `Z`). **`I` and `O` are strictly excluded** to avoid visual confusion with `1` and `0`.
- **Digit Position**: 2 decimal digits (`01` through `99`).

### Series Progression
1. **Single-Letter Series**: `A01` .. `A99`, `B01` .. `B99`, ... `H01` .. `H99`, `J01` .. `J99`, ... `N01` .. `N99`, `P01` .. `Z99`.
   - Total single-letter space: 24 valid letters × 99 numbers = **2,376 unique IDs per prefix**.
2. **Two-Letter Series (Overflow)**: `AA01` .. `ZZ99` (excluding `I` and `O` in both letter positions: 24 × 24 × 99 = **57,024 unique IDs per prefix**).

---

### Authoritative Prefix Table

| Prefix | Entity Type | Stored Path in Vault | Description |
|---|---|---|---|
| **`FRI`** | Friction | `friction/YYYY-MM-DD-slug.md` | Irritations, complaints, seedling problems (*"I don't like..."*) |
| **`OBS`** | Observation | `observation/YYYY-MM-DD-slug.md` | Noticed facts, things learned from people or experiments |
| **`IDEA`** | Idea | `idea/YYYY-MM-DD-slug.md` | Specific concept or proposed solution |
| **`QUE`** | Question | `question/YYYY-MM-DD-slug.md` | Questions held open, inquiry graph nodes |
| **`EXP`** | Experiment | `experiment/YYYY-MM-DD-slug.md` | Test designs, trials, build-and-measure efforts |
| **`AST`** | Asset | `asset/YYYY-MM-DD-slug.md` | Standing capabilities (skills, tools, systems Jared has) |
| **`ART`** | Artifact | `artifact/YYYY-MM-DD-slug.md` | Inputs or outputs associated with work units/nodes |
| **`SRC`** | Source | `source/YYYY-MM-DD-slug.md` | Provenance for external papers, articles, datasheets |
| **`UOW`** | Unit of Work | `work/UOW-xxx/unit.yaml` | Single executable task step |
| **`WFL`** | Workflow | (Frontmatter / workflow state) | Dependency set of work units |
| **`DOC`** | Document / Design | `docs/design/...` | Meta design documents and specifications |

---

## 03 · Allocation Algorithm & Rules

The ID allocation algorithm must be strictly deterministic: two independent people or processes scanning the same store must allocate the exact same next ID.

### Deterministic Allocation Algorithm

1. **Scan**: Scan the vault directory corresponding to the requested entity prefix (or all existing frontmatter `id` fields).
2. **Filter & Parse**: Extract all IDs matching `^PREFIX-([A-HJ-NP-Z]{1,2})([0-9]{2})$` (case-insensitive).
3. **Empty Case**: If no IDs exist for the prefix, return **`PREFIX-A01`**.
4. **Sequence Numbering**: Map each letter sequence to base-24 number using the alphabet `['A'..'H', 'J'..'N', 'P'..'Z']`:
   - Single letter: `index = letter_val * 99 + (number - 1)`
   - Two letters: `index = (24 + first_letter_val * 24 + second_letter_val) * 99 + (number - 1)`
5. **Increment**: Take the highest allocated sequence index, increment by `1`, and encode back into the corresponding letter(s) and zero-padded 2-digit string.
6. **Return**: Format as uppercase `PREFIX-<SUFFIX>`.

### Invariant Rules
- **No Reuse**: An allocated ID is **never reused**, even if the node is archived, retired, parked, or deleted. Edges and event logs maintain permanent referential integrity.
- **Case-Insensitive In, Uppercase Out**: Input queries (`fri-a01`, `Fri-A01`) resolve cleanly; all stored frontmatter and filenames write strictly uppercase (`FRI-A01`).
- **No `I` or `O`**: Characters `I` and `O` are forbidden in letter positions. Valid letter alphabet: `A, B, C, D, E, F, G, H, J, K, L, M, N, P, Q, R, S, T, U, V, W, X, Y, Z` (24 letters).
- **Paths Never Refer to Filenames**: Links in markdown or YAML reference IDs only (`id: IDEA-A01`), never file paths (`idea/2026-08-24-cycling-display.md`). Filenames may be renamed freely without breaking links.
