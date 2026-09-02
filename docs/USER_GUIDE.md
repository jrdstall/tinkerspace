# Innovator's Workspace (Tinkerspace) — User Guide & Operational Playbook

Welcome to **Tinkerspace**, your personal, distraction-free innovation workstation. 

This guide provides step-by-step instructions for running, operating, and mastering the workspace, along with concrete operational playbooks for everyday innovation routines.

---

## 01 · Philosophy & Core Principles

Tinkerspace is built around a few foundational commitments:

1. **You Are the Chief Architect**: AI agents are tireless research assistants and pair programmers operating behind a secure tool wall. They draft, survey, analyze, and propose — but **only you make decisions, approve changes, and advance ideas**.
2. **Zero-Classification Frictionless Capture**: Thoughts, irritations, and sparks enter the system instantly without forcing you to stop and categorize them. Categorization happens later during focused triage.
3. **No Vendor Lock-In (Plain Markdown + Git)**: All notes, work units, and workflows are stored as clean Markdown and YAML files in your vault. Writes are atomic (`tempfile` + rename), and changes are automatically committed to git. You can inspect or edit everything directly in Obsidian, VS Code, or any text editor.
4. **Separation of Code and Data**: Development code (`tinkerspace`) is kept strictly separated from your official personal datastore (`IW/vault`), keeping your real ideas clean and safe during testing.
5. **No Background Engines or Watchers**: The system runs entirely on-demand in response to your explicit interactions. No surprise token bills, background battery drains, or phantom watchers.

---

## 02 · Environments: Production vs Development

Your workstation is set up with two distinct environments:

### 1. Production Deployment (`C:\Users\jrdst\software\IW`)
This is your **daily-driver workspace** where your real notes and official datastore live.
- **Location**: `C:\Users\jrdst\software\IW`
- **To Launch**: Double-click `start.bat` (or run `.\start.ps1` in PowerShell).
- **Contents**:
  ```
  C:\Users\jrdst\software\IW\
  ├── .venv/            # Dedicated, self-contained Python runtime
  ├── vault/            # Your official personal datastore (git repo)
  ├── content/templates # Activity library templates
  ├── start.bat         # 1-click double-clickable launcher
  ├── start.ps1         # PowerShell launcher
  └── USER_GUIDE.md     # This handbook
  ```
- Automatically opens your browser to `http://localhost:8000` connected to your official vault.

### 2. Development Playground (`C:\Users\jrdst\software\tinkerspace`)
This is where we write code, fix bugs, and add new features.
- Contains the full source code, test suites (`tests/`), design specs (`docs/design/`), and build scaffolding.
- All automated tests run against temporary scratch folders in `tmp_path`, never touching your production vault.

### 3. Upgrading Production
Whenever code changes or new features are added in `tinkerspace`, update your production installation with one command:
```powershell
uv run python scripts/deploy.py --target "C:\Users\jrdst\software\IW"
```
*This installs the latest package and templates in 5 seconds while leaving your existing `vault/` data 100% untouched.*

---

## 03 · Syncing Your Vault with GitHub (Multi-Device Sync)

Your production datastore at `C:\Users\jrdst\software\IW\vault` is initialized as a standard Git repository. To sync your notes across your workstation, tablet, and laptop:

1. Create a private repository on GitHub (e.g. `github.com/jrdstall/tinkerspace-vault`).
2. Link your local vault to GitHub:
   ```powershell
   cd C:\Users\jrdst\software\IW\vault
   git remote add origin https://github.com/jrdstall/tinkerspace-vault.git
   git branch -M main
   git push -u origin main
   ```
3. On your tablet or laptop, clone that same repository into your Obsidian or tablet sync folder. Every write by Tinkerspace commits automatically to git!

---

## 04 · The Daily Innovation Rhythm

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
   │ 5. DISPATCH & COLLECT (/board, MCP, Chat, CLI Courier) │
   │    Execute activities with AI, collect & level up CML. │
   └────────────────────────────────────────────────────────┘
```

---

## 05 · Complete Maturation Playbook: From Idea to AI Dispatch to Results

This section details how to take an idea from a raw seedling (CML 1) through research, design, and validation using Tinkerspace workflows and external AI assistants.

### Step 1: Open the Plan Builder (`/ideas/{id}/plan`)
Navigate to any idea node (e.g. `IDEA-A01`) from the **Explore** page or the **Maturity Board**, and click **🎯 Plan Maturation**:

You have two ways to construct a plan:

#### Option A: 🤖 Auto-Drafting a Plan
- Select your target CML (e.g., advancing from **CML 1 &rarr; CML 2**, or **CML 2 &rarr; CML 3**).
- The planner inspects your idea's 4-score equalizer (`Novel`, `Works`, `Reach`, `Story`), spotlights the lowest-scoring dimension ("laggard"), and automatically sequences activities following the *"cheap and decisive first"* rule (e.g., Prior Art &rarr; Divergent Generation &rarr; Trade Study).

#### Option B: 🛠️ Custom Plan Builder
Build a bespoke workflow tailored to your exact project:
1. Click **+ Add Custom Step** to add as many activity cards as needed.
2. For each card:
   - **Step Title**: e.g., *"Comprehensive Patent & Prior Art Survey"*, *"Explore 5 Architecture Options"*, *"Draft Breadboard Test Plan"*.
   - **Activity Template**: Select from standard templates (`prior-art-survey@1`, `questionstorm@1`, `divergent-generation@1`, `trade-study@1`, `point-design@1`, `parts-and-skills-survey@1`, `experiment-design@1`) or choose `freeform@1`.
   - **Assignee**: Choose `Agent (AI)` for LLM research/synthesis, `Human (Jared)` for physical assembly/testing, or `Tool (Local)` for scripts.
   - **Estimated Duration**: Sized to 1–2 hour single-session blocks.
   - **Step Dependencies (Predecessors)**: Select which prior steps must finish before this step can begin (e.g., Step 2 depends on Step 1). Tinkerspace ensures dependent steps stay blocked until their inputs are ready.
   - **Custom Step Instructions (Optional)**: Type specific constraints, databases to search, part numbers, or focus areas. If left blank, Tinkerspace automatically populates the rich default instructions from the activity template.
3. Click **Generate Workflow**:
   - Tinkerspace creates a workflow container (`WFL-xxx`) in `vault/work/`.
   - Generates concrete units of work (`UOW-xxx`) with pre-compiled action guide prompts in `vault/work/UOW-xxx/action_guide.md`.
   - Immediately redirects you to the visual DAG diagram at `/workflow/WFL-xxx`.

---

### Step 2: Review & Edit Prompts (Action Guides)
Every generated unit of work has an **Action Guide** — a self-contained, high-context prompt that tells the AI (or human) exactly what to do.

#### What an Action Guide Contains:
- **Project Context**: Idea ID, title, domain, tags, and description.
- **Activity Objectives**: What this step accomplishes (e.g., finding prior patents, evaluating trade-offs, designing test circuits).
- **Core Rubric / Questions**: DARPA Heilmeier questions, evaluation criteria, and failure thresholds.
- **Output Schema**: The structured Markdown format and metadata header the deliverable must follow.

#### How to Edit Prompts In-Flight:
You don't need to re-create a plan if requirements change:
1. On the **Workflow page** (`/workflow/WFL-xxx`) or the **Work Board** (`/board`), locate the unit card.
2. Click **✏️ Edit Prompt**.
3. Add or modify instructions, search keywords, or special constraints in the text area.
4. Click **Save Action Guide** — your edits are instantly updated in `vault/work/UOW-xxx/unit.yaml` and saved to git.

---

### Step 3: Dispatching to Your AI Tool

Units on the **Work Board** (`/board`) are organized by state:
- **Blocked**: Waiting for upstream prerequisite steps to complete.
- **Ready**: Upstream dependencies are met. Ready for dispatch!
- **Dispatched / In Progress**: Currently being researched or executed.
- **Accepted / Done**: Deliverables collected and scores materialized.

Choose the dispatch method that fits your workflow:

#### 📋 Method 1: Copy-Paste Prompt (Claude, ChatGPT, or Antigravity Chat — Zero Setup)
This is the simplest, most versatile method for daily interactive work.

1. On `/board` or `/workflow/WFL-xxx`, locate your **Ready** unit.
2. Click **📋 Copy Prompt** (or highlight the Action Guide text).
3. Open your preferred AI tool (Claude Desktop, Antigravity chat, or ChatGPT).
4. **What to say to the AI**:
   ```text
   I am executing an innovation task for an idea in my Tinkerspace workspace. 
   Here is the complete context, objective, and action guide for this unit:

   [PASTE COPIED PROMPT HERE]

   Please thoroughly execute this research/analysis and produce the final deliverable 
   using the requested markdown structure with the deliverable metadata header.
   ```
5. **Interactive Pair Programming / Brainstorming**:
   - Chat back and forth with the AI! Push back on weak ideas, ask it to look up specific patents or datasheets, or have it compare alternative architectures.
   - When the analysis is solid, instruct the AI:
     *"Please generate the final deliverable markdown, including the YAML/comment header with your summary, verdict, and proposed scores."*

#### 🤖 Method 2: Automated MCP Server (Claude Desktop or Antigravity IDE)
If you use Claude Desktop or Antigravity IDE, Tinkerspace provides a native Model Context Protocol (MCP) server that lets the agent read tasks and submit deliverables automatically:

1. In your `claude_desktop_config.json` (or Antigravity MCP configuration):
   ```json
   {
     "mcpServers": {
       "tinkerspace": {
         "command": "C:\\Users\\jrdst\\software\\IW\\.venv\\Scripts\\python.exe",
         "args": ["-m", "iw.mcp.server", "--vault", "C:\\Users\\jrdst\\software\\IW\\vault"]
       }
     }
   }
   ```
2. In the AI chat, simply say:
   - *"List the ready units on my Tinkerspace work board."* &rarr; AI calls `list_steps()`.
   - *"Execute unit UOW-A01 for the cycle computer idea."* &rarr; AI calls `get_step("UOW-A01")`, conducts research, and calls `submit_result("UOW-A01", content=...)`.

#### 💻 Method 3: CLI Courier
You can also dispatch directly from your terminal:
```powershell
uv run python -m iw.adapters.couriers.cli_courier dispatch UOW-A01
```

---

### Step 4: Getting Results Back into Tinkerspace & Advancing CML

Once the AI produces the deliverable, bringing the results back into Tinkerspace takes just a few seconds.

#### 1. The Deliverable Format
A valid deliverable is a standard Markdown file containing a metadata header (either YAML frontmatter or an HTML comment block):

```markdown
<!--
unit: UOW-A01
summary: "Identified 3 key prior patents; memory-in-pixel display is fully unencumbered."
verdict: proceed
scores:
  novel: 3
  works: 3
-->

# Prior Art & Patent Landscape Survey: Handlebar Display

## 1. Executive Summary
Conducted patent database and literature search across USPTO, Espacenet, and Google Patents...

## 2. Identified Prior Art
1. **US Patent 7,123,456** (Garmin): Relates to transflective LCD backlights; expired 2021.
2. **EP Patent 2,987,654** (Wahoo): GPS cycle computer BLE synchronization. Does not cover low-power memory-in-pixel display circuitry.

## 3. Novelty & Freedom-to-Operate Assessment
No active patents restrict reflective Sharp memory LCD pairing with micro-power BLE SoC. Freedom-to-operate is clear.

## 4. Recommendations
Proceed to divergent architecture trade study (UOW-A02).
```

#### 2. Saving the Deliverable:
- Save the text above to `C:\Users\jrdst\software\IW\vault\work\UOW-A01\deliverable.md`.
- *(Optional)*: If the AI generated supporting files (e.g. `circuit_schematic.png`, `trade_matrix.csv`, or `bom.xlsx`), drop them directly into the same `vault/work/UOW-A01/` folder.

#### 3. Completing the Unit on the Work Board:
1. Open the Work Board (`/board`).
2. Click **📥 Collect / Complete** on the unit card.

#### 4. What Tinkerspace Does Automatically Upon Collection:
- **Extracts Structured Findings**: Reads the header for summary, verdict (`proceed`, `pivot`, `kill`), and score evaluations.
- **Catalogs Artifacts**: Automatically registers `deliverable.md` and any supporting images/CSVs as permanent Artifact nodes (`ART-xxx`) in your vault.
- **Materializes Facts onto the Idea**:
  - Links the artifacts to the Idea node (`IDEA-A01 --> [illustrates] --> ART-001`).
  - Appends the summary to the Idea's permanent activity log.
  - Updates the Idea's 4-score equalizer (`Novel`, `Works`, `Reach`, `Story`).
  - Automatically recalculates the idea's overall Concept Maturity Level (`min(scores)`).
- **Unblocks Downstream Steps**: Downstream units in the workflow whose dependencies are now fulfilled automatically transition from **Blocked** to **Ready**!

---

### Step 5: Reviewing the Maturing Idea
- Visit `/node/IDEA-A01`: See the updated CML badge, score equalizer, activity log, and clickable artifact links.
- Visit `/maturity`: Watch the idea card advance from CML 1 &rarr; CML 2 &rarr; CML 3 across the board columns.
- Visit `/board`: Pick up the newly unblocked downstream unit and dispatch the next phase of work!

---

## 06 · Individual Subsystem Reference

### A. Quick Capture (`Ctrl+K` or Header Button)
- **Shortcut**: Press `Ctrl+K` anywhere in the app to open the quick-capture modal.
- **Prompt Stems**: Click prompt buttons to kickstart capture:
  - `"I don't like..."` (Friction / Complaint)
  - `"There has to be a better way to..."` (Process / Tooling)
  - `"I wish..."` (Seedling Idea)
- **Submit**: Press `Enter` to send the thought directly into the append-only inbox.

### B. Fast Keyboard Triage (`/triage`)
Process your raw inbox efficiently without taking your hands off the keyboard:
- **`[A]` Accept**: Converts the raw thought into a permanent typed node in `vault/notes/`.
- **`[D]` Discard**: Cleanses noise or irrelevant snippets.
- **`[E]` Defer**: Keeps the item in the inbox for later review.
- **Editable Raw Text**: Edit typos or clarify wording directly in the raw capture box during triage before committing.
- **Searchable Edge Linker**: Search existing nodes by title or pick from dropdowns to link related nodes immediately.

### C. Intake & File Drop (`/intake`)
- **Drop Folder**: Drop PDF datasheets, tablet sketches, images, or Markdown files into `vault/inbox/drop/`.
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

### E. Question Graph & Inquiry Arc (`/question-graph/{id}`)
Deconstruct and expand upon any idea using Warren Berger's **Why &rarr; What If &rarr; How** inquiry arc:
- **Interactive Stems**: Click preset chips (*Why?*, *Why Must It Be?*, *Question Assumptions*, *Constraint Removal*, *Inversion*, *How Might We?*, *Harsh Critic*) or use *Blank Slate* to compose custom questions.
- **Visual DAG Viewport**: Interactive Mermaid flowchart diagram with full mouse drag-to-pan, wheel zoom, and reset/fit controls.
- **Sub-Question Scoping**: Questionstorming questions are preserved as focused idea sub-artifacts and excluded from the top-level Explore catalog.
- **Branch Follow-up**: Click *➕ Branch Follow-up* on any question card to seed child questions and build deep inquiry trees.

### F. Association Engine (`/associations`)
Uncover serendipitous, non-obvious cross-domain links:
- **Combinatorial Sampler**: Pairs ideas across disparate domains (e.g., cycling + solid-state energy).
- **Structural Sampler**: Identifies graph hubs and dangling nodes with few inbound connections.
- **Adversarial Judge**: Automatically scores candidate pairs on plausibility, surprise, and generative potential before presenting them.
- **Card Deck Interface**: Review generated candidate cards with one-click **Keep** (creates permanent typed edge) or **Discard**.

### G. Scout Standing Interests (`/scout`)
- Register long-term research topics (e.g., "Solid state cathode degradation").
- Specify domain and staleness intervals (e.g., 30 days).
- When an interest becomes stale, it surfaces on your home dashboard under **Recommended Activities** with one-click actions:
  - **Raise Sweep Order**: Dispatches an observation sweep workflow.
  - **Dismiss**: Resets the staleness interval clock.

---

## 07 · Vault Architecture Reference

All your data lives inside `vault/`:

```
vault/
├── notes/               # Permanent atomic Markdown nodes (IDEA-xxx, FRI-xxx, etc.)
├── work/                # Active and completed work units and workflows
│   ├── WFL-A01/         # workflow.yaml (DAG structure and dependencies)
│   └── UOW-A01/         # unit.yaml, action_guide.md, deliverable.md
├── inbox/
│   ├── raw.jsonl        # Append-only quick-capture inbox
│   └── drop/            # Drop folder for sketches, drawings, and external files
├── cas/                 # Bookkeeper content-addressed store (SHA-256 binary blobs)
├── meta/                # Scout interests, association state, index metadata
└── events.jsonl         # Append-only immutable system event log
```

---

## 08 · Quick Reference Keybindings & URLs

| Route | Purpose | Key Actions |
|---|---|---|
| `/` | **Explore & Search** | Full-text query, facet filtering, recent touches. |
| `/triage` | **Keyboard Triage** | `[A]` Accept, `[D]` Discard, `[E]` Defer. |
| `/maturity` | **Maturity Board** | CML columns, Worth Matrix, Laggard spotlight. |
| `/associations` | **Association Deck** | Keep/Discard serendipity card review. |
| `/board` | **Work Board** | Ready/Blocked units, prompt editing, dispatch, result collection. |
| `/ideas/{id}/plan` | **Plan Builder** | Auto-draft CML plans, custom step builder, instructions authoring. |
| `/question-graph/{id}` | **Question Graph** | Visual inquiry tree DAG, pan & zoom, Berger move composer. |
| `/scout` | **Scout Interests** | Register standing topics, review sweep recommendations. |
| `/intake` | **File Drop Intake** | Ingest sketches, PDFs, and tablet exports. |
| `Ctrl+K` | **Quick Capture** | Global hotkey to record raw thoughts. |

---

*Tinkerspace is your personal innovation engine — plan boldly, dispatch fearlessly, and let your ideas mature into reality!*
