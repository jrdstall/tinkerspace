"""Unit-of-work state machine and lifecycle transition engine.

Enforces valid lifecycle transitions defined in DA-09 §01 and updates store state atomically.
"""

from iw.contracts.models import Author, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol

VALID_TRANSITIONS: dict[UnitState, set[UnitState]] = {
    UnitState.BLOCKED: {UnitState.READY, UnitState.PARKED, UnitState.SKIPPED},
    UnitState.READY: {UnitState.DISPATCHED, UnitState.PARKED, UnitState.SKIPPED, UnitState.ACCEPTED},
    UnitState.DISPATCHED: {UnitState.RETURNED, UnitState.READY, UnitState.PARKED, UnitState.ACCEPTED},
    UnitState.RETURNED: {UnitState.ACCEPTED, UnitState.READY, UnitState.PARKED, UnitState.SKIPPED},
    UnitState.PARKED: {UnitState.READY, UnitState.BLOCKED},
    UnitState.ACCEPTED: set(),
    UnitState.SKIPPED: set(),
}


def can_transition(current_state: UnitState, target_state: UnitState) -> bool:
    """Check whether a transition between two unit states is permitted."""
    allowed = VALID_TRANSITIONS.get(current_state, set())
    return target_state in allowed


def transition_unit_state(
    unit: UnitOfWork,
    target_state: UnitState,
    author: Author,
    store: StoreProtocol,
) -> UnitOfWork:
    """Transition a unit of work to a target state, validating against the lifecycle machine."""
    if not author or not author.kind:
        raise ValueError("Author with kind is required on unit state transition (UOW-08)")

    if not can_transition(unit.state, target_state):
        raise ValueError(
            f"Invalid state transition from '{unit.state.value}' to '{target_state.value}' (UOW-03)"
        )

    unit.state = target_state
    saved_unit = store.write_unit(unit, author=author)
    return saved_unit
