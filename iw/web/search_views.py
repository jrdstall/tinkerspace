"""Node search API web views for autocomplete pickers.

Layer 4 Web surface module.
Governed by TRIAGE-07 and EXPLORE-09.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from iw.contracts.store import StoreProtocol
from iw.core.index import InMemoryIndex


async def api_node_search_view(request: Request) -> Response:
    """API endpoint returning scored node matches for interactive search pickers."""
    store: StoreProtocol = request.app.state.store
    query = request.query_params.get("q", "").strip()
    exclude_id = request.query_params.get("exclude", "").strip()
    raw_limit = request.query_params.get("limit", "15").strip()

    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 15

    store.sync_refresh()
    nodes = store.list_nodes()
    index = InMemoryIndex(nodes)
    results = index.search_for_picker(query=query, exclude_id=exclude_id, limit=limit)
    return JSONResponse(results)
