"""
widgets_ctk.py

Migration of widgets.py from tkinter/ttk to CustomTkinter (CTk).

Key differences vs. the original:
  - ttk.Style-based validation colouring is replaced with direct fg_color /
    text_color keyword args on each CTk widget.
  - CTk widgets do not accept validate= / validatecommand=; validation is wired
    through textvariable traces and <FocusOut> / <Key> bindings instead.
  - ttk.Spinbox has no CTk equivalent; ValidatedSpinbox keeps ttk.Spinbox as
    the inner widget but lives inside a CTkFrame so it blends visually.
  - ttk.LabelFrame → CTkFrame with an overlaid CTkLabel for the group title.
  - BoundText uses CTkTextbox instead of tk.Text.
"""

import tkinter as tk
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import customtkinter as ctk

from ..constants import FieldTypes as FT

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
_NORMAL_BG = ("white", "#2b2b2b")  # (light-mode, dark-mode) field bg
_ERROR_BG = ("darkred", "#7a0000")
_NORMAL_FG = ("black", "white")
_ERROR_FG = ("white", "white")
_ERROR_LABEL = ("darkred", "#ff6b6b")


class Frame(ctk.CTkFrame):
    """Drop-in replacement for the original ttk.Frame subclass."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _add_frame(self, label_text: str) -> "LabelFrame":
        frame = LabelFrame(self, label_text=label_text)
        frame.grid(sticky="nsew")
        # Return the inner content frame so callers grid widgets
        # into it directly without risking title overlap.
        return frame.content


class LabelFrame(ctk.CTkFrame):
    """
    CTk equivalent of ttk.LabelFrame.

    The title label is pinned to row 0; all child widgets should be placed
    inside ``self.content`` (a transparent CTkFrame that occupies row 1 and
    expands to fill the remaining space).  This prevents any child widget
    from overlapping the title.

    Usage
    -----
        group = LabelFrame(parent, label_text="Settings")
        ctk.CTkLabel(group.content, text="Hello").grid(row=0, column=0)
    """

    def __init__(self, *args, label_text: str = "", **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.rowconfigure(0, weight=0)  # title row  – fixed height
        self.rowconfigure(1, weight=1)  # content row – expands
        self.columnconfigure(0, weight=1)

        if label_text:
            self._title = ctk.CTkLabel(
                self,
                text=label_text,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            )
            self._title.grid(row=0, column=0, padx=10, pady=(6, 0), sticky="w")

        # Inner frame where callers place their widgets
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, padx=6, pady=(2, 6), sticky="nsew")


# ---------------------------------------------------------------------------
# Validation mixin (rewritten for CTk)
# ---------------------------------------------------------------------------


class ValidatedMixin:
    """
    Adds validation to a CTk input widget.

    Because CTk widgets do not expose validate= / validatecommand=, validation
    is driven by:
      • <Key>      → _key_validate()
      • <FocusOut> → _focusout_validate()
    """

    def __init__(self, *args, error_var=None, **kwargs) -> None:
        self.error = error_var or tk.StringVar()
        super().__init__(*args, **kwargs)
        self.bind("<Key>", self._on_key)
        self.bind("<FocusOut>", self._on_focusout)

    # ------------------------------------------------------------------
    # Internal event handlers
    # ------------------------------------------------------------------

    def _on_key(self, event) -> None:
        widget = event.widget
        current = self._get_value()
        char = event.char
        index = str(widget.index(tk.INSERT)) if hasattr(widget, "index") else "0"
        action = "1"  # insert

        self.error.set("")
        valid = self._key_validate(
            proposed=current + char,
            current=current,
            char=char,
            event="key",
            index=index,
            action=action,
        )
        self._set_error_style(not valid)
        if not valid:
            self._key_invalid(
                proposed=current + char,
                current=current,
                char=char,
                event="key",
                index=index,
                action=action,
            )
            # Prevent the character from being inserted
            return "break"

    def _on_focusout(self, event) -> None:
        self.error.set("")
        valid = self._focusout_validate(event="focusout")
        self._set_error_style(not valid)
        if not valid:
            self._focusout_invalid(event="focusout")

    def _set_error_style(self, on: bool) -> None:
        """Switch the widget's colours to indicate an error state."""
        try:
            if on:
                self.configure(fg_color=_ERROR_BG, text_color=_ERROR_FG)
            else:
                self.configure(fg_color=_NORMAL_BG, text_color=_NORMAL_FG)
        except Exception:
            pass  # not all widgets support both kwargs

    def _get_value(self) -> str:
        """Return the current string value of the widget."""
        try:
            return self.get()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Override these in subclasses
    # ------------------------------------------------------------------

    def _focusout_validate(self, **kwargs) -> bool:
        return True

    def _key_validate(self, **kwargs) -> bool:
        return True

    def _focusout_invalid(self, **kwargs) -> None:
        pass

    def _key_invalid(self, **kwargs) -> None:
        pass

    def trigger_focusout_validation(self) -> bool:
        valid = self._focusout_validate(event="focusout")
        self._set_error_style(not valid)
        if not valid:
            self._focusout_invalid(event="focusout")
        return valid


# ---------------------------------------------------------------------------
# Concrete validated widgets
# ---------------------------------------------------------------------------


class DateEntry(ValidatedMixin, ctk.CTkEntry):
    """CTkEntry that only accepts YYYY-MM-DD dates."""

    def _key_validate(self, action: str, index: str, char: str, **kwargs) -> bool:
        if action == "0":
            return True
        if index in ("0", "1", "2", "3", "5", "6", "8", "9"):
            return char.isdigit()
        if index in ("4", "7"):
            return char == "-"
        return False

    def _focusout_validate(self, event=None, **kwargs) -> bool:
        value = self.get()
        if not value:
            self.error.set("A value is required")
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            self.error.set("Invalid date")
            return False
        return True


class RequiredEntry(ValidatedMixin, ctk.CTkEntry):
    """CTkEntry that requires a non-empty value on focus-out."""

    def _focusout_validate(self, event=None, **kwargs) -> bool:
        if not self.get():
            self.error.set("A value is required")
            return False
        return True


class ValidatedCombobox(ValidatedMixin, ctk.CTkComboBox):
    """
    CTkComboBox with autocomplete-style key validation.

    Note: CTkComboBox uses a `command` callback (called on selection) and
    `values` list.  The textvariable is set via the `variable` kwarg.
    """

    def _key_validate(self, proposed: str, action: str, **kwargs) -> bool:
        if action == "0":
            self.set("")
            return True
        values = self.cget("values") or []
        matching = [x for x in values if x.lower().startswith(proposed.lower())]
        if not matching:
            return False
        if len(matching) == 1:
            self.set(matching[0])
            return False
        return True

    def _focusout_validate(self, event=None, **kwargs) -> bool:
        if not self.get():
            self.error.set("A value is required")
            return False
        return True


class ValidatedSpinbox(ctk.CTkFrame):
    """
    A fully native CTk spinbox with +/- buttons and validation.

    Replaces the original ttk.Spinbox wrapper. Based on the CTkFloatSpinbox
    pattern, extended with:
      * from_ / to range clamping
      * per-keystroke validation on the inner CTkEntry
      * focus-out validation with error reporting
      * min_var / max_var dynamic range traces
      * focus_update_var support
      * textvariable binding

    Parameters
    ----------
    number_type : "float" | "integer"
        Controls accepted keystrokes, step display, and how the value is
        coerced on focus-out.

        "float"   -- decimal point allowed; variable stored as float;
                     default increment 0.1
        "integer" -- decimal point blocked; variable stored as int;
                     default increment 1
    """

    def __init__(
        self,
        *args,
        width: int = 120,
        height: int = 32,
        from_: Any = "-Infinity",
        to: Any = "Infinity",
        increment: Any = None,  # None -> use number_type default
        number_type: str = "float",  # "float" | "integer"
        min_var=None,
        max_var=None,
        focus_update_var=None,
        textvariable=None,
        error_var=None,
        **kwargs,
    ) -> None:
        super().__init__(*args, width=width, height=height, **kwargs)

        if number_type not in ("float", "integer"):
            raise ValueError(
                f"number_type must be 'float' or 'integer', got {number_type!r}"
            )
        self.number_type = number_type

        # Default increments per type
        if increment is None:
            increment = "0.1" if number_type == "float" else "1"

        self._inc = Decimal(str(increment))
        self.precision = self._inc.normalize().as_tuple().exponent
        self._from = Decimal(str(from_))
        self._to = Decimal(str(to))
        self.error = error_var or tk.StringVar()

        # Use IntVar for integers so the variable type matches the field type
        if textvariable is not None:
            self.variable = textvariable
        elif number_type == "integer":
            self.variable = tk.IntVar()
        else:
            self.variable = tk.DoubleVar()

        self.configure(fg_color=("gray78", "gray28"))
        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_columnconfigure(1, weight=1)

        btn_size = height - 6
        self._sub_btn = ctk.CTkButton(
            self,
            text="-",
            width=btn_size,
            height=btn_size,
            command=self._subtract,
        )
        self._sub_btn.grid(row=0, column=0, padx=(3, 0), pady=3)

        self.entry = ctk.CTkEntry(
            self,
            width=width - (2 * height),
            height=btn_size,
            border_width=0,
        )
        self.entry.grid(row=0, column=1, padx=3, pady=3, sticky="ew")

        self._add_btn = ctk.CTkButton(
            self,
            text="+",
            width=btn_size,
            height=btn_size,
            command=self._add,
        )
        self._add_btn.grid(row=0, column=2, padx=(0, 3), pady=3)

        # Seed with the variable's current value (default 0)
        self.entry.insert(0, str(self.variable.get()))

        # Sync textvariable → entry
        self.variable.trace_add("write", self._var_to_entry)

        # Validate keystrokes and focus-out on the inner entry
        self.entry.bind("<Key>", self._on_key)
        self.entry.bind("<FocusOut>", self._on_focusout)

        # Dynamic range variables
        if min_var:
            self.min_var = min_var
            self.min_var.trace_add("write", self._set_minimum)
        if max_var:
            self.max_var = max_var
            self.max_var.trace_add("write", self._set_maximum)

        self.focus_update_var = focus_update_var
        if focus_update_var:
            self.entry.bind("<FocusOut>", self._set_focus_update_var, add="+")

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def _add(self) -> None:
        try:
            value = Decimal(str(self.entry.get())) + self._inc
            self._write(value)
        except InvalidOperation:
            pass

    def _subtract(self) -> None:
        try:
            value = Decimal(str(self.entry.get())) - self._inc
            self._write(value)
        except InvalidOperation:
            pass

    def _write(self, value: Decimal) -> None:
        """Clamp to [from_, to] then push to entry and variable."""
        value = max(self._from, min(self._to, value))
        display = str(int(value)) if self.number_type == "integer" else str(value)
        self.entry.delete(0, "end")
        self.entry.insert(0, display)
        try:
            if self.number_type == "integer":
                self.variable.set(int(value))
            else:
                self.variable.set(float(value))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public get / set (mirrors original API)
    # ------------------------------------------------------------------

    def get(self) -> str:
        return self.entry.get()

    def set(self, value) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, str(value))

    # ------------------------------------------------------------------
    # Variable sync
    # ------------------------------------------------------------------

    def _var_to_entry(self, *_) -> None:
        try:
            new_val = str(self.variable.get())
            if self.entry.get() != new_val:
                self.entry.delete(0, "end")
                self.entry.insert(0, new_val)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _on_key(self, event) -> None:
        current = self.entry.get()
        char = event.char
        proposed = current + char

        valid = self._key_validate(
            char=char,
            index=str(len(current)),
            current=current,
            proposed=proposed,
            action="1",
        )
        self._set_error_style(not valid)
        if not valid:
            return "break"

    def _on_focusout(self, event=None) -> None:
        self.error.set("")
        valid = self._focusout_validate()
        self._set_error_style(not valid)

    def _set_error_style(self, on: bool) -> None:
        color = _ERROR_BG if on else _NORMAL_BG
        self.entry.configure(fg_color=color)

    def _key_validate(
        self, char: str, index: str, current: str, proposed: str, action: str, **_
    ) -> bool:
        if action == "0":
            return True

        no_negative = self._from >= 0
        # For integers, always block the decimal point regardless of precision
        no_decimal = self.number_type == "integer" or self.precision >= 0

        if any(
            [
                char not in "-1234567890.",
                char == "-" and (no_negative or index != "0"),
                char == "." and (no_decimal or "." in current),
            ]
        ):
            return False

        if proposed in (".", "-", "-."):
            return True

        try:
            d = Decimal(proposed)
        except InvalidOperation:
            return False

        if d > self._to or d.as_tuple().exponent < self.precision:
            return False

        return True

    def _focusout_validate(self) -> bool:
        value = self.entry.get()
        try:
            d_value = Decimal(value)
        except InvalidOperation:
            self.error.set(f"Invalid number: {value}")
            return False

        if d_value < self._from:
            self.error.set(f"Value is too low (min {self._from})")
            return False
        if d_value > self._to:
            self.error.set(f"Value is too high (max {self._to})")
            return False

        # Coerce and sync to the variable using the correct type
        try:
            if self.number_type == "integer":
                coerced = int(d_value)
                # Normalise display (remove any accidental decimal)
                self.entry.delete(0, "end")
                self.entry.insert(0, str(coerced))
                self.variable.set(coerced)
            else:
                self.variable.set(float(d_value))
        except Exception:
            pass

        return True

    def trigger_focusout_validation(self) -> bool:
        valid = self._focusout_validate()
        self._set_error_style(not valid)
        return valid

    # ------------------------------------------------------------------
    # Dynamic range
    # ------------------------------------------------------------------

    def _set_minimum(self, *_) -> None:
        try:
            self._from = Decimal(str(self.min_var.get()))
        except (tk.TclError, ValueError, InvalidOperation):
            pass
        self.trigger_focusout_validation()

    def _set_maximum(self, *_) -> None:
        try:
            self._to = Decimal(str(self.max_var.get()))
        except (tk.TclError, ValueError, InvalidOperation):
            pass
        self.trigger_focusout_validation()

    def _set_focus_update_var(self, event=None) -> None:
        value = self.get()
        if self.focus_update_var and not self.error.get():
            self.focus_update_var.set(value)

    # ------------------------------------------------------------------
    # State (disable / enable forwarded to inner widgets)
    # ------------------------------------------------------------------

    def configure(self, **kwargs) -> None:
        state = kwargs.pop("state", None)
        super().configure(**kwargs)
        if state is not None and hasattr(self, "entry"):
            self.entry.configure(state=state)
            self._add_btn.configure(state=state)
            self._sub_btn.configure(state=state)


class ValidatedRadioGroup(ctk.CTkFrame):
    """A group of CTkRadioButtons with focus-out validation."""

    def __init__(
        self,
        *args,
        variable=None,
        error_var=None,
        values=None,
        button_args=None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.variable = variable or tk.StringVar()
        self.error = error_var or tk.StringVar()
        self.values = values or []
        button_args = button_args or {}

        for v in self.values:
            btn = ctk.CTkRadioButton(
                self,
                text=v,
                value=v,
                variable=self.variable,
                **button_args,
            )
            btn.pack(side=tk.LEFT, ipadx=10, ipady=2, expand=True, fill="x")

        self.bind("<FocusOut>", self.trigger_focusout_validation)

    def trigger_focusout_validation(self, *_) -> None:
        self.error.set("")
        if not self.variable.get():
            self.error.set("A value is required")


class BoundText(ctk.CTkTextbox):
    """CTkTextbox with a bound textvariable (mirrors the original BoundText)."""

    def __init__(self, *args, textvariable=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._variable = textvariable
        if self._variable:
            self.insert("1.0", self._variable.get())
            self._variable.trace_add("write", self._set_content)
            self.bind("<<Modified>>", self._set_var)

    def _set_var(self, *_) -> None:
        content = self.get("1.0", "end-1chars")
        self._variable.set(content)

    def _set_content(self, *_) -> None:
        self.delete("1.0", tk.END)
        self.insert("1.0", self._variable.get())


# ---------------------------------------------------------------------------
# Compound widget
# ---------------------------------------------------------------------------


class LabelInput(ctk.CTkFrame):
    """A CTkFrame containing a label, an input widget, and an error label."""

    field_types = {
        FT.string: RequiredEntry,
        FT.string_list: ValidatedCombobox,
        FT.short_string_list: ValidatedRadioGroup,
        FT.iso_date_string: DateEntry,
        FT.long_string: BoundText,
        FT.decimal: ValidatedSpinbox,
        FT.integer: ValidatedSpinbox,
        FT.boolean: ctk.CTkCheckBox,
    }

    def __init__(
        self,
        parent,
        label_text: str,
        var,
        input_class=None,
        input_args=None,
        label_args=None,
        field_spec=None,
        disable_var=None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        input_args = input_args or {}
        label_args = label_args or {}

        self.variable = var
        self.variable.label_widget = self  # type: ignore

        # Resolve input_class and extra args from field_spec
        if field_spec:
            field_type = field_spec.get("type", FT.string)
            input_class = input_class or self.field_types.get(field_type)
            for spec_key, arg_key in [
                ("min", "from_"),
                ("max", "to"),
                ("inc", "increment"),
            ]:
                if spec_key in field_spec and arg_key not in input_args:
                    input_args[arg_key] = field_spec[spec_key]
            if "values" in field_spec and "values" not in input_args:
                input_args["values"] = field_spec["values"]
            # Automatically set number_type for spinbox fields
            if input_class is ValidatedSpinbox and "number_type" not in input_args:
                input_args["number_type"] = (
                    "integer" if field_type == FT.integer else "float"
                )

        # Label (buttons carry their own text)
        if input_class in (ctk.CTkCheckBox, ctk.CTkButton):
            input_args["text"] = label_text
        else:
            self.label = ctk.CTkLabel(self, text=label_text, anchor="w", **label_args)
            self.label.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))

        # Variable binding
        if input_class in (
            ctk.CTkCheckBox,
            ctk.CTkButton,
            ctk.CTkRadioButton,
            ValidatedRadioGroup,
        ):
            input_args["variable"] = self.variable
        else:
            input_args["textvariable"] = self.variable

        # Build the input widget
        if input_class == ctk.CTkRadioButton:
            self.input = ctk.CTkFrame(self)
            btn = None
            for v in input_args.pop("values", []):
                btn = input_class(self.input, value=v, text=v, **input_args)
                btn.pack(side=tk.LEFT, ipadx=10, ipady=2, expand=True, fill="x")
            self.input.error = getattr(btn, "error", tk.StringVar())
            self.input.trigger_focusout_validation = getattr(
                btn, "_focusout_validate", lambda: True
            )
        else:
            self.input = input_class(self, **input_args)

        self.input.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.columnconfigure(0, weight=1)

        # Error label
        self.error = getattr(self.input, "error", tk.StringVar())
        self._error_label = ctk.CTkLabel(
            self,
            textvariable=self.error,
            text_color=_ERROR_LABEL,
            anchor="w",
        )
        self._error_label.grid(row=2, column=0, sticky="ew", padx=2)

        # Disable variable wiring
        if disable_var:
            self.disable_var = disable_var
            self.disable_var.trace_add("write", self._check_disable)

    def _check_disable(self, *_) -> None:
        if not hasattr(self, "disable_var"):
            return
        if self.disable_var.get():
            self.input.configure(state=tk.DISABLED)
            self.variable.set("")
            self.error.set("")
        else:
            self.input.configure(state=tk.NORMAL)

    def grid(self, sticky="ew", **kwargs) -> None:
        super().grid(sticky=sticky, **kwargs)
