"""
controllers/instrument_controller.py

Concrete controller for the Robot instrument page.

This is the ONLY file that knows about hardware-specific logic.
The page calls connect() / disconnect() — it never touches the hardware itself.
"""

from __future__ import annotations

from queue import Queue
from typing import Any

from .base_controller import BaseController


class InstrumentController(BaseController):
    """
    Controller for a robot connected over IP.

    Replace the body of _do_connect / _do_disconnect with real SDK calls.
    """

    def __init__(self, message_queue: Queue) -> None:
        super().__init__(message_queue)
        self._connection = None   # replace with your SDK connection object

    # ------------------------------------------------------------------
    # Param validation (pure logic — no UI)
    # ------------------------------------------------------------------

    def _validate_params(self, params: dict[str, Any]) -> dict[str, str]:
        errors: dict[str, str] = {}
        ip = params.get("ip_address", "").strip()
        if not ip:
            errors["ip_address"] = "IP address is required"
        elif not _is_valid_ip(ip):
            errors["ip_address"] = f"{ip!r} is not a valid IP address"
        return errors

    # ------------------------------------------------------------------
    # Hardware calls
    # ------------------------------------------------------------------

    def _do_connect(self, params: dict[str, Any]) -> None:
        ip = params["ip_address"]
        self._post_progress(f"Connecting to {ip}…")
        # TODO: replace with real connection
        # self._connection = RobotSDK.connect(ip)

    def _do_disconnect(self) -> None:
        # TODO: replace with real teardown
        # self._connection.close()
        self._connection = None

    def _do_execute(self, params: dict[str, Any]) -> None:
        # TODO: implement robot action
        self._post_progress("Running…")
        # self._connection.run()
        self._post_completed("Finished")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
