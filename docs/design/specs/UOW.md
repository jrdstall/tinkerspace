# UOW — Subsystem Behaviour Specifications

UOW-01  A unit of work is stored in structured `work/<UOW-id>/unit.yaml`, not as a markdown node note.
UOW-02  A unit of work has one of seven explicit states: `blocked`, `ready`, `dispatched`, `returned`, `accepted`, `skipped`, `parked`.
UOW-03  State transitions enforce valid state machine paths and reject illegal transitions with an error.
UOW-04  Writing `unit.yaml` is atomic via temporary file and rename, and reads never cache across requests.
UOW-05  State transitions emit immutable `unit.state_changed` audit records to the event log.
UOW-06  Unit lookups by ID are case-insensitive on input (`uow-a01` matches `UOW-A01`).
UOW-07  Scanning units discovers all `work/UOW-*/unit.yaml` folders across the vault on demand.
UOW-08  Every unit write and state transition requires explicit author attribution (`author.kind` required).
