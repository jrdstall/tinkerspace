# SCOUT — Behaviour Specification

This specification defines the behavior of the Scout standing interests and recommended activities service in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §08, §10, §14.4, and `docs/design/DA-04-components.md`.

---

## SCOUT — Behaviour

SCOUT-01  Standing interests register a research topic, target domain, optional subject idea link, tags, and a staleness interval in days.
SCOUT-02  Staleness evaluations and recommendations are computed strictly on-demand upon page load or API request without background daemons, schedulers, or file system watchers (V§14.4).
SCOUT-03  A standing interest becomes a Recommended Activity offer when `(now - max(last_swept_at, last_dismissed_at, created_at)).days >= staleness_interval_days`.
SCOUT-04  Dismissing an offer updates `last_dismissed_at` to the current timestamp, immediately clearing the offer until its interval expires again.
SCOUT-05  Dispatching a sweep updates `last_swept_at` to the current timestamp and raises an observation sweep or prior-art survey workflow order.
SCOUT-06  Deactivating a standing interest marks it inactive and excludes it from future recommendation evaluations without destroying historical records.
