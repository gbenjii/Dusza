"""Csak olvasható szöveges kódnézet sorszámokkal, szintaxisszínezéssel, töréspontokkal
és sorkiemeléssel.

A színezés a tokenizáló tokenfajtáit használja (kulcsszó, szám, logikai, operátor).
A sorszámra kattintva töréspont kapcsolható; a sor többi részére kattintva a hozzá
tartozó blokk kijelölődik a blokkszerkesztőben.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from gui import stilus
from gui.tooltip import Tooltip
from nyelv.tokenizalo import TokenFajta, tokenizal_sor

SZIN_AKTUALIS = "#fef3c7"
SZIN_HIBAS = "#fecaca"
SZIN_KIJELOLT = "#dbeafe"
SZIN_TORESPONT = "#dc2626"
SZIN_KOVETKEZO = "#2563eb"
TOKEN_SZINEK = {
    TokenFajta.KULCSSZO: "#7c3aed",
    TokenFajta.SZAM: "#b45309",
    TokenFajta.LOGIKAI: "#0f766e",
    TokenFajta.OPERATOR: "#be123c",
    TokenFajta.AZONOSITO: "#1e3a8a",
}
JEL_TORESPONT = "●"
JEL_KOVETKEZO = "▶"
SORSZAM_OSZLOPOK = 5
"""A sor elején ennyi karakter a „margó” (jel + sorszám); ide kattintva töréspont kapcsol."""


class Kodnezet(ctk.CTkFrame):
    """A program szöveges alakja, a blokkokkal mindig szinkronban."""

    def __init__(self, master, sorra_kattintas: Callable[[int], None],
                 torespont_valt: Callable[[int], None]) -> None:
        super().__init__(master, fg_color=stilus.PANEL, corner_radius=10,
                         border_width=1, border_color=stilus.SZEGELY)
        self._sorra_kattintas = sorra_kattintas
        self._torespont_valt = torespont_valt
        self._sorok: list[str] = []
        self._torespontok: set[int] = set()
        self._kovetkezo: int | None = None
        self._fejlec()
        self.doboz = ctk.CTkTextbox(self, font=stilus.mono(13), wrap="none", fg_color="#fbfcfe",
                                    border_width=1, border_color=stilus.SZEGELY, text_color=stilus.SZOVEG)
        self.doboz.pack(fill="both", expand=True, padx=8, pady=8)
        szoveg = self.doboz._textbox
        szoveg.configure(cursor="arrow", spacing1=2, spacing3=2)
        szoveg.tag_configure("sorszam", foreground="#94a3b8")
        szoveg.tag_configure("torespont", foreground=SZIN_TORESPONT)
        szoveg.tag_configure("kovetkezo", foreground=SZIN_KOVETKEZO)
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

    def _fejlec(self) -> None:
        sor = ctk.CTkFrame(self, fg_color="transparent")
        sor.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(sor, text="Szöveges nézet", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(side="left")
        masol = ctk.CTkButton(sor, text="Másolás", width=10, height=24, font=stilus.betu(10),
                              fg_color="transparent", border_width=1, border_color=stilus.SZEGELY,
                              text_color=stilus.SZOVEG, hover_color="#e2e8f0", command=self._masolas)
        masol.pack(side="right")
        Tooltip(masol, "A teljes forráskód vágólapra másolása.")
        alcim = ctk.CTkLabel(self, text="csak olvasható – a blokkokkal együtt változik.  Sorszámra "
                                        "kattintás: töréspont (●), a futás ott megáll.", font=stilus.betu(10),
                             text_color=stilus.HALVANY, justify="left", wraplength=330)
        alcim.pack(anchor="w", padx=12)
        stilus.tordel(alcim, self)

    # ---------- Megjelenítés ----------

    def megjelenit(self, sorok: list[str], torespontok: set[int] | None = None) -> None:
        """Újraírja a teljes szöveget (tokenenként színezve)."""
        self._sorok = list(sorok)
        if torespontok is not None:
            self._torespontok = set(torespontok)
        szoveg = self._szoveg
        self.doboz.configure(state="normal")
        szoveg.delete("1.0", "end")
        if not sorok:
            szoveg.insert("end", "  (üres program)", "sorszam")
        for index, sor in enumerate(sorok, start=1):
            jel, cimke = self._jel(index)
            szoveg.insert("end", jel, cimke)
            szoveg.insert("end", f"{index:>3}  ", "sorszam")
            token_sor = tokenizal_sor(sor, index)
            szoveg.insert("end", " " * token_sor.behuzas)
            for darab, token in enumerate(token_sor.tokenek_):
                if darab:
                    szoveg.insert("end", " ")
                szoveg.insert("end", token.szoveg, token.fajta.name)
            szoveg.insert("end", "\n")
        self.doboz.configure(state="disabled")

    def _jel(self, sorszam: int) -> tuple[str, str]:
        if sorszam == self._kovetkezo:
            return JEL_KOVETKEZO, "kovetkezo"
        if sorszam in self._torespontok:
            return JEL_TORESPONT, "torespont"
        return " ", "sorszam"

    def _jel_frissit(self, sorszam: int | None) -> None:
        if sorszam is None or not 1 <= sorszam <= len(self._sorok):
            return
        jel, cimke = self._jel(sorszam)
        self.doboz.configure(state="normal")
        self._szoveg.delete(f"{sorszam}.0", f"{sorszam}.1")
        self._szoveg.insert(f"{sorszam}.0", jel, cimke)
        self.doboz.configure(state="disabled")

    def torespontok_beallit(self, torespontok: set[int]) -> None:
        regi = self._torespontok
        self._torespontok = set(torespontok)
        for sorszam in regi ^ self._torespontok:
            self._jel_frissit(sorszam)

    def kovetkezo_jelol(self, sorszam: int | None) -> None:
        """A következőként végrehajtandó sor jelölése (▶) nyomkövetés közben."""
        regi, self._kovetkezo = self._kovetkezo, sorszam
        self._jel_frissit(regi)
        self._jel_frissit(sorszam)
        if sorszam is not None:
            self._szoveg.see(f"{sorszam}.0")

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

    # ---------- Események ----------

    def _kattintas(self, esemeny) -> str:
        index = self._szoveg.index(f"@{esemeny.x},{esemeny.y}")
        sor, oszlop = (int(resz) for resz in index.split("."))
        if not 1 <= sor <= len(self._sorok):
            return "break"
        if oszlop < SORSZAM_OSZLOPOK:
            self._torespont_valt(sor)
        else:
            self._sorra_kattintas(sor)
        return "break"

    def _masolas(self) -> None:
        self.clipboard_clear()
        self.clipboard_append("\n".join(self._sorok) + ("\n" if self._sorok else ""))
