"""
constants.py

Project-wide enumerations.  This module has NO imports from the project —
it is safe to import from anywhere without creating circular dependencies.
"""

from enum import Enum, auto


class FieldTypes(Enum):
    """
    Logical data type of a form field.

    Used by:
      - FieldDef  (models/fields.py)  to describe storage type
      - FIELD_WIDGET_MAP (views/widgets.py) to select the correct CTk widget
    """

    # Text
    string            = auto()   # single-line required text
    long_string       = auto()   # multi-line (CTkTextbox)

    # Constrained text
    string_list       = auto()   # dropdown (ValidatedCombobox)
    short_string_list = auto()   # radio group (ValidatedRadioGroup)
    iso_date_string   = auto()   # YYYY-MM-DD (DateEntry)

    # Numeric
    decimal           = auto()   # float (ValidatedSpinbox, number_type="float")
    integer           = auto()   # int   (ValidatedSpinbox, number_type="integer")

    # Boolean
    boolean           = auto()   # checkbox (CTkCheckBox)

    def __str__(self) -> str:
        return self.name
