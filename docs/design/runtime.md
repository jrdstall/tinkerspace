---
id: DOC-runtime
type: artifact
title: Runtime Environment and Operational Architecture
date: 2026-08-29
domain: meta
tags: [runtime, environment, deployment, security]
---

# Runtime Environment & Operational Architecture

**Single-process ASGI architecture, local network access, Windows service lifecycle, and security boundaries.**

Governed by `docs/InnovatorsWorkspaceVision_12.md` §07, §10, D18, D20 and `docs/DesignPhasePlan_2.md` A2, A3, A4, A10.

---

## 01 · Repository and Storage Layout

Two separate repositories/directories:
1. **`iw-code` (`tinkerspace`)**:
   - Location: `c:\Users\jrdst\software\tinkerspace`
   - Remote: `https://github.com/jrdstall/tinkerspace.git`
   - Holds Python application code, MCP server, Jinja templates, tests, and design docs.
2. **`iw-vault` (Datastore)**:
   - Synced folder holding all note markdown files, inbox items, and work unit folders (`work/UOW-xxx/`).
   - Synced continuously across Workstation, Laptop, and Tablet (via Syncthing).
   - Git runs on the Workstation only; `.git/` is explicitly excluded from sync.

---

## 02 · Starting and Running the Service

The system runs as a single unified ASGI process hosting both the Web UI and the MCP endpoint (A4).

### Running on the Windows Workstation
```powershell
# In c:\Users\jrdst\software\tinkerspace
uv run uvicorn iw.web.app:app --host 0.0.0.0 --port 8000
```

### Windows Startup & Reboot Behavior
- The service is run on-demand or via a Windows shortcut in the Startup folder (`shell:startup`) pointing to a PowerShell launcher script.
- If the machine reboots or sleeps, the service stops safely without data corruption because:
  - All writes to markdown files and YAML are atomic.
  - There is no background caching daemon, timer, or unpersisted state in memory.
  - The derived index is rebuilt from disk on next launch.

---

## 03 · Network Access & D18 Security Decision

### Trusted Single-User Network (D18)
Per Decision D18 in the Vision document:
- The service is accessible across the local home network (Workstation IP port 8000) or via Tailscale.
- There is no multi-user authentication gate in Phase 1; any network request reaching the service is assumed to be Jared.
- *Accepted Risk:* Running on a trusted LAN without an authentication gate is accepted for personal single-user operation. A simple token/passphrase header can be added later if exposed outside the home network.

---

## 04 · The Environment Rule: The Tool Wall Outside the Codebase

Per V§14.6 and Design Plan §10:
> **The MCP surface is a wall, not a window.** The wall is worthless if another tool opens a door beside it.

**Standing System Rule:**
No note-taking application plugin (e.g., Obsidian community plugins), CLI utility, or background daemon that exposes the vault folder to unconstrained AI search, directory traversal, or arbitrary code execution may be installed or activated on any machine that can see the `iw-vault` directory.
