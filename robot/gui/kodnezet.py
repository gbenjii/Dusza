"""Csak olvasható szöveges kódnézet sorszámokkal, szintaxisszínezéssel és sorkiemeléssel.

A színezés a tokenizáló tokenfajtáit használja (kulcsszó, szám, logikai, operátor).
Egy sorra kattintva a hozzá tartozó blokk kijelölődik a blokkszerkesztőben.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from gui import stilus
from nyelv.tokenizalo import TokenFajta, tokenizal_sor

SZIN_AKTUALIS = "#fef3c7"
SZIN_HIBAS = "#fecaca"
SZIN_KIJELOLT = "#dbeafe"
TOKEN_SZINEK = {
    TokenFajta.KULCSSZO: "#7c3aed",
    TokenFajta.SZAM: "#b45309",
    TokenFajta.LOGIKAI: "#0f766e",
    TokenFajta.OPERATOR: "#be123c",
    TokenFajta.AZONOSITO: "#1e3a8a",
}


class Kodnezet(ctk.CTkFrame):
    """A program szöveges alakja, a blokkokkal mindig szinkronban."""

    def __init__(self, master, sorra_kattintas: Callable[[int], None]) -> None:
        super().__init__(master, fg_color=stilus.PANEL, corner_radius=10,
                         border_width=1, border_color=stilus.SZEGELY)
        self._sorra_kattintas = sorra_kattintas
        ctk.CTkLabel(self, text="Szöveges nézet", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkLabel(self, text="csak olvasható – a blokkokkal együtt változik; kattints egy sorra",
                     font=stilus.betu(10), text_color=stilus.HALVANY).pack(anchor="w", padx=12)
        self.doboz = ctk.CTkTextbox(self, font=stilus.mono(13), wrap="none", fg_color="#fbfcfe",
                                    border_width=1, border_color=stilus.SZEGELY, text_color=stilus.SZOVEG)
        self.doboz.pack(fill="both", expand=True, padx=8, pady=8)
        szoveg = self.doboz._textbox
        szoveg.configure(cursor="arrow", spacing1=2, spacing3=2)
        szoveg.tag_configure("sorszam", foreground="#94a3b8")
        szoveg.tag_configure("kijelolt", background=SZIN_KIJELOLT)
        szoveg.tag_configure("aktualis", background=SZIN_AKTUALIS)
        szoveg.tag_configure("hibas", background=SZIN_HIBAS)
        for fajta, szin in TOKEN_SZINEK.items():
            szoveg.tag_configure(fajta.name, foreground=szin)
        szoveg.tag_raise("aktualis")
        szoveg.tag_raise("hibas")
        szoveg.bind("<Button-1>", self._kattintas)
        self._szoveg = szoveg
        self.doboz.configure(state="disabled")

    def megjelenit(self, sorok: list[str]) -> None:
        """Újraírja a teljes szöveget (tokenenként színezve)."""
        szoveg = self._szoveg
        self.doboz.configure(state="normal")
        szoveg.delete("1.0", "end")
        if not sorok:
            szoveg.insert("end", "  (üres program)", "sorszam")
        for index, sor in enumerate(sorok, start=1):
            szoveg.insert("end", f"{index:>3}  ", "sorszam")
            token_sor = tokenizal_sor(sor, index)
            szoveg.insert("end", " " * token_sor.behuzas)
            for darab, token in enumerate(token_sor.tokenek_):
                if darab:
                    szoveg.insert("end", " ")
                szoveg.insert("end", token.szoveg, token.fajta.name)
            szoveg.insert("end", "\n")
        self.doboz.configure(state="disabled")

    def kiemel(self, sorszam: int | None, hibas: bool = False) -> None:
        """A végrehajtott sor kiemelése (hibánál piros)."""
        self._szoveg.tag_remove("aktualis", "1.0", "end")
        self._szoveg.tag_remove("hibas", "1.0", "end")
        if sorszam is None:
            return
        cimke = "hibas" if hibas else "aktualis"
        self._szoveg.tag_add(cimke, f"{sorszam}.0", f"{sorszam}.end+1c")
        self._szoveg.see(f"{sorszam}.0")

    def kijelol(self, sorszamok: list[int]) -> None:
        """A blokkszerkesztőben kijelölt blokk sorainak halvány kiemelése."""
        self._szoveg.tag_remove("kijelolt", "1.0", "end")
        for sorszam in sorszamok:
            self._szoveg.tag_add("kijelolt", f"{sorszam}.0", f"{sorszam}.end+1c")
        if sorszamok:
            self._szoveg.see(f"{sorszamok[0]}.0")

    def _kattintas(self, esemeny) -> str:
        index = self._szoveg.index(f"@{esemeny.x},{esemeny.y}")
        self._sorra_kattintas(int(index.split(".")[0]))
        return "break"
