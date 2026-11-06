"""Csak olvasható szöveges kódnézet sorszámokkal és sorkiemeléssel.

Egy sorra kattintva a hozzá tartozó blokk kijelölődik a blokkszerkesztőben.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

KOD_BETU = ("Consolas", 11)
SZIN_AKTUALIS = "#fff176"
SZIN_HIBAS = "#ef9a9a"
SZIN_KIJELOLT = "#d6e9ff"
SZIN_SORSZAM = "#9e9e9e"


class Kodnezet(ttk.LabelFrame):
    """A program szöveges alakja, a blokkokkal mindig szinkronban."""

    def __init__(self, master: tk.Misc, sorra_kattintas: Callable[[int], None]) -> None:
        super().__init__(master, text="Szöveges nézet (csak olvasható)")
        self._sorra_kattintas = sorra_kattintas
        self.szoveg = tk.Text(self, width=38, font=KOD_BETU, wrap="none",
                              state="disabled", cursor="arrow", background="#fafafa")
        gorgeto = ttk.Scrollbar(self, orient="vertical", command=self.szoveg.yview)
        self.szoveg.configure(yscrollcommand=gorgeto.set)
        self.szoveg.pack(side="left", fill="both", expand=True)
        gorgeto.pack(side="right", fill="y")
        self.szoveg.tag_configure("sorszam", foreground=SZIN_SORSZAM)
        self.szoveg.tag_configure("kijelolt", background=SZIN_KIJELOLT)
        self.szoveg.tag_configure("aktualis", background=SZIN_AKTUALIS)
        self.szoveg.tag_configure("hibas", background=SZIN_HIBAS)
        self.szoveg.tag_raise("aktualis")
        self.szoveg.tag_raise("hibas")
        self.szoveg.bind("<Button-1>", self._kattintas)

    def megjelenit(self, sorok: list[str]) -> None:
        """Újraírja a teljes szöveget."""
        self.szoveg.configure(state="normal")
        self.szoveg.delete("1.0", "end")
        if not sorok:
            self.szoveg.insert("end", "(üres program – szúrj be blokkot a bal oldalon)", "sorszam")
        for index, sor in enumerate(sorok, start=1):
            self.szoveg.insert("end", f"{index:>3} ", "sorszam")
            self.szoveg.insert("end", sor + "\n")
        self.szoveg.configure(state="disabled")

    def kiemel(self, sorszam: int | None, hibas: bool = False) -> None:
        """A végrehajtott sor kiemelése (hibánál piros)."""
        self.szoveg.tag_remove("aktualis", "1.0", "end")
        self.szoveg.tag_remove("hibas", "1.0", "end")
        if sorszam is None:
            return
        cimke = "hibas" if hibas else "aktualis"
        self.szoveg.tag_add(cimke, f"{sorszam}.0", f"{sorszam}.end+1c")
        self.szoveg.see(f"{sorszam}.0")

    def kijelol(self, sorszamok: list[int]) -> None:
        """A blokkszerkesztőben kijelölt blokk sorainak halvány kiemelése."""
        self.szoveg.tag_remove("kijelolt", "1.0", "end")
        for sorszam in sorszamok:
            self.szoveg.tag_add("kijelolt", f"{sorszam}.0", f"{sorszam}.end+1c")
        if sorszamok:
            self.szoveg.see(f"{sorszamok[0]}.0")

    def _kattintas(self, esemeny: tk.Event) -> str:
        index = self.szoveg.index(f"@{esemeny.x},{esemeny.y}")
        self._sorra_kattintas(int(index.split(".")[0]))
        return "break"
