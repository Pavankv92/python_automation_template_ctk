"""
models/fields.py

FieldDef — the single source of truth for every form field in the application.

This module is pure Python: no tkinter, no customtkinter.  That makes it
testable without a display and reusable in non-GUI contexts (CLI, REST API).

Tk variables are created on demand by the view layer (BasePage), not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..constants import FieldTypes as FT


@dataclass
class FieldDef:
    """
    Describes one form field completely.

    Attributes
    ----------
    key         : str       — machine name, used as dict key everywhere
    label       : str       — human-readable label shown in the UI
    field_type  : FT        — controls which widget LabelInput builds
    default     : Any       — seed value; also written to settings file
    required    : bool      — must be non-empty before an action is taken
    min         : Any|None  — lower bound (numeric fields only)
    max         : Any|None  — upper bound (numeric fields only)
    increment   : Any|None  — step size  (numeric fields only)
    values      : list|None — allowed values (combobox / radio group only)

    Notes
    -----
    storage_type is derived automatically from field_type so you never have
    to keep them in sync manually.
    """

    key:        str
    label:      str
    field_type: FT
    default:    Any       = ""
    required:   bool      = True
    min:        Any       = None
    max:        Any       = None
    increment:  Any       = None
    values:     list|None = None

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def storage_type(self) -> str:
        """
        JSON-serialisable type string understood by SettingsModel.

        Derived from field_type so there is only one place to update
        when a new FieldTypes member is added.
        """
        _map: dict[FT, str] = {
            FT.string:            "str",
            FT.long_string:       "str",
            FT.string_list:       "str",
            FT.short_string_list: "str",
            FT.iso_date_string:   "str",
            FT.decimal:           "float",
            FT.integer:           "int",
            FT.boolean:           "bool",
        }
        return _map.get(self.field_type, "str")

    # ------------------------------------------------------------------
    # Conversion helpers used by the view / settings layers
    # ------------------------------------------------------------------

    def as_settings_dict(self) -> dict[str, Any]:
        """Format expected by SettingsModel: {"type": ..., "value": ...}."""
        return {"type": self.storage_type, "value": self.default}

    def as_field_spec(self) -> dict[str, Any]:
        """
        Format expected by LabelInput(field_spec=...).

        LabelInput uses this to resolve widget class and constraints.
        """
        spec: dict[str, Any] = {"type": self.field_type}
        if self.min      is not None: spec["min"]       = self.min
        if self.max      is not None: spec["max"]       = self.max
        if self.increment is not None: spec["inc"]      = self.increment
        if self.values   is not None: spec["values"]    = self.values
        return spec


# ---------------------------------------------------------------------------
# Field registry
# ---------------------------------------------------------------------------

@dataclass
class FieldRegistry:
    """
    Ordered collection of FieldDef objects for one page.

    Usage
    -----
        class MyPageFields(FieldRegistry):
            ip_address: FieldDef = field(default_factory=lambda: FieldDef(
                key="ip_address",
                label="Robot IP address",
                field_type=FT.string,
                default="198.168.0.1",
            ))

    The base class provides iteration and conversion helpers so pages
    never need to maintain parallel dicts.
    """

    def all(self) -> list[FieldDef]:
        """Return all FieldDef fields in definition order."""
        import dataclasses
        return [
            getattr(self, f.name)
            for f in dataclasses.fields(self)
            if isinstance(getattr(self, f.name), FieldDef)
        ]

    def by_key(self) -> dict[str, FieldDef]:
        """Return {field.key: FieldDef} mapping."""
        return {fd.key: fd for fd in self.all()}

    def as_settings_fields(self) -> dict[str, dict]:
        """Convert all fields to the format SettingsModel expects."""
        return {fd.key: fd.as_settings_dict() for fd in self.all()}
