"""A kijelölt blokk mezőinek szerkesztése gépeléssel (érték, változónév, kifejezés).

Hibás azonosítót vagy értéket (pl. `while`, `9lives`, `101`) magyar
üzenettel elutasít; csak érvényes adat kerül a modellbe.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from nyelv.ellenorzo import azonosito_hiba, ertek_hiba
from nyelv.kiiro import fej_szoveg
from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertek, Ertekadas, ErtekKif, Fordulas, IsThereKif,
    Kifejezes, Kiiras, Lepes, Muvelet, MuveletKif, NotKif, Utasitas,
)

KIF_ERTEK = "V  (egyszerű érték)"
KIF_ISTHERE = "isThere V  (szenzor)"
KIF_MUVELET = "V művelet V"
KIF_NOT = "not V"
KIF_FAJTAK = (KIF_ERTEK, KIF_ISTHERE, KIF_MUVELET, KIF_NOT)
MUVELETEK = tuple(muvelet.value for muvelet in Muvelet)

ERTEK_SUGO = "V lehet: változónév, 0–100 közötti egész szám, true vagy false."

ERTEK_FELIRATOK: dict[type, str] = {
    Lepes: "Lépések száma (V):",
    Fordulas: "Negyedfordulatok balra (V):",
    Kiiras: "Kiírandó érték (V):",
    Elagazas: "Feltétel (logikai V):",
    Ciklus: "Feltétel (logikai V):",
}


def _kif_fajta(kif: Kifejezes) -> str:
    if isinstance(kif, IsThereKif):
        return KIF_ISTHERE
    if isinstance(kif, MuveletKif):
        return KIF_MUVELET
    if isinstance(kif, NotKif):
        return KIF_NOT
    return KIF_ERTEK


def _elso_operandus(kif: Kifejezes) -> str:
    return kif.bal.szoveg if isinstance(kif, MuveletKif) else kif.ertek.szoveg


class TulajdonsagPanel(ttk.LabelFrame):
    """Űrlap a kijelölt blokk mezőihez; `alkalmazva` hívódik sikeres módosítás után."""

    def __init__(self, master: tk.Misc, alkalmazva: Callable[[], None]) -> None:
        super().__init__(master, text="Kijelölt blokk mezői")
        self._alkalmazva = alkalmazva
        self._utasitas: Utasitas | None = None
        self._mezok: dict[str, tk.StringVar] = {}
        self._tartalom = ttk.Frame(self)
        self._tartalom.pack(fill="x", padx=6, pady=4)
        self.megjelenit(None)

    # ---------- Felépítés ----------

    def megjelenit(self, utasitas: Utasitas | None) -> None:
        """Az űrlap újraépítése a kijelölt blokkhoz."""
        self._utasitas = utasitas
        self._torol()
        if utasitas is None:
            self._felirat("Kattints egy blokkra a szerkesztéséhez.")
            return
        self._felirat(f"Blokk: {fej_szoveg(utasitas)}", vastag=True)
        if isinstance(utasitas, Banyaszas):
            self._felirat("A „mine here” blokknak nincs beállítható mezője.")
            return
        if isinstance(utasitas, Ertekadas):
            self._ertekadas_mezoi(utasitas)
        else:
            ertek = utasitas.feltetel if isinstance(utasitas, (Elagazas, Ciklus)) else utasitas.ertek
            self._beviteli_mezo("ertek", ERTEK_FELIRATOK[type(utasitas)], ertek.szoveg)
        self._felirat(ERTEK_SUGO, szurke=True)
        ttk.Button(self._tartalom, text="✔ Alkalmaz (Enter)", command=self._alkalmaz).pack(
            anchor="e", pady=(4, 0))

    def _torol(self) -> None:
        for gyerek in self._tartalom.winfo_children():
            gyerek.destroy()
        self._mezok = {}

    def _felirat(self, szoveg: str, vastag: bool = False, szurke: bool = False) -> None:
        betu = ("Segoe UI", 9, "bold") if vastag else ("Segoe UI", 9)
        szin = "#757575" if szurke else "#000000"
        ttk.Label(self._tartalom, text=szoveg, font=betu, foreground=szin,
                  wraplength=330).pack(anchor="w")

    def _beviteli_mezo(self, kulcs: str, felirat: str, kezdo: str, szulo: tk.Misc | None = None) -> None:
        sor = ttk.Frame(szulo or self._tartalom)
        sor.pack(fill="x", pady=1)
        ttk.Label(sor, text=felirat, width=26).pack(side="left")
        valtozo = tk.StringVar(value=kezdo)
        mezo = ttk.Entry(sor, textvariable=valtozo, width=14)
        mezo.pack(side="left", fill="x", expand=True)
        mezo.bind("<Return>", lambda _e: self._alkalmaz())
        self._mezok[kulcs] = valtozo

    def _ertekadas_mezoi(self, utasitas: Ertekadas) -> None:
        self._beviteli_mezo("nev", "Változó neve:", utasitas.nev)
        sor = ttk.Frame(self._tartalom)
        sor.pack(fill="x", pady=1)
        ttk.Label(sor, text="Jobb oldal (érték-blokk):", width=26).pack(side="left")
        fajta = tk.StringVar(value=_kif_fajta(utasitas.kif))
        valaszto = ttk.Combobox(sor, textvariable=fajta, values=KIF_FAJTAK, state="readonly", width=20)
        valaszto.pack(side="left")
        self._mezok["kif_fajta"] = fajta
        self._kif_keret = ttk.Frame(self._tartalom)
        self._kif_keret.pack(fill="x")
        self._kif_mezoi(utasitas.kif)
        valaszto.bind("<<ComboboxSelected>>", lambda _e: self._kif_fajta_valtozott())

    def _kif_mezoi(self, kif: Kifejezes) -> None:
        for gyerek in self._kif_keret.winfo_children():
            gyerek.destroy()
        fajta = self._mezok["kif_fajta"].get()
        elso = _elso_operandus(kif)
        if fajta != KIF_MUVELET:
            self._beviteli_mezo("elso", "Operandus (V):", elso, self._kif_keret)
            return
        jobb = kif.jobb.szoveg if isinstance(kif, MuveletKif) else "0"
        muvelet = kif.muvelet.value if isinstance(kif, MuveletKif) else "+"
        self._beviteli_mezo("elso", "Bal operandus (V):", elso, self._kif_keret)
        sor = ttk.Frame(self._kif_keret)
        sor.pack(fill="x", pady=1)
        ttk.Label(sor, text="Művelet:", width=26).pack(side="left")
        self._mezok["muvelet"] = tk.StringVar(value=muvelet)
        ttk.Combobox(sor, textvariable=self._mezok["muvelet"], values=MUVELETEK,
                     state="readonly", width=6).pack(side="left")
        self._beviteli_mezo("jobb", "Jobb operandus (V):", jobb, self._kif_keret)

    def _kif_fajta_valtozott(self) -> None:
        elso = self._mezok["elso"].get().strip()
        self._kif_mezoi(ErtekKif(Ertek(elso)))

    # ---------- Alkalmazás ----------

    def _alkalmaz(self) -> None:
        utasitas = self._utasitas
        if utasitas is None:
            return
        try:
            self._beir(utasitas)
        except ValueError as hiba:
            messagebox.showerror("Érvénytelen bevitel", str(hiba), parent=self)
            return
        self._alkalmazva()

    def _ertek(self, kulcs: str) -> Ertek:
        szoveg = self._mezok[kulcs].get().strip()
        hiba = ertek_hiba(szoveg)
        if hiba is not None:
            raise ValueError(hiba)
        return Ertek(szoveg)

    def _beir(self, utasitas: Utasitas) -> None:
        """Ellenőrzi és beírja a mezők tartalmát; hibánál ValueError."""
        if isinstance(utasitas, Ertekadas):
            nev = self._mezok["nev"].get().strip()
            hiba = azonosito_hiba(nev)
            if hiba is not None:
                raise ValueError(hiba)
            kif = self._kifejezes()
            utasitas.nev = nev
            utasitas.kif = kif
        elif isinstance(utasitas, (Elagazas, Ciklus)):
            utasitas.feltetel = self._ertek("ertek")
        elif not isinstance(utasitas, Banyaszas):
            utasitas.ertek = self._ertek("ertek")

    def _kifejezes(self) -> Kifejezes:
        fajta = self._mezok["kif_fajta"].get()
        elso = self._ertek("elso")
        if fajta == KIF_ISTHERE:
            return IsThereKif(elso)
        if fajta == KIF_NOT:
            return NotKif(elso)
        if fajta == KIF_MUVELET:
            return MuveletKif(elso, Muvelet(self._mezok["muvelet"].get()), self._ertek("jobb"))
        return ErtekKif(elso)
