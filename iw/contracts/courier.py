"""Courier protocol definition."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CourierProtocol(Protocol):
    """Layer 3 courier adapter contract for transporting orders and results."""

    @property
    def name(self) -> str:
        """Unique identifier of the courier (e.g. 'mcp-pull', 'file-handoff')."""
        ...

    def deliver_order(self, unit_id: str, payload: dict[str, Any]) -> bool:
        """Transport work order to the destination worker."""
        ...

    def retrieve_result(self, unit_id: str) -> dict[str, Any] | None:
        """Retrieve output result files or status for an order."""
        ...
