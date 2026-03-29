"""
views/base_page.py

BasePage — inherit this for every tab/page in the application.

Responsibilities
----------------
- Owns the tk variable dict (_vars) and creates them from a FieldRegistry
- Handles settings load / save against a SettingsModel
- Owns the thread-safe message queue and <<CheckQueue>> binding
- Provides _get_errors() for form validation
- Provides make_read_only() / make_editable() for bulk input state changes

What BasePage does NOT do
--------------------------
- Build any UI (that is the subclass's job)
- Know anything about hardware or connections (that is the controller's job)
"""

from __future__ import annotations

import tkinter as tk
from queue import Queue
from typing import TYPE_CHECKING, Any, ClassVar

import customtkinter as ctk

from ..models.fields import FieldRegistry, FieldDef
from ..models.base import SettingsModel          # existing SettingsModel
from ..utils import TicketHandler, TicketPurpose
from . import widgets as w

if TYPE_CHECKING:
    from ..utils import Ticket


# Tk variable type — maps storage_type string → tk.Variable subclass
_VAR_TYPES: dict[str, type] = {
    "str":   tk.StringVar,
    "int":   tk.IntVar,
    "float": tk.DoubleVar,
    "bool":  tk.BooleanVar,
}


class BasePage(w.Frame):
    """
    Base class for all application pages (notebook tabs).

    Subclass contract
    -----------------
    Required:
        SETTINGS_FILE : ClassVar[str]   — filename for JSON settings
        _registry     : FieldRegistry   — created in __init__ before super()

    Optional overrides:
        _build_ui()              — build all widgets (called by BasePage.__init__)
        _on_ticket(ticket)       — handle a single ticket from the queue
        _extra_validation()      — return additional {key: error} beyond fields

    Minimal subclass example::

        class MyPage(BasePage):
            SETTINGS_FILE = "my_settings.json"

            def __init__(self, *args, **kwargs):
                self._registry = MyPageFields()
                super().__init__(*args, **kwargs)

            def _build_ui(self):
                frame = w.LabelFrame(self, label_text="Settings")
                frame.grid(row=0, column=0, sticky="nsew")
                w.LabelInput(
                    frame.content,
                    label_text=self._registry.ip_address.label,
                    var=self._vars["ip_address"],
                    field_spec=self._registry.ip_address.as_field_spec(),
                ).grid(row=0, column=0)
    """

    SETTINGS_FILE: ClassVar[str] = "settings.json"

    def __init__(self, *args, **kwargs) -> None:
        # _registry must be set by the subclass before calling super().__init__
        if not hasattr(self, "_registry"):
            raise TypeError(
                f"{type(self).__name__} must set self._registry "
                "before calling super().__init__()"
            )

        super().__init__(*args, **kwargs)

        # --- Settings model -------------------------------------------
        self._settings_model = SettingsModel(
            fields=self._registry.as_settings_fields(),
            file_name=self.SETTINGS_FILE,
        )

        # --- Tk variables (one per field, correct type) ---------------
        self._vars: dict[str, tk.Variable] = self._make_vars()
        self._load_settings()

        # --- Message queue --------------------------------------------
        self._message_queue: Queue[Ticket] = Queue()
        self._ticket_handler = TicketHandler(
            message_queue=self._message_queue, event_widget=self
        )
        self.bind("<<CheckQueue>>", self._check_queue)

        # --- Build UI -------------------------------------------------
        self._build_ui()

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Override to construct all widgets."""
        pass

    def _on_ticket(self, ticket: "Ticket") -> None:
        """
        Override to handle tickets beyond the default status update.

        The base implementation handles UPDATE_STATUS, EXECUTION_COMPLETED,
        ERROR_MESSAGE, and UPDATE_PROGRESS by calling _set_status().
        Call super()._on_ticket(ticket) to keep that behaviour.
        """
        pass

    def _extra_validation(self) -> dict[str, str]:
        """
        Override to add page-specific validation beyond required fields.
        Return {field_key: error_message} for any failures.
        """
        return {}

    # ------------------------------------------------------------------
    # Variable management
    # ------------------------------------------------------------------

    def _make_vars(self) -> dict[str, tk.Variable]:
        """Create one tk.Variable per field, seeded with its default."""
        vars_: dict[str, tk.Variable] = {}
        for fd in self._registry.all():
            cls = _VAR_TYPES.get(fd.storage_type, tk.StringVar)
            vars_[fd.key] = cls(value=fd.default)
        return vars_

    def get_var(self, key: str) -> tk.Variable:
        """Type-safe accessor — raises KeyError with a clear message."""
        if key not in self._vars:
            raise KeyError(
                f"No variable {key!r} on {type(self).__name__}. "
                f"Available: {list(self._vars)}"
            )
        return self._vars[key]

    def get_values(self) -> dict[str, Any]:
        """Return {key: current_value} for all fields."""
        return {k: v.get() for k, v in self._vars.items()}

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Restore saved values into tk vars and wire save traces."""
        for fd in self._registry.all():
            saved = self._settings_model.fields.get(fd.key, {}).get("value")
            if saved is not None:
                try:
                    self._vars[fd.key].set(saved)
                except tk.TclError:
                    pass  # saved value incompatible with var type — use default

        for var in self._vars.values():
            var.trace_add("write", self._save_settings)

    def _save_settings(self, *_) -> None:
        """Persist all current values to the settings file."""
        for key, var in self._vars.items():
            try:
                self._settings_model.set(key, var.get())
            except tk.TclError:
                pass
        self._settings_model.save()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _get_errors(self) -> dict[str, str]:
        """
        Trigger focus-out validation on every LabelInput-backed var.
        Returns {field_key: error_message} for any failures.
        Merges results from _extra_validation().
        """
        errors: dict[str, str] = {}

        for key, var in self._vars.items():
            label_widget = getattr(var, "label_widget", None)
            if label_widget is None:
                continue
            inp = getattr(label_widget, "input", None)
            if inp and hasattr(inp, "trigger_focusout_validation"):
                inp.trigger_focusout_validation()
            error_var = getattr(label_widget, "error", None)
            if error_var and error_var.get():
                errors[key] = error_var.get()

        errors.update(self._extra_validation())
        return errors

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _set_inputs_state(self, state: str, frame: ctk.CTkFrame) -> None:
        """Set state on all non-button LabelInput children of a frame."""
        for child in frame.winfo_children():
            inp = getattr(child, "input", None)
            if inp is None or isinstance(inp, ctk.CTkButton):
                continue
            try:
                inp.configure(state=state)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, message: str) -> None:
        """Update the status variable if the subclass defined one."""
        if hasattr(self, "_status_var"):
            self._status_var.set(message)

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    _STATUS_TICKETS: ClassVar[frozenset] = frozenset({
        TicketPurpose.UPDATE_STATUS,
        TicketPurpose.EXECUTION_COMPLETED,
        TicketPurpose.ERROR_MESSAGE,
        TicketPurpose.UPDATE_PROGRESS,
    })

    def _check_queue(self, event) -> None:
        """Drain the full queue on each <<CheckQueue>> event."""
        while not self._message_queue.empty():
            ticket = self._message_queue.get()
            if ticket.ticket_type in self._STATUS_TICKETS:
                self._set_status(ticket.ticket_value)
            self._on_ticket(ticket)
