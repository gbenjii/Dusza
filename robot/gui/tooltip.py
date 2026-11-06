"""Egyszerű buborék-súgó (tooltip) tkinter vezérlőkhöz."""

from __future__ import annotations

import tkinter as tk

KESLELTETES_MS = 500
TOOLTIP_HATTER = "#ffffe0"
SORTORES_PX = 320


class Tooltip:
    """Ha az egér a vezérlő fölött áll, rövid magyarázó szöveget mutat."""

    def __init__(self, vezerlo: tk.Widget, szoveg: str) -> None:
        self.vezerlo = vezerlo
        self.szoveg = szoveg
        self._ablak: tk.Toplevel | None = None
        self._idozito: str | None = None
        vezerlo.bind("<Enter>", self._belep, add="+")
        vezerlo.bind("<Leave>", self._elrejt, add="+")
        vezerlo.bind("<ButtonPress>", self._elrejt, add="+")

    def _belep(self, _esemeny: tk.Event) -> None:
        self._idozito = self.vezerlo.after(KESLELTETES_MS, self._mutat)

    def _mutat(self) -> None:
        x = self.vezerlo.winfo_rootx() + 12
        y = self.vezerlo.winfo_rooty() + self.vezerlo.winfo_height() + 4
        self._ablak = tk.Toplevel(self.vezerlo)
        self._ablak.wm_overrideredirect(True)
        self._ablak.wm_geometry(f"+{x}+{y}")
        tk.Label(self._ablak, text=self.szoveg, background=TOOLTIP_HATTER, relief="solid",
                 borderwidth=1, wraplength=SORTORES_PX, justify="left",
                 padx=6, pady=3).pack()

    def _elrejt(self, _esemeny: tk.Event | None = None) -> None:
        if self._idozito is not None:
            self.vezerlo.after_cancel(self._idozito)
            self._idozito = None
        if self._ablak is not None:
            self._ablak.destroy()
            self._ablak = None
