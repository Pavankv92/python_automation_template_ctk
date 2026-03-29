"""
application.py

Application — the root CTk window.

Adding a new page
-----------------
1. Import your page class
2. Add one entry to the PAGES list: ("Tab Label", PageClass)

That is all.  Application never imports page internals or field definitions.
"""

from __future__ import annotations

from typing import ClassVar
import customtkinter as ctk

from .pages.instrument_page import InstrumentMainPage

# from .pages.calibration_page import CalibrationPage  ← add future pages here


class Application(ctk.CTk):
    """
    Root application window.

    PAGES is the single place that registers tab label → page class.
    The constructor iterates it and wires everything up automatically.
    """

    PAGES: ClassVar[list[tuple[str, type]]] = [
        ("Robot", InstrumentMainPage),
        # ("Calibration", CalibrationPage),   ← uncomment to add a tab
    ]

    TITLE: ClassVar[str] = "Application"
    WIDTH: ClassVar[int] = 900
    HEIGHT: ClassVar[int] = 600

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.title(self.TITLE)
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._notebook = ctk.CTkTabview(self)
        self._notebook.grid(row=0, column=0, sticky="nsew")

        self._pages: dict[str, ctk.CTkFrame] = {}
        for label, page_cls in self.PAGES:
            tab_frame = self._notebook.add(label)
            tab_frame.columnconfigure(0, weight=1)
            tab_frame.rowconfigure(0, weight=1)
            page = page_cls(tab_frame)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[label] = page

    def get_page(self, label: str) -> ctk.CTkFrame:
        """Return a registered page by its tab label."""
        if label not in self._pages:
            raise KeyError(f"No page {label!r}. Registered: {list(self._pages)}")
        return self._pages[label]
