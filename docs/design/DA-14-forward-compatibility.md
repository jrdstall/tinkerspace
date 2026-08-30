---
id: DOC-DA-14
type: artifact
title: DA-14 · Forward-Compatibility Checklist
date: 2026-08-30
domain: meta
tags: [forward-compatibility, audit, architecture, local-models, vector-index, association-engine, vendor-independence]
---

# DA-14 · Forward-Compatibility Checklist

**The architectural audit of the finished Phase 1 and 2 design specifications against future requirements (Phases 3–5) and the definitive Vendor-Independence Test.**

Governed by `docs/DesignPhasePlan_2.md` §12, DA-14 and `docs/InnovatorsWorkspaceVision_12.md` V§05, V§07, V§08, V§10, V§13, V§14.

---

## 01 · Purpose & Pragmatic Architecture

Per the scope boundary established in the Design Phase Plan, Phases 3–5 are deliberately not designed upfront. Instead, **DA-14 serves as an architectural sanity check** — a structured audit pass over the completed Phase 1 and Phase 2 specifications (`DA-01` through `DA-12`) to confirm that our foundation does not bake in accidental dead-ends (such as hardcoded cloud billing or rigid database lock-in).

```
┌────────────────────────────────────────────────────────────────────────┐
│ THE PRAGMATIC ARCHITECTURE POSTURE (AGENTS.md)                         │
│                                                                        │
│  1. Clean Seams: Future capabilities (local models, vector search,      │
│     association samplers) can plug in naturally as outer adapters or   │
│     disposable projections without needing a total scrap-and-rewrite. │
│                                                                        │
│  2. Usability & Iteration First: If building or testing reveals that   │
│     a Core concept, data structure, or interface is clunky or wrong,   │
│     Core will be refactored immediately. Real-world single-user        │
│     usability always takes precedence over preserving past sketches.   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 02 · The Eight Forward-Compatibility Audits

---

### Audit 1 · Local Model Tier as a Provider Adapter (D2, V§08)

* **Requirement:** The local model tier (e.g. Ollama, `llama.cpp`, local Qwen) must arrive as an outer courier adapter without assuming remote network connectivity, latency, or token billing.
* **Design Check:**
  * In `iw/contracts/courier.py` (`DA-04`), the `CourierProtocol` is an abstract interface with zero assumptions about HTTP or billing.
  * In `iw/contracts/models.py`, `Author` differentiates between `courier` (observed as `"local-model"`) and `declared_model` (asserted by worker).
  * In `DA-10` (MCP Contract), the 5 tools operate identically over `stdio` subprocess pipes as they do over network SSE.
  * In `DA-11` (Activity Templates), `default_assignee.tier` distinguishes `fast`, `standard`, and `frontier`, explicitly allowing zero-cost local routing for high-volume pairing tasks (V§13).
* **Where it changes:** Simply add `iw/adapters/courier/local_model.py` implementing `CourierProtocol`. Zero changes to `iw/core/` or `iw/domain/`.
* **Verdict:** `PASS`

---

### Audit 2 · Embeddings & Vector Index as a Disposable Projection (D5, A8)

* **Requirement:** Embeddings and semantic search must live in a derived SQLite cache that can be blown away and recomputed from markdown on disk at any time without database migrations.
* **Design Check:**
  * In `DA-02 §04` and `iw/contracts/store.py`, markdown frontmatter on disk is the **sole source of truth**. SQLite is strictly a secondary read-cache.
  * In `iw/contracts/index.py` (`IndexProtocol`), the index exposes `rebuild_index()` which scans all `.md` files fresh from disk.
  * In Phase 3, adding vector embeddings (via `sqlite-vec` or an embedding table) only extends the SQLite table creation in `iw/core/index.py`. Deleting `cache.db` and restarting recalculates embeddings from the markdown body.
* **Where it changes:** Add embedding generation inside `iw/core/index.py:rebuild_index()`. Zero changes to node markdown format or the store engine.
* **Verdict:** `PASS`

---

### Audit 3 · Association Engine Corpus Dump Delivery (V§13, V§05)

* **Requirement:** The distilled corpus dump (title, one-line, domain, tags, origin, state) must be producible as a tool step output and delivered through `fetch_context` without turning `fetch_context` into an open query/search interface (protecting the MCP Wall).
* **Design Check:**
  * In `DA-10 §01` (Invariant 6: Uniform Bulk Delivery), bulk context is explicitly defined as an input artifact.
  * When an association run (`UOW-xxx`) is instantiated, the system exports the distilled corpus to `work/UOW-xxx/inputs/corpus_dump.json` (registered as `ART-CORPUS-DUMP`).
  * The agent retrieves this declared file via `fetch_context("UOW-xxx", "ART-CORPUS-DUMP")`.
  * The MCP Wall remains completely sealed: no `list_nodes` or `search_vault` tools exist or are required.
* **Where it changes:** Implemented as standard workflow instantiation in `iw/core/workflow.py`. Zero modifications to the MCP protocol or wall invariants.
* **Verdict:** `PASS`

---

### Audit 4 · Assets in the Pairing Pool (V§13, V§09)

* **Requirement:** Assets (`AST-xxx`) must participate directly in combinatorial pairing (V§13) without the sampler assuming every node has maturity scores or standard idea fields.
* **Design Check:**
  * In `DA-03 §02` (Data Model), `asset` is a first-class `Node` type with standard identity fields (`id`, `title`, `domain`, `tags`, `state`).
  * In `iw/contracts/models.py` and `DA-02`, custom attributes live in `attrs: dict[str, Any]` (e.g. `attrs.capability`, `attrs.location`).
  * The pairing sampler selects over all active `Node` entities. It does not require `scores.novel` or `scores.works` to exist on parent nodes.
* **Where it changes:** Implemented in the Phase 3 sampler algorithm (`iw/core/sampler.py`). Zero changes to data structures or store schemas.
* **Verdict:** `PASS`

---

### Audit 5 · Competing Sampler Strategies with a Control Arm (V§13)

* **Requirement:** The system must record which strategy (`random` control, `anti_similar`, `mid_band`) produced each kept survivor, logging attribution from day one of the engine.
* **Design Check:**
  * In `DA-03 §04` (Edge Model) and `iw/contracts/models.py`, `Edge` carries `relation: "derived_from"`, `note: str`, and `attrs: dict[str, Any]`.
  * When Jared accepts an association survivor, the edge records:
    ```yaml
    relation: derived_from
    note: "Synthesized via association run"
    attrs:
      sampler_strategy: "anti_similar"
      distance_metric: 0.78
    ```
  * In `DA-09 §06` (Event Log), `unit.accepted` records the full attribution payload in `events.jsonl`.
* **Where it changes:** Stamped by the association collection step. Edge and event models accommodate this natively without schema changes.
* **Verdict:** `PASS`

---

### Audit 6 · Agent-Proposed Template Revisions (V§05, V§10)

* **Requirement:** Activity templates must be versioned content in git so that an agent proposing a template improvement creates a standard, reviewable git diff.
* **Design Check:**
  * In `DA-11 §01 & §03`, templates are standalone YAML files in `templates/activities/<id>@<version>.yaml` tracked in git.
  * When an agent proposes a revised template, it submits the file into `work/UOW-xxx/proposed_template.yaml` via `submit_result`.
  * Jared reviews the diff on the Work Board and approves merging it into `templates/activities/`.
* **Where it changes:** Content files in git. Zero code changes required to support template evolution.
* **Verdict:** `PASS`

---

### Audit 7 · The `meta` Domain Invariant (V§14.21)

* **Requirement:** Frictions and ideas about Innovator's Workspace itself are ordinary nodes in the `meta` domain, competing with engineering ideas without special-case logic.
* **Design Check:**
  * In `DA-03 §03` and `DA-05 §04`, `domain: "meta"` is a standard string domain value alongside `mechanics`, `electronics`, `software`, etc.
  * Meta nodes travel the exact same triage pipeline, earn the exact same CML scores, and instantiate the exact same units of work.
  * No `if node.domain == "meta"` branching exists in Core, Contracts, or Store.
* **Where it changes:** Handled entirely uniformly by standard system logic.
* **Verdict:** `PASS`

---

### Audit 8 · Maturity Scores & Derived CML Frontmatter (V§14.15, DA-03, DA-12)

* **Requirement:** Multi-criteria scores, screening verdicts, and CML must materialize directly into note frontmatter on disk without breaking unassessed notes or requiring database migrations.
* **Design Check:**
  * In `DA-12 §07` and `DA-03 §05`, collection updates `subject.attrs['scores']` (`novel`, `works`, `reach`, `story`) and writes `cml = min(scores.values())` directly to disk using atomic rename.
  * Unassessed notes lack score attributes and cleanly default to CML 1.
  * In `DA-12 §05`, missing or unparseable scores degrade gracefully without aborting collection or corrupting frontmatter.
* **Where it changes:** Fully implemented in `DA-12` parser and `iw/core/frontmatter.py`. Zero migration debt.
* **Verdict:** `PASS`

---

## 03 · The Vendor-Independence Review Question (V§07)

> **The Fundamental Test:** *"Could Jared delete every other tool today and still capture, read, triage, plan, dispatch, and review?"*

```
┌────────────────────────────────────────────────────────────────────────┐
│ VENDOR INDEPENDENCE AUDIT (DELETING OBSIDIAN, VS CODE, CLAUDE, ETC.)  │
└────────────────────────────────────────────────────────────────────────┘
```

| Lifecycle Step | How IW Executes Standalone (Zero External Dependencies) | Status |
|---|---|:--:|
| **1. Capture** | Local Starlette web form (`/capture`), global hotkey script, or dropping a `.txt` file into `iw-vault/inbox/`. | **PASS** |
| **2. Triage** | Standalone keyboard triage surface (`/triage`) with 1-keystroke domain keys, tag input, and atomic file creation. | **PASS** |
| **3. Read & Explore** | Local web app (`/explore`) with full-text search, domain filters, and markdown rendering. All files readable in standard text editor. | **PASS** |
| **4. Plan & Dispatch** | Local workflow engine (`/workflows`) instantiates templates into `work/UOW-xxx/unit.yaml` without needing cloud servers. | **PASS** |
| **5. Human Work** | Jared opens `work/UOW-xxx/deliverable.md` in any basic text editor (Notepad, Vim), edits prose, and clicks *Attach Result* in the IW UI. | **PASS** |
| **6. AI Work** | Works with local models via stdio, external agents via neutral JSON-RPC MCP, or offline via self-contained clipboard File Handoff. | **PASS** |
| **7. Review & Collect** | IW collection engine parses DA-12 headers, updates subject YAML frontmatter, stamps attribution, and commits to local git. | **PASS** |

### Verdict on Vendor Independence
**PASS.** Innovator's Workspace owns 100% of its data (markdown/YAML on disk), its versioning (local git), its business logic (pure Python stdlib), and its interface (local Starlette/HTMX server). If every third-party service and tool were uninstalled tomorrow, the system remains completely operational.

---

## 04 · Summary Audit Matrix

| # | Check Item | Vision Ref | Design Spec | Architectural Nature | Verdict |
|---|---|---|---|---|:--:|
| **1** | Local Model Tier | D2, V§08 | `DA-04`, `DA-10` | Additive courier adapter (`iw/adapters/`) | `PASS` |
| **2** | Vector Embeddings | D5, A8 | `DA-02`, `DA-04` | Disposable SQLite rebuild (`iw/core/index.py`) | `PASS` |
| **3** | Corpus Dump Delivery | V§13, V§05 | `DA-10`, `DA-09` | Declared artifact via `fetch_context` | `PASS` |
| **4** | Assets in Pairing Pool | V§13, V§09 | `DA-03` | Native `Node` type (`type: asset`) | `PASS` |
| **5** | Control Arm Attribution | V§13 | `DA-03`, `DA-09` | Stamped on `Edge.attrs` & `events.jsonl` | `PASS` |
| **6** | Agent Template Diffs | V§05, V§10 | `DA-11`, `DA-02` | Git-versioned YAML files in vault | `PASS` |
| **7** | `meta` Domain Invariant | V§14.21 | `DA-03`, `DA-05` | Standard domain string; zero special cases | `PASS` |
| **8** | CML Frontmatter | V§14.15 | `DA-03`, `DA-12` | Atomic disk write to subject YAML | `PASS` |
| **9** | Vendor Independence | V§07, V§14 | Whole System | 100% self-contained local stack | `PASS` |

---

## 05 · Design Phase Completion Greenlight

With all eight forward-compatibility audits passing with zero architectural amendments required, **the Phase 1 and Phase 2 design specifications (`DA-01` through `DA-12`, `DA-14`) are complete, validated, and ready for full implementation.**

