"""
pages/instrument_page.py

InstrumentMainPage — the Robot tab.

This file's only job is building the UI and wiring user actions to the
controller.  Business logic, settings I/O, and queue handling all live in
BasePage or InstrumentController.

Adding a new page to the application
-------------------------------------
1. Define your fields in a FieldRegistry subclass (models/fields.py pattern)
2. Create a controller (controllers/base_controller.py subclass)
3. Create this file — inherit BasePage, override _build_ui()
4. Register the page in Application (application.py)
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from typing import ClassVar

import customtkinter as ctk

from ..constants import FieldTypes as FT
from ..models.fields import FieldDef, FieldRegistry
from ..views import widgets as w
from ..views.base_page import BasePage
from ..views.dialogs import ErrorDialog
from ..controllers.instrument_controller import InstrumentController
from ..utils import TicketPurpose

if __name__ == "__main__":
    from ..utils import Ticket


# ---------------------------------------------------------------------------
# Field registry for this page
# ---------------------------------------------------------------------------

@dataclass
class InstrumentFields(FieldRegistry):
    """
    All fields on the Robot page.

    To add a field: add a FieldDef attribute here.
    The variable, settings persistence, and validation are automatic.
    """
    ip_address: FieldDef = field(
        default_factory=lambda: FieldDef(
            key="ip_address",
            label="Robot IP address",
            field_type=FT.string,
            default="198.168.0.1",
            required=True,
        )
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class InstrumentMainPage(BasePage):

    SETTINGS_FILE: ClassVar[str] = "instruments_settings.json"

    def __init__(self, *args, **kwargs) -> None:
        # Registry must be set before super().__init__ so BasePage can
        # build vars and load settings before _build_ui() is called.
        self._registry = InstrumentFields()
        super().__init__(*args, **kwargs)

        # Controller is created after super().__init__ because it needs
        # self._message_queue which BasePage creates.
        self._controller = InstrumentController(self._message_queue)

    # ------------------------------------------------------------------
    # UI construction  (called by BasePage.__init__ after vars are ready)
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=9)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_connection_frame()
        self._build_main_frame()
        self._build_status_frame()

    def _build_connection_frame(self) -> None:
        self._connection_frame = w.LabelFrame(self, label_text="Connection")
        self._connection_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)

        content = self._connection_frame.content
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)

        fd = self._registry.ip_address
        w.LabelInput(
            content,
            label_text=fd.label,
            var=self._vars[fd.key],
            field_spec=fd.as_field_spec(),
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self._connect_btn = ctk.CTkButton(
            content, text="Connect", command=self._on_connect
        )
        self._connect_btn.grid(row=0, column=1, padx=(0, 4), pady=4)

    def _build_main_frame(self) -> None:
        self._main_frame = w.LabelFrame(self, label_text="Main")
        self._main_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        # Add instrument-specific controls into self._main_frame.content

    def _build_status_frame(self) -> None:
        self._status_frame = w.LabelFrame(self, label_text="Status")
        self._status_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)

        self._status_var = tk.StringVar(
            value="Enter the IP address and hit Connect"
        )
        content = self._status_frame.content
        content.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            content, textvariable=self._status_var, anchor="w"
        ).grid(row=0, column=0, sticky="nsew", padx=4, pady=2)

    # ------------------------------------------------------------------
    # Ticket handling (override BasePage hook)
    # ------------------------------------------------------------------

    def _on_ticket(self, ticket) -> None:
        """Handle tickets beyond status updates."""
        if ticket.ticket_type == TicketPurpose.EXECUTION_COMPLETED:
            # Re-enable UI when an async action finishes
            self._set_connected_state(connected=True)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        if self._controller.is_connected:
            self._controller.disconnect()
            self._set_connected_state(connected=False)
            return

        # Validate UI fields first (shows inline errors)
        errors = self._get_errors()
        if errors:
            field_list = "\n  • ".join(errors.keys())
            self._set_status(
                "Cannot connect — errors in: " + ", ".join(errors.keys())
            )
            ErrorDialog(
                parent=self.winfo_toplevel(),
                title="Connection Error",
                message=(
                    "Cannot connect to the robot.\n\n"
                    "The following fields have errors:\n  • " + field_list
                ),
            )
            return

        # Hand off to controller with plain Python values
        params = self.get_values()
        success = self._controller.connect(params)
        self._set_connected_state(connected=success)

    def _set_connected_state(self, *, connected: bool) -> None:
        """Update button label and input states to reflect connection."""
        self._connect_btn.configure(text="Disconnect" if connected else "Connect")
        state = "disabled" if connected else "normal"
        self._set_inputs_state(state, self._connection_frame.content)
