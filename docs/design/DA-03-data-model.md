---
id: DOC-DA-03
type: artifact
title: DA-03 · Data Model Reference
date: 2026-08-29
domain: meta
tags: [data-model, schema, edges, erd, graduation]
---

# DA-03 · Data Model Reference

**Complete field-level specifications for nodes, flexible edge vocabulary, authored vs. derived field lifecycle, and entity-relationship model.**

Governed by `docs/InnovatorsWorkspaceVision_12.md` §09, §11, §13, §14 and `docs/DesignPhasePlan_2.md` DA-03.

---

## 01 · Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    NODE ||--o{ EDGE : "participates in"
    NODE ||--o{ RECORD : "has history"
    NODE ||--o{ ARTIFACT : "references or attaches"
    WORK_UNIT ||--o{ ARTIFACT : "consumes (inputs) & produces (outputs)"
    WORKFLOW ||--|{ WORK_UNIT : "contains"
    NODE ||--o{ WORKFLOW : "subject of"

    NODE {
        string id PK "FRI-xxx, IDEA-xxx, AST-xxx"
        string type "friction, observation, idea, question, asset, source"
        string title "Concise description"
        datetime created "ISO 8601 UTC"
        string domain "Primary domain tag"
        string_list tags "Searchable tags"
        string state "active, parked, retired"
        datetime last_touched "ISO 8601 UTC"
        json attrs "Extensible key-value bag"
    }

    EDGE {
        string from FK "Source node ID"
        string to FK "Target node ID"
        string relation "Canonical relation or custom string"
        datetime created "ISO 8601 UTC"
        json author "Attribution structure"
        float confidence "0.0 to 1.0"
        string note "Context or justification"
    }

    WORK_UNIT {
        string id PK "UOW-xxx"
        string workflow FK "WFL-xxx or null"
        string_list subject FK "Subject node IDs"
        string title "Work description"
        string activity "Activity catalogue key"
        string_list input_artifacts "ART-xxx input files"
        string state "blocked, ready, dispatched, returned, accepted"
        string template "Template version tag"
    }

    ARTIFACT {
        string id PK "ART-xxx"
        string role "report, diagram, dataset, input_doc"
        string produced_by FK "UOW-xxx or null"
        string_list input_to FK "UOW-xxx consuming this"
        string source_file "Relative path in vault"
        string rendered_file "Relative SVG/PNG path"
    }

    RECORD {
        string id PK "Event or assessment ID"
        string subject FK "Node ID"
        datetime timestamp "ISO 8601 UTC"
        string kind "assessment, screening, dispatch"
        json payload "Record details"
    }
```

---

## 02 · Edge Relations: Canonical Vocabulary & Open Flexibility

### Open Flexibility Rule
The `relation` field in an Edge is stored as an **open string**. You are not restricted to an immutable enum; you can define custom relationship names during triage or note editing at any time.

### Canonical 19 Relations
To enable automated graph rendering (e.g. question graphs, maturity calculations, workflow chaining), the system recognizes 19 standardized relations with defined directionality:

| # | Relation Name | From Node | To Node | Directional Meaning |
|---|---|---|---|---|
| 1 | **`raises`** | Friction / Observation / Idea | Question | `from` brings up or triggers inquiry in `to` |
| 2 | **`answers`** | Idea / Observation / Experiment | Question | `from` resolves or provides an answer for `to` |
| 3 | **`addresses`** | Idea / Experiment | Friction | `from` offers a solution or mitigation for `to` |
| 4 | **`evidence_for`** | Observation / Experiment / Source | Idea / Question | `from` provides supporting evidence for `to` |
| 5 | **`evidence_against`** | Observation / Experiment / Source | Idea / Question | `from` provides refuting evidence against `to` |
| 6 | **`contradicts`** | Node | Node | `from` factually conflicts with statement in `to` |
| 7 | **`duplicate_of`** | Node (duplicate) | Node (canonical) | `from` is a duplicate of original node `to` |
| 8 | **`refines`** | Idea / Question | Idea / Question | `from` clarifies, details, or specializes `to` |
| 9 | **`supersedes`** | Node (successor) | Node (predecessor) | `from` obsoletes and replaces `to` |
| 10 | **`derived_from`** | Idea / Asset | Parent Node(s) | `from` originated from concept/material in `to` |
| 11 | **`produced_by`** | Artifact | Unit of Work | `from` was generated during execution of `to` |
| 12 | **`illustrates`** | Artifact (Drawing/Diagram) | Node | `from` visually depicts or charts `to` |
| 13 | **`cites`** | Node | Source / Artifact | `from` references external publication or file `to` |
| 14 | **`broadens`** | Question | Question | `from` expands the inquiry scope of `to` |
| 15 | **`narrows`** | Question | Question | `from` focuses the inquiry scope of `to` |
| 16 | **`presupposes`** | Question / Idea | Question / Assumption | `from` takes for granted the prior truth of `to` |
| 17 | **`reframes`** | Question / Idea | Question / Idea | `from` shifts the paradigm or perspective of `to` |
| 18 | **`rejected_because`** | Candidate Idea / Option | Observation / Finding | `from` was screened out due to criteria in `to` |
| 19 | **`enables`** | **Asset** | **Idea / Experiment** | **`from` (standing capability) makes `to` reachable** |

> [!IMPORTANT]
> **Direction of `enables`**: `AST-A01 (Asset)` → `IDEA-A01 (Idea)`. The asset is the enabler; the idea is the beneficiary.

---

## 03 · Frontmatter Fields of a Node (`.md` Note File)

The table below specifies all YAML frontmatter fields stored inside each individual node's `.md` file, distinguishing between directly authored fields and system-derived fields.

Per V§14.15, **a note carries its own state**. Derived fields are never calculated solely at display time in a view; they are materialized directly into the file's YAML frontmatter.

| Frontmatter Field | Nature | Default Value | Write Trigger Event |
|---|---|---|---|
| `id` | Authored | Auto-allocated | Initial file creation |
| `type` | Authored | Required | Triage or manual authoring |
| `title` | Authored | Required | Triage or note edit |
| `domain`, `tags` | Authored | Required | Triage or note edit |
| `state` | Authored | `active` | User state change (`active`, `parked`, `retired`) |
| `worth_me`, `worth_others` | Authored | Required on Idea | User evaluation in Triage / Node view |
| `scores.novel` | Derived | `1` | Prior-art survey completion or self-assessment |
| `scores.works` | Derived | `1` | Proof-of-concept trial or assessment |
| `scores.reach` | Derived | `1` | Parts-and-skills survey read against assets |
| `scores.story` | Derived | `1` | Pitch draft review or self-assessment |
| `cml` | Derived | `1` | Recomputed automatically as `min(novel, works, reach, story)` |
| `screening_verdict` | Derived | `null` | Completion of screening assessment activity |
| `last_touched` | Derived | Timestamp on write | Any write operation touching the note |

### Recompute Command (V§14.18)
All derived fields can be recomputed deterministically from store files using a single CLI command:
```bash
uv run tinkerspace recompute
```
Executing this command on a clean repository produces **byte-identical** file frontmatter.

---

## 04 · The `attrs{}` Bag Graduation Procedure

To prevent premature data modeling, new experimental attributes start in the `attrs{}` dictionary.

### The Graduation Rule (V§14.20)
A key lives in `attrs{}` until code logic branches on it. The moment:
1. A UI view filters, sorts, or renders specially based on the key, OR
2. A workflow rule or domain service gates logic on the key,

The key **graduates** out of `attrs{}` to become a first-class typed property in the schema.
