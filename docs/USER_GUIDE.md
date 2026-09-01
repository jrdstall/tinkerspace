# Innovator's Workspace (Tinkerspace) — User Guide & Operational Playbook

Welcome to **Tinkerspace**, your personal, distraction-free innovation workstation. 

This guide provides step-by-step instructions for running, operating, and mastering the workspace, along with operational playbooks for everyday innovation routines.

---

## 01 · Philosophy & Core Principles

Tinkerspace is built around a few foundational commitments:

1. **You Are the Chief Architect**: AI agents are tireless research assistants and pair programmers operating behind a secure tool wall. They draft, survey, analyze, and propose — but **only you make decisions, approve changes, and advance ideas**.
2. **Zero-Classification Frictionless Capture**: Thoughts, irritations, and sparks enter the system instantly without forcing you to stop and categorize them. Categorization happens later during focused triage.
3. **No Vendor Lock-In (Plain Markdown + Git)**: All notes, work units, and workflows are stored as clean Markdown and YAML files in your `iw-vault/` directory. Writes are atomic (`tempfile` + rename), and changes are automatically committed to git. You can inspect or edit everything directly in Obsidian, VS Code, or any text editor.
4. **No Background Engines or Watchers**: The system runs entirely on-demand in response to your explicit interactions. No surprise token bills, background battery drains, or phantom watchers.

---

## 02 · Starting the Application

To launch the local web server:

```powershell
uv run uvicorn iw.web.app:app --port 8000 --reload
```

Open your browser to:
👉 **`http://localhost:8000`**

---

## 03 · The Daily Innovation Rhythm

```
   ┌────────────────────────────────────────────────────────┐
   │ 1. CAPTURE  (Ctrl+K / File Drop / Tablet Sync)         │
   │    Grab raw complaints, observations, and sparks.      │
   └──────────────────────────┬─────────────────────────────┘
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │ 2. TRIAGE   (/triage)                                  │
   │    Fast keyboard pass (A/D/E) to convert to typed nodes.│
   └──────────────────────────┬─────────────────────────────┘
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │ 3. EXPLORE & ASSOCIATE (/associations, /question-graph)│
   │    Discover non-obvious pairings and deconstruct Qs.   │
   └──────────────────────────┬─────────────────────────────┘
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │ 4. PLAN MATURATION (/ideas/{id}/plan)                  │
   │    Auto-draft or custom-build CML advancement plans.   │
   └──────────────────────────┬─────────────────────────────┘
                              ▼
   ┌────────────────────────────────────────────────────────┐
   │ 5. DISPATCH & COLLECT (/board, MCP, CLI Courier)       │
   │    Run activities with Claude/Antigravity and collect.  │
   └────────────────────────────────────────────────────────┘
```

---

## 04 · Feature Playbooks

### A. Quick Capture (`Ctrl+K` or Header Button)
- **Shortcut**: Press `Ctrl+K` anywhere in the app to open the quick-capture modal.
- **Prompt Stems**: Click prompt buttons to kickstart capture:
  - `"I don't like..."` (Friction / Complaint)
  - `"There has to be a better way to..."` (Process / Tooling)
  - `"I wish..."` (Seedling Idea)
- **Submit**: Press `Enter` to send the thought directly into the append-only inbox.

### B. Fast Keyboard Triage (`/triage`)
Process your raw inbox efficiently without taking your hands off the keyboard:
- **`[A]` Accept**: Converts the raw thought into a permanent typed node in `iw-vault/notes/`.
- **`[D]` Discard**: Cleanses noise or irrelevant snippets.
- **`[E]` Defer**: Keeps the item in the inbox for later review.
- **Node Type Selection**:
  - `friction`: A problem, irritation, or bottleneck.
  - `idea`: A potential solution, invention, or concept.
  - `observation`: An empirical real-world signal (observed, networked, or experimented).
  - `question`: An inquiry driving further exploration.
  - `asset`: A physical tool, skill, software, or part you own.
- **Attribution**: Automatically records your authorship (`kind: human`) and syncs to git.

### C. Intake & File Drop (`/intake`)
- **Drop Folder**: Drop PDF datasheets, tablet sketches, images, or Markdown files into `iw-vault/inbox/drop/`.
- **Intake Flow**: Review dropped files on `/intake`, extract readable text automatically with pluggable extractors, and attach them as assets, observations, or idea concept art.

### D. Idea Maturity Board (`/maturity`)
Track ideas through the 5 Concept Maturity Levels (CML):
- **CML 1 · Spark**: Initial raw seedling or napkin sketch.
- **CML 2 · Plausible**: One sketched path with initial prior-art/Heilmeier feasibility.
- **CML 3 · Explored**: A-Team trade space explored with divergent options and pre-declared rejection criteria.
- **CML 4 · Chosen**: Architecture selected with point design, parts & skills survey, and story pitch.
- **CML 5 · Real**: Empirically measured and verified with a working prototype.

**The 4-Score Mini Equalizer**:
- `Novel` (Differentiator vs prior art)
- `Works` (Technical and physical viability)
- `Reach` (Feasibility given your owned assets & hours)
- `Story` (Clarity and compelling narrative pitch)
- *The overall CML equals `min(Novel, Works, Reach, Story)`.*
- **Laggard Spotlight**: Orange indicators immediately identify your lowest-scoring dimension and recommend targeted activities to advance it.

### E. Maturation Planner & Custom Plan Builder (`/ideas/{id}/plan`)
Navigate to any idea node and click **🎯 Plan Maturation**:
- **🤖 Auto-Draft Mode**: Select your target CML (e.g. CML 2 &rarr; 4). The Planner drafts a deterministic, DAG-sequenced workflow enforcing "cheap and decisive first".
- **🛠️ Custom Plan Builder**: Build your own plan from scratch:
  - Add custom steps dynamically.
  - Pick from 12+ activity templates (e.g., `divergent-generation@1`, `trade-study@1`, `point-design@1`, `experiment-design@1`, `parts-and-skills-survey@1`) or define `freeform@1` tasks.
  - Assign to **Agent (AI)**, **Human (Jared)**, or **Tool (Local)**.
  - Set estimated duration (sized to 1–2 hr single-session blocks).
  - Declare upstream step dependencies (e.g., Step 2 depends on Step 1).
- **Instantiate**: One click generates a `WFL-xxx` workflow containing concrete `UOW-xxx` units in `iw-vault/work/`.

### F. Association Engine (`/associations`)
Uncover serendipitous, non-obvious cross-domain links:
- **Combinatorial Sampler**: Pairs ideas across disparate domains (e.g., cycling + solid-state energy).
- **Structural Sampler**: Identifies graph hubs and dangling nodes with few inbound connections.
- **Adversarial Judge**: Automatically scores candidate pairs on plausibility, surprise, and generative potential before presenting them.
- **Card Deck Interface**: Review generated candidate cards with one-click **Keep** (creates permanent typed edge) or **Discard**.

### G. Question Graph (`/question-graph/{id}`)
Deconstruct and expand upon any idea using the **Why &rarr; What If &rarr; How** inquiry arc:
- Transform frictions into high-leverage "Why" questions.
- Branch into divergent "What If" possibilities.
- Converge into actionable "How" implementation questions.

### H. Work Board & Dispatching Agents (`/board`)
- **Ready vs Blocked**: Units whose upstream dependencies are met appear in the **Ready** column.
- **Dispatch to AI**:
  - **MCP Surface**: If using Claude Desktop or Antigravity IDE, connect the MCP server (`iw/mcp/server.py`). The agent fetches task context (`get_step`) and submits deliverables (`submit_result`) without touching your file system directly.
  - **CLI Courier**: Run `uv run python -m iw.adapters.couriers.cli_courier dispatch UOW-xxx` to output structured prompts or dispatches.
- **Result Collection**: Review agent deliverables on `/board`, adjust scores, approve findings, and auto-unblock downstream steps.

### I. Scout Standing Interests (`/scout`)
- Register long-term research topics (e.g., "Solid state cathode degradation").
- Specify domain and staleness intervals (e.g., 30 days).
- When an interest becomes stale, it surfaces on your home dashboard under **Recommended Activities** with one-click actions:
  - **Raise Sweep Order**: Dispatches an observation sweep workflow.
  - **Dismiss**: Resets the staleness interval clock.

---

## 05 · Vault Architecture Reference

All your data lives inside `iw-vault/`:

```
iw-vault/
├── notes/               # Permanent atomic Markdown nodes (IDEA-xxx, FRI-xxx, etc.)
├── work/                # Active and completed work units and workflows
│   ├── WFL-A01/         # workflow.yaml
│   └── UOW-A01/         # unit.yaml, action_guide.md, deliverable.md
├── inbox/
│   ├── raw.jsonl        # Append-only quick-capture inbox
│   └── drop/            # Drop folder for sketches, drawings, and external files
├── cas/                 # Bookkeeper content-addressed store (SHA-256 binary blobs)
├── meta/                # Scout interests, association state, index metadata
└── events.jsonl         # Append-only immutable system event log
```

---

## 06 · Quick Reference Keybindings & URLs

| Route | Purpose | Key Actions |
|---|---|---|
| `/` | **Explore & Search** | Full-text query, facet filtering, recent touches. |
| `/triage` | **Keyboard Triage** | `[A]` Accept, `[D]` Discard, `[E]` Defer. |
| `/maturity` | **Maturity Board** | CML columns, Worth Matrix, Laggard spotlight. |
| `/associations` | **Association Deck** | Keep/Discard serendipity card review. |
| `/board` | **Work Board** | Ready/Blocked units, dispatch, result collection. |
| `/scout` | **Scout Interests** | Register standing topics, review sweep recommendations. |
| `/intake` | **File Drop Intake** | Ingest sketches, PDFs, and tablet exports. |
| `Ctrl+K` | **Quick Capture** | Global hotkey to record raw thoughts. |

---

*Tinkerspace is your workspace — run it, explore it, and let it accelerate your ideas!*
