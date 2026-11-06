"""Egyszerű buborék-súgó (tooltip) tkinter / customtkinter vezérlőkhöz."""

from __future__ import annotations

import tkinter as tk

from gui import stilus

KESLELTETES_MS = 500
TOOLTIP_HATTER = "#1f2937"
SORTORES_PX = 320


class Tooltip:
    """Ha az egér a vezérlő fölött áll, rövid magyarázó szöveget mutat."""

    def __init__(self, vezerlo, szoveg: str) -> None:
        self.vezerlo = vezerlo
        self.szoveg = szoveg
        self._ablak: tk.Toplevel | None = None
        self._idozito: str | None = None
        vezerlo.bind("<Enter>", self._belep, add="+")
        vezerlo.bind("<Leave>", self._elrejt, add="+")
        vezerlo.bind("<ButtonPress>", self._elrejt, add="+")

    def _belep(self, _esemeny) -> None:
        self._elrejt()
        self._idozito = self.vezerlo.after(KESLELTETES_MS, self._mutat)

    def _mutat(self) -> None:
        self._idozito = None
        x = self.vezerlo.winfo_rootx() + 12
        y = self.vezerlo.winfo_rooty() + self.vezerlo.winfo_height() + 4
        self._ablak = tk.Toplevel(self.vezerlo)
        self._ablak.wm_overrideredirect(True)
        self._ablak.wm_geometry(f"+{x}+{y}")
        tk.Label(self._ablak, text=self.szoveg, background=TOOLTIP_HATTER, foreground="#f9fafb",
                 font=stilus.tk_betu(10), wraplength=SORTORES_PX, justify="left",
                 padx=8, pady=5).pack()

    def _elrejt(self, _esemeny=None) -> None:
        if self._idozito is not None:
            self.vezerlo.after_cancel(self._idozito)
            self._idozito = None
        if self._ablak is not None:
            self._ablak.destroy()
            self._ablak = None
