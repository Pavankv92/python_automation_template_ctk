"""
views/dialogs.py

Reusable CTk dialog classes — drop-in replacements for tkinter.messagebox.

All dialogs are modal CTkToplevel windows that centre themselves over their
parent.  No external packages required.
"""

from __future__ import annotations
import customtkinter as ctk


class _BaseDialog(ctk.CTkToplevel):
    """Internal base — handles grab, resize lock, and centring."""

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkToplevel,
        title: str,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.grab_set()
        self.resizable(False, False)
        self._parent = parent

    def _centre(self) -> None:
        self.update_idletasks()
        px, py = self._parent.winfo_rootx(), self._parent.winfo_rooty()
        pw, ph = self._parent.winfo_width(),  self._parent.winfo_height()
        dw, dh = self.winfo_width(),           self.winfo_height()
        self.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    def _add_ok_button(self) -> None:
        ctk.CTkButton(self, text="OK", width=80, command=self.destroy).pack(
            pady=(0, 16)
        )


class ErrorDialog(_BaseDialog):
    """
    Modal error dialog.

    Usage
    -----
        ErrorDialog(parent, title="Connection Error", message="...")
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkToplevel,
        title: str,
        message: str,
    ) -> None:
        super().__init__(parent, title)
        ctk.CTkLabel(
            self, text=message, wraplength=340, justify="left"
        ).pack(padx=20, pady=(20, 10))
        self._add_ok_button()
        self._centre()


class ConfirmDialog(_BaseDialog):
    """
    Modal yes/no confirmation dialog.

    The result is available via the `.confirmed` attribute after the
    dialog closes (True = confirmed, False = cancelled).

    Usage
    -----
        dlg = ConfirmDialog(parent, title="Disconnect?", message="...")
        parent.wait_window(dlg)
        if dlg.confirmed:
            ...
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkToplevel,
        title: str,
        message: str,
    ) -> None:
        super().__init__(parent, title)
        self.confirmed: bool = False

        ctk.CTkLabel(
            self, text=message, wraplength=340, justify="left"
        ).pack(padx=20, pady=(20, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        ctk.CTkButton(
            btn_frame, text="Yes", width=80, command=self._confirm
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_frame, text="No", width=80, command=self.destroy
        ).pack(side="left")

        self._centre()

    def _confirm(self) -> None:
        self.confirmed = True
        self.destroy()
