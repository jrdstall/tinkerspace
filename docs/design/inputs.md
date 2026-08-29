---
id: DOC-inputs
type: artifact
title: Project Inputs (IN-01 to IN-04) — Innovator's Workspace
date: 2026-08-29
domain: meta
tags: [inputs, decisions, setup]
---

# Project Inputs (IN-01 to IN-04)

Documenting the initial environment, repository topology, and tooling decisions provided by Jared on 2026-08-29.

---

## IN-01 · Prototype Findings
- **Status:** Closed / Resolved.
- **Location:** `c:\Users\jrdst\software\innoworkspace`
- **Findings/Decision:** The prototype was exploratory evidence and a thinking tool. We will start fresh with a clean architecture; no code, data, or design artifacts are to be migrated from the prototype.

---

## IN-02 · Host & Environment Specifics
- **Status:** Closed / Resolved.
- **Workstation:** Windows 11 Home. Manually powered on/ensured running when conducting IW service work.
- **Laptop:** Windows 11 Pro. Used for development, browser interface access, and offline markdown writing.
- **Python Runtime:** Python 3.12+ managed via `uv` (one standalone binary on Windows, zero virtualenv friction).

---

## IN-03 · Repository & Workspace Topology
- **Status:** Closed / Resolved.
- **Code Repository (`iw-code`):** `tinkerspace` (`https://github.com/jrdstall/tinkerspace.git`) at `c:\Users\jrdst\software\tinkerspace`. Houses application server, MCP server, interfaces, tests, and design docs.
- **Datastore Repository (`iw-vault`):** Separate synced directory/git repo for the actual markdown notes, work units, and raw inbox files.

---

## IN-04 · Sync Service & Tablet Apps
- **Status:** Closed / Resolved.
- **File Sync Tool:** Syncthing (primary target: free, peer-to-peer, robust); Google Drive as evaluated fallback if needed.
- **Markdown Editor:** Obsidian installed on tablet and mobile devices to read and edit markdown notes in the synced store.
- **Sketching / Legacy Intake:** Samsung Notes on tablet (legacy notes to be manually transcribed/imported; drawings exported as PNG/SVG to sync folder).
