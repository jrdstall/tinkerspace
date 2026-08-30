# BOARD — Subsystem Behaviour Specifications

BOARD-01  The Work Board (`/board`) displays active units grouped by lifecycle state into Ready Set, In Progress, Awaiting Review, and Parked sections.
BOARD-02  Ready unit cards prominently display the 5-point Action Guide banner (Assignee, Inputs, Task, Deliverable, Resume).
BOARD-03  Dispatching a ready unit from the board transitions state to `dispatched`, updates `unit.yaml`, logs the audit event, and updates the board.
BOARD-04  Parking a unit from the board transitions state to `parked`, removing it from the active ready set.
BOARD-05  Skipping a unit from the board transitions state to `skipped`, resolving downstream dependencies.
BOARD-06  The board operates without background watchers, loading state directly from vault disk, and provides an explicit Refresh State action to trigger sync and re-evaluate ready units.
