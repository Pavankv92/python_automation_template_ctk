"""
controllers/base_controller.py

BaseController — base class for all hardware/connection controllers.

Responsibilities
----------------
- Owns the connection state machine (disconnected → connecting → connected)
- Posts Ticket messages to the page's queue (never touches tk widgets directly)
- Exposes a clean interface the page can call: connect(), disconnect(), etc.

What BaseController does NOT do
---------------------------------
- Import or reference any CTk / tk widget
- Read tk variables directly (it receives plain Python values from the page)

This separation means controllers are fully testable without a display.
"""

from __future__ import annotations

from enum import Enum, auto
from queue import Queue
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..utils import Ticket, TicketPurpose


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING   = auto()
    CONNECTED    = auto()
    ERROR        = auto()


class BaseController:
    """
    Inherit this for every instrument / hardware controller.

    Parameters
    ----------
    message_queue : Queue[Ticket]
        The page's queue.  Post tickets here; never call tk directly.

    Subclass contract
    -----------------
    Required overrides:
        _do_connect(params)    — perform the actual connection; raise on failure
        _do_disconnect()       — tear down the connection

    Optional overrides:
        _do_execute(params)    — run the main action
        _validate_params(p)    — return {key: error} before connecting

    Example::

        class RobotController(BaseController):
            def _do_connect(self, params):
                self._robot = Robot(params["ip_address"])
                self._robot.connect()

            def _do_disconnect(self):
                self._robot.disconnect()
    """

    def __init__(self, message_queue: "Queue[Ticket]") -> None:
        self._queue = message_queue
        self._state = ConnectionState.DISCONNECTED

    # ------------------------------------------------------------------
    # Public API (called by the page)
    # ------------------------------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    def connect(self, params: dict[str, Any]) -> bool:
        """
        Validate params, then attempt connection.
        Returns True on success.  Posts status tickets throughout.
        """
        errors = self._validate_params(params)
        if errors:
            self._post_error(
                "Cannot connect — invalid parameters:\n  • "
                + "\n  • ".join(f"{k}: {v}" for k, v in errors.items())
            )
            return False

        self._set_state(ConnectionState.CONNECTING)
        self._post_status("Connecting…")
        try:
            self._do_connect(params)
            self._set_state(ConnectionState.CONNECTED)
            self._post_status("Connected")
            return True
        except Exception as exc:
            self._set_state(ConnectionState.ERROR)
            self._post_error(f"Connection failed: {exc}")
            return False

    def disconnect(self) -> None:
        """Tear down the connection and reset state."""
        if not self.is_connected:
            return
        try:
            self._do_disconnect()
        finally:
            self._set_state(ConnectionState.DISCONNECTED)
            self._post_status("Disconnected")

    def execute(self, params: dict[str, Any] | None = None) -> None:
        """Run the main action (optional — not all controllers need this)."""
        if not self.is_connected:
            self._post_error("Not connected")
            return
        try:
            self._do_execute(params or {})
        except Exception as exc:
            self._post_error(f"Execution failed: {exc}")

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _validate_params(self, params: dict[str, Any]) -> dict[str, str]:
        """Override to validate connection params. Return {key: error}."""
        return {}

    def _do_connect(self, params: dict[str, Any]) -> None:
        raise NotImplementedError

    def _do_disconnect(self) -> None:
        raise NotImplementedError

    def _do_execute(self, params: dict[str, Any]) -> None:
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_state(self, state: ConnectionState) -> None:
        self._state = state

    def _post_status(self, message: str) -> None:
        from ..utils import Ticket, TicketPurpose
        self._queue.put(Ticket(TicketPurpose.UPDATE_STATUS, message))

    def _post_error(self, message: str) -> None:
        from ..utils import Ticket, TicketPurpose
        self._queue.put(Ticket(TicketPurpose.ERROR_MESSAGE, message))

    def _post_progress(self, message: str) -> None:
        from ..utils import Ticket, TicketPurpose
        self._queue.put(Ticket(TicketPurpose.UPDATE_PROGRESS, message))

    def _post_completed(self, message: str = "Done") -> None:
        from ..utils import Ticket, TicketPurpose
        self._queue.put(Ticket(TicketPurpose.EXECUTION_COMPLETED, message))
