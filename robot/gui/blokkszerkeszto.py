"""Vizuális blokkszerkesztő: paletta, húzással mozgatható blokkok, szerkeszthető mezők.

A program szerkesztése CSAK itt lehetséges:
  • a bal oldali palettáról egy blokkot a vászonra húzva tetszőleges helyre
    (elé, mögé, if/while törzsébe, else-ágba) kerül; kattintásra a kijelölt
    blokk mögé (ha nincs kijelölés, a program végére);
  • a már meglévő blokkok a fejüknél megfogva áthúzhatók máshová
    (a vezérlőblokkok a teljes törzsükkel együtt mozognak);
  • a fehér mezőkre kattintva a tartalmuk átírható; a szám és a true/false
    mezők mellett −/+ gomb van a gyors léptetéshez;
  • a narancs érték-blokk ▾ gombjával választható a set jobb oldalának fajtája.
Minden módosítás után a `valtozott` függvény hívódik (a szöveges nézet is frissül).
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from tkinter import messagebox

import customtkinter as ctk

from gui import stilus
from gui.tooltip import Tooltip
from nyelv.ellenorzo import azonosito_hiba, ertek_hiba, ertek_leptet, leptetheto_e
from nyelv.kiiro import fej_szoveg
from nyelv.szerkesztes import (
    VEZERLO_FAJTAK, BeszurasHelye, BlokkFajta, SzerkesztesiHiba, athelyez,
    athelyezes_hiba, beszur, beszur_ide, beszuras_hiba, beszuras_ide_hiba,
    else_ag_valt, pozicio_keres, torol, torzsek,
)
from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertek, Ertekadas, ErtekKif, Fordulas, IsThereKif,
    Kiiras, Lepes, Muvelet, MuveletKif, NotKif, Utasitas, vezerlo_e,
)

# ---- Méretek (képpont) ----
FEJ_H = 34
ELSE_H = 26
LAB_H = 12
URES_H = 30
KOZ = 4
BEHUZAS = 22
BAL_MARGO = 40
FELSO_MARGO = 10
MIN_SZELESSEG = 380
MEZO_H = 22
CHIP_W = 18
HUZAS_KUSZOB = 6
JOBB_LEPCSO = 10

# ---- Színek: (kitöltés, szegély) – a feladatleírás ábráinak színvilága ----
PARANCS_SZIN = ("#dbeafe", "#93c5fd")
KIIRAS_SZIN = ("#dcfce7", "#86efac")
HA_SZIN = ("#ede9fe", "#a78bfa")
AMIG_SZIN = ("#d1fae5", "#34d399")
ERTEK_SZIN = ("#ffedd5", "#fb923c")
TORZS_HATTER = "#f8fafc"
MEZO_HATTER = "#ffffff"
MEZO_SZEGELY = "#94a3b8"
SZIN_KIJELOLT = "#1d4ed8"
SZIN_AKTUALIS = "#f59e0b"
SZIN_AKTUALIS_HATTER = "#fef3c7"
SZIN_HIBAS = "#dc2626"
SZIN_HIBAS_HATTER = "#fee2e2"
SZIN_JO_HELY = "#2563eb"
SZIN_ROSSZ_HELY = "#dc2626"

BLOKK_SZINEK: dict[type, tuple[str, str]] = {
    Lepes: PARANCS_SZIN, Fordulas: PARANCS_SZIN, Banyaszas: PARANCS_SZIN,
    Ertekadas: PARANCS_SZIN, Kiiras: KIIRAS_SZIN, Elagazas: HA_SZIN, Ciklus: AMIG_SZIN,
}

PALETTA = (
    ("Parancsblokkok", (
        (BlokkFajta.LEPES, "step forward", PARANCS_SZIN, "Lépés előre n mezőt."),
        (BlokkFajta.FORDULAS, "turn by", PARANCS_SZIN, "Fordulás balra n negyedfordulattal."),
        (BlokkFajta.BANYASZAS, "mine here", PARANCS_SZIN, "Az arany kibányászása a robot mezőjén."),
        (BlokkFajta.KIIRAS, "print", KIIRAS_SZIN, "Érték kiírása a konzolra."),
        (BlokkFajta.ERTEKADAS, "set … to …", PARANCS_SZIN, "Értékadás változónak."),
    )),
    ("Vezérlőblokkok", (
        (BlokkFajta.HA, "if", HA_SZIN, "Elágazás: a törzs csak igaz feltételnél fut."),
        (BlokkFajta.HA_KULONBEN, "if – else", HA_SZIN, "Kétirányú elágazás."),
        (BlokkFajta.AMIG, "while", AMIG_SZIN, "Ciklus: a törzs addig ismétlődik, amíg a feltétel igaz."),
    )),
)
FAJTA_NEVEK = {fajta: nev for _cim, elemek in PALETTA for fajta, nev, _sz, _s in elemek}

ERTEK_BLOKK_MENU = (
    ("érték (simpleval)", "ertek"), ("isThere …", "isThere"), ("not …", "not"),
    *((f"… {muvelet.value} …", muvelet.value) for muvelet in Muvelet),
)

SUGO = ("Húzd a blokkot a palettáról a kívánt helyre, vagy kattints rá (a kijelölt blokk "
        "mögé kerül). Blokk áthelyezése: fogd meg és húzd. Fehér mező: kattints és írd át; "
        "−/+ : érték léptetése. Jobb klikk: további műveletek.")


# ---------- Mezők elérése ----------

def _kif_operandus(kif, kulcs: str) -> Ertek:
    if isinstance(kif, MuveletKif):
        return kif.bal if kulcs == "elso" else kif.jobb
    return kif.ertek


def mezo_ertek(utasitas: Utasitas, kulcs: str) -> str:
    """Egy szerkeszthető mező szövege."""
    if kulcs == "nev":
        return utasitas.nev
    if kulcs == "feltetel":
        return utasitas.feltetel.szoveg
    if kulcs == "ertek":
        return utasitas.ertek.szoveg
    if kulcs == "muvelet":
        return utasitas.kif.muvelet.value
    return _kif_operandus(utasitas.kif, kulcs).szoveg


def mezo_beallit(utasitas: Utasitas, kulcs: str, szoveg: str) -> None:
    """Egy mező beírása (az ellenőrzés a hívó dolga)."""
    if kulcs == "nev":
        utasitas.nev = szoveg
    elif kulcs == "feltetel":
        utasitas.feltetel = Ertek(szoveg)
    elif kulcs == "ertek":
        utasitas.ertek = Ertek(szoveg)
    elif kulcs == "muvelet":
        utasitas.kif.muvelet = Muvelet(szoveg)
    elif isinstance(utasitas.kif, MuveletKif):
        if kulcs == "elso":
            utasitas.kif.bal = Ertek(szoveg)
        else:
            utasitas.kif.jobb = Ertek(szoveg)
    else:
        utasitas.kif.ertek = Ertek(szoveg)


def mezo_hiba(kulcs: str, szoveg: str) -> str | None:
    return azonosito_hiba(szoveg) if kulcs == "nev" else ertek_hiba(szoveg)


def kif_atalakit(utasitas: Ertekadas, fajta: str) -> None:
    """A set jobb oldalának (érték-blokk) cseréje; az első operandus megmarad."""
    elso = _kif_operandus(utasitas.kif, "elso")
    if fajta == "ertek":
        utasitas.kif = ErtekKif(elso)
    elif fajta == "isThere":
        utasitas.kif = IsThereKif(elso)
    elif fajta == "not":
        utasitas.kif = NotKif(elso)
    else:
        jobb = utasitas.kif.jobb if isinstance(utasitas.kif, MuveletKif) else Ertek("1")
        utasitas.kif = MuveletKif(elso, Muvelet(fajta), jobb)


def fej_elemek(utasitas: Utasitas) -> list[tuple]:
    """A blokk fejsorának elemei: ("szo", szöveg) | ("mezo", kulcs) | ("kif", [elemek])."""
    if isinstance(utasitas, Lepes):
        return [("szo", "step forward"), ("mezo", "ertek")]
    if isinstance(utasitas, Fordulas):
        return [("szo", "turn by"), ("mezo", "ertek")]
    if isinstance(utasitas, Banyaszas):
        return [("szo", "mine here")]
    if isinstance(utasitas, Kiiras):
        return [("szo", "print"), ("mezo", "ertek")]
    if isinstance(utasitas, Elagazas):
        return [("szo", "if"), ("mezo", "feltetel")]
    if isinstance(utasitas, Ciklus):
        return [("szo", "while"), ("mezo", "feltetel")]
    kif = utasitas.kif
    if isinstance(kif, IsThereKif):
        belso = [("szo", "isThere"), ("mezo", "elso")]
    elif isinstance(kif, NotKif):
        belso = [("szo", "not"), ("mezo", "elso")]
    elif isinstance(kif, MuveletKif):
        belso = [("mezo", "elso"), ("muvelet", "muvelet"), ("mezo", "jobb")]
    else:
        belso = [("mezo", "elso")]
    return [("szo", "set"), ("mezo", "nev"), ("szo", "to"), ("kif", belso)]


@dataclass
class Terulet:
    """Kattintható téglalap a vásznon."""

    x0: float
    y0: float
    x1: float
    y1: float
    tipus: str          # blokk | mezo | minusz | plusz | muvelet | kif_fajta | ures
    utasitas: Utasitas
    kulcs: str = ""

    def benne(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


@dataclass
class Hely:
    """Beszúrási / ledobási hely: melyik törzs hányadik pozíciója."""

    lista: list[Utasitas]
    index: int
    x: float
    y: float


def _kerek(vaszon: tk.Canvas, x0, y0, x1, y1, r=6, **opciok) -> int:
    """Lekerekített téglalap."""
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pontok = (x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
              x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0)
    return vaszon.create_polygon(pontok, smooth=True, **opciok)


class Blokkszerkeszto(ctk.CTkFrame):
    """Paletta + blokkvászon + eszközsor."""

    def __init__(self, master, program: list[Utasitas], valtozott: Callable[[], None],
                 kijeloles_valtozott: Callable[[Utasitas | None], None],
                 uzenet: Callable[[str, bool], None],
                 visszavon: Callable[[], None], ujra: Callable[[], None]) -> None:
        super().__init__(master, fg_color=stilus.PANEL, corner_radius=10,
                         border_width=1, border_color=stilus.SZEGELY)
        self.program = program
        self.kijelolt: Utasitas | None = None
        self.aktualis_sorszam: int | None = None
        self.aktualis_hibas = False
        self._valtozott = valtozott
        self._kijeloles_valtozott = kijeloles_valtozott
        self._uzenet = uzenet
        self._visszavon = visszavon
        self._ujra = ujra
        self._teruletek: list[Terulet] = []
        self._helyek: list[Hely] = []
        self._sor_y: dict[int, tuple[float, float]] = {}
        self._jobb_szel = MIN_SZELESSEG
        self._also_y = FELSO_MARGO
        self._betu = tkfont.Font(family=stilus.SANS, size=10)
        self._betu_vastag = tkfont.Font(family=stilus.SANS, size=10, weight="bold")
        self._mono = tkfont.Font(family=stilus.MONO, size=10)
        self._szerkeszto_mezo: tk.Entry | None = None
        self._huzas: dict | None = None
        self._jelolo: list[int] = []

        ctk.CTkLabel(self, text="Blokkszerkesztő", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(anchor="w", padx=12, pady=(8, 0))
        self._eszkozsor()
        torzs = ctk.CTkFrame(self, fg_color="transparent")
        torzs.pack(fill="both", expand=True, padx=8, pady=(4, 4))
        self._paletta(torzs)
        self._vaszon_letrehoz(torzs)
        ctk.CTkLabel(self, text=SUGO, font=stilus.betu(10), text_color=stilus.HALVANY,
                     wraplength=520, justify="left").pack(fill="x", padx=12, pady=(0, 8))

    # ---------- Nyilvános felület ----------

    def program_beallit(self, program: list[Utasitas]) -> None:
        self.program = program
        self.kijelolt = None
        self._kijeloles_valtozott(None)

    def frissit(self) -> None:
        """Újrarajzolja a blokkokat a modell alapján."""
        self._szerkesztes_vege(mentes=False)
        if self.kijelolt is not None and pozicio_keres(self.program, self.kijelolt) is None:
            self.kijelolt = None
        self._rajzol()
        self._gombok_frissit()

    def kijelol(self, utasitas: Utasitas | None) -> None:
        self.kijelolt = utasitas
        self._rajzol()
        self._gombok_frissit()
        self._kijeloles_valtozott(utasitas)

    def kijelol_sorszam(self, sorszam: int) -> None:
        utasitas = self._sorszam_utasitas(self.program, sorszam)
        if utasitas is not None:
            self.kijelol(utasitas)
            self._lathatova_tesz(sorszam)

    def kiemel_sorszam(self, sorszam: int | None, hibas: bool = False) -> None:
        """A futás közben végrehajtott sor kiemelése."""
        self.aktualis_sorszam = sorszam
        self.aktualis_hibas = hibas
        self._rajzol()
        if sorszam is not None:
            self._lathatova_tesz(sorszam)

    # ---------- Felépítés ----------

    def _eszkozsor(self) -> None:
        sav = ctk.CTkFrame(self, fg_color="transparent")
        sav.pack(fill="x", padx=10, pady=(4, 0))
        gombok = (
            ("torles", "✕ Törlés", self._torles, "A kijelölt blokk törlése a teljes tartalmával (Delete)."),
            ("fel", "▲ Feljebb", partial(self._mozgat, -1), "A kijelölt blokk egy hellyel feljebb (Alt+↑)."),
            ("le", "▼ Lejjebb", partial(self._mozgat, 1), "A kijelölt blokk egy hellyel lejjebb (Alt+↓)."),
            ("else", "if ↔ if-else", self._else_valt, "A kijelölt if blokkhoz else-ág hozzáadása / elvétele."),
        )
        self._gombok: dict[str, ctk.CTkButton] = {}
        for kulcs, felirat, parancs, sugo in gombok:
            gomb = ctk.CTkButton(sav, text=felirat, command=parancs, width=10, height=28,
                                 font=stilus.betu(11), fg_color=stilus.GOMB_SEMLEGES[0],
                                 hover_color=stilus.GOMB_SEMLEGES[1])
            gomb.pack(side="left", padx=(0, 4))
            Tooltip(gomb, sugo)
            self._gombok[kulcs] = gomb
        for felirat, parancs, sugo in (("↷ Újra", lambda: self._ujra(), "Visszavont lépés újra (Ctrl+Y)."),
                                       ("↶ Visszavonás", lambda: self._visszavon(),
                                        "Az utolsó szerkesztés visszavonása (Ctrl+Z).")):
            gomb = ctk.CTkButton(sav, text=felirat, command=parancs, width=10, height=28,
                                 font=stilus.betu(11), fg_color="transparent", border_width=1,
                                 border_color=stilus.SZEGELY, text_color=stilus.SZOVEG,
                                 hover_color="#e2e8f0")
            gomb.pack(side="right", padx=(4, 0))
            Tooltip(gomb, sugo)

    def _gombok_frissit(self) -> None:
        van = self.kijelolt is not None
        for kulcs in ("torles", "fel", "le"):
            self._gombok[kulcs].configure(state="normal" if van else "disabled")
        self._gombok["else"].configure(
            state="normal" if isinstance(self.kijelolt, Elagazas) else "disabled")

    def _paletta(self, szulo) -> None:
        keret = ctk.CTkFrame(szulo, fg_color="#f1f5f9", corner_radius=8, width=150)
        keret.pack(side="left", fill="y", padx=(0, 6))
        ctk.CTkLabel(keret, text="Új blokk", font=stilus.betu(12, True),
                     text_color=stilus.SZOVEG).pack(anchor="w", padx=8, pady=(6, 0))
        ctk.CTkLabel(keret, text="húzd a helyére\nvagy kattints", font=stilus.betu(10),
                     text_color=stilus.HALVANY, justify="left").pack(anchor="w", padx=8)
        for cim, elemek in PALETTA:
            ctk.CTkLabel(keret, text=cim, font=stilus.betu(10, True),
                         text_color=stilus.HALVANY).pack(anchor="w", padx=8, pady=(8, 2))
            for fajta, nev, (kitoltes, szegely), sugo in elemek:
                elem = ctk.CTkLabel(keret, text=nev, font=stilus.betu(11), fg_color=kitoltes,
                                    text_color=stilus.SZOVEG, corner_radius=6, height=30,
                                    anchor="w", cursor="hand2")
                elem.pack(fill="x", padx=8, pady=2)
                elem.bind("<ButtonPress-1>", partial(self._paletta_nyom, fajta))
                elem.bind("<B1-Motion>", self._paletta_huz)
                elem.bind("<ButtonRelease-1>", self._paletta_enged)
                Tooltip(elem, sugo + " Húzd a programba, vagy kattints rá.")

    def _vaszon_letrehoz(self, szulo) -> None:
        keret = ctk.CTkFrame(szulo, fg_color="transparent")
        keret.pack(side="left", fill="both", expand=True)
        self.vaszon = tk.Canvas(keret, background="#ffffff", highlightthickness=1,
                                highlightbackground=stilus.SZEGELY, highlightcolor=stilus.KIEMELO)
        gorgeto = ctk.CTkScrollbar(keret, orientation="vertical", command=self.vaszon.yview)
        vizszintes = ctk.CTkScrollbar(keret, orientation="horizontal", command=self.vaszon.xview)
        self.vaszon.configure(yscrollcommand=gorgeto.set, xscrollcommand=vizszintes.set)
        vizszintes.pack(side="bottom", fill="x")
        self.vaszon.pack(side="left", fill="both", expand=True)
        gorgeto.pack(side="right", fill="y")
        v = self.vaszon
        v.bind("<ButtonPress-1>", self._nyomas)
        v.bind("<B1-Motion>", self._huzas_mozog)
        v.bind("<ButtonRelease-1>", self._elengedes)
        v.bind("<Double-Button-1>", self._dupla_kattintas)
        v.bind("<Button-3>", self._jobb_kattintas)
        v.bind("<Motion>", self._mutato)
        v.bind("<Delete>", lambda _e: self._torles())
        v.bind("<Escape>", lambda _e: self.kijelol(None))
        v.bind("<Up>", lambda _e: self._szomszed_kijelol(-1))
        v.bind("<Down>", lambda _e: self._szomszed_kijelol(1))
        v.bind("<Alt-Up>", lambda _e: (self._mozgat(-1), "break")[1])
        v.bind("<Alt-Down>", lambda _e: (self._mozgat(1), "break")[1])
        v.bind("<MouseWheel>", lambda e: v.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units"))
        v.bind("<Button-4>", lambda _e: v.yview_scroll(-2, "units"))
        v.bind("<Button-5>", lambda _e: v.yview_scroll(2, "units"))
        v.bind("<Configure>", lambda _e: self._rajzol())

    # ---------- Elrendezés és rajzolás ----------

    def _szoveg_szel(self, szoveg: str, vastag: bool = False) -> float:
        return (self._betu_vastag if vastag else self._betu).measure(szoveg)

    def _elemek_szel(self, utasitas: Utasitas, elemek: list[tuple]) -> float:
        szel = 0.0
        for elem in elemek:
            if elem[0] == "szo":
                szel += self._szoveg_szel(elem[1], True) + 8
            elif elem[0] == "muvelet":
                szel += self._szoveg_szel(mezo_ertek(utasitas, "muvelet"), True) + 18
            elif elem[0] == "mezo":
                szoveg = mezo_ertek(utasitas, elem[1])
                szel += max(28, self._mono.measure(szoveg) + 14) + 6
                if leptetheto_e(szoveg):
                    szel += 2 * (CHIP_W + 2) + 2
            else:
                szel += self._elemek_szel(utasitas, elem[1]) + CHIP_W + 18
        return szel

    def _szukseges_szel(self, lista: list[Utasitas], melyseg: int) -> float:
        szel = 0.0
        for utasitas in lista:
            x = BAL_MARGO + melyseg * BEHUZAS + 10
            szel = max(szel, x + self._elemek_szel(utasitas, fej_elemek(utasitas)) + 12 + melyseg * JOBB_LEPCSO)
            for torzs in torzsek(utasitas):
                szel = max(szel, self._szukseges_szel(torzs, melyseg + 1))
        return szel

    def _rajzol(self) -> None:
        v = self.vaszon
        v.delete("all")
        self._jelolo = []
        self._teruletek = []
        self._helyek = []
        self._sor_y = {}
        lathato = max(v.winfo_width() - 14, MIN_SZELESSEG)
        self._jobb_szel = max(lathato, self._szukseges_szel(self.program, 0), MIN_SZELESSEG)
        y = self._lista_rajzol(self.program, 0, FELSO_MARGO, None)
        if not self.program:
            _kerek(v, BAL_MARGO, FELSO_MARGO, self._jobb_szel, FELSO_MARGO + 70, 10,
                   fill=TORZS_HATTER, outline=MEZO_SZEGELY, dash=(4, 3))
            v.create_text((BAL_MARGO + self._jobb_szel) / 2, FELSO_MARGO + 35, fill=stilus.HALVANY,
                          font=stilus.tk_betu(11), justify="center",
                          text="Üres program.\nHúzz ide egy blokkot a bal oldali palettáról!")
            self._helyek = [Hely(self.program, 0, BAL_MARGO, FELSO_MARGO + 35)]
            y = FELSO_MARGO + 80
        self._also_y = y
        v.configure(scrollregion=(0, 0, self._jobb_szel + 8, y + 40))
        if y + 40 <= v.winfo_height():
            v.yview_moveto(0)  # ha minden kifér, ne maradjon üres sáv felül

    def _lista_rajzol(self, lista: list[Utasitas], melyseg: int, y: float,
                      szulo: Utasitas | None) -> float:
        x = BAL_MARGO + melyseg * BEHUZAS
        if not lista:
            # Üres törzs: szaggatott helyőrző, ide lehet blokkot húzni.
            if szulo is not None:
                _kerek(self.vaszon, x + 4, y + 2, self._jobb(melyseg) - 4, y + URES_H - 4, 6,
                       fill=TORZS_HATTER, outline=MEZO_SZEGELY, dash=(3, 3))
                self.vaszon.create_text(x + 14, y + URES_H / 2 - 1, anchor="w", fill=stilus.HALVANY,
                                        font=stilus.tk_betu(9), text="(üres törzs – húzz ide blokkot)")
                self._teruletek.append(Terulet(x, y, self._jobb(melyseg), y + URES_H, "ures", szulo))
                self._helyek.append(Hely(lista, 0, x, y + URES_H / 2))
                return y + URES_H
            return y
        for index, utasitas in enumerate(lista):
            self._helyek.append(Hely(lista, index, x, y - KOZ / 2))
            y = self._utasitas_rajzol(utasitas, melyseg, x, y) + KOZ
        self._helyek.append(Hely(lista, len(lista), x, y - KOZ / 2))
        return y

    def _keret(self, utasitas: Utasitas, sorszam: int | None) -> tuple[str, int, str | None]:
        """(szegélyszín, vastagság, kiemelő háttér) a kijelölés / futás szerint."""
        if sorszam is not None and sorszam == self.aktualis_sorszam:
            if self.aktualis_hibas:
                return SZIN_HIBAS, 3, SZIN_HIBAS_HATTER
            return SZIN_AKTUALIS, 3, SZIN_AKTUALIS_HATTER
        if utasitas is self.kijelolt:
            return SZIN_KIJELOLT, 3, None
        return BLOKK_SZINEK[type(utasitas)][1], 1, None

    def _utasitas_rajzol(self, utasitas: Utasitas, melyseg: int, x: float, y: float) -> float:
        v = self.vaszon
        kitoltes, _szegely = BLOKK_SZINEK[type(utasitas)]
        jobb = self._jobb(melyseg)
        if not vezerlo_e(utasitas):
            szin, vastag, hatter = self._keret(utasitas, utasitas.sorszam)
            _kerek(v, x, y, jobb, y + FEJ_H, 7, fill=hatter or kitoltes, outline=szin, width=vastag)
            self._sorszam_rajzol(utasitas.sorszam, y, FEJ_H)
            self._teruletek.append(Terulet(x, y, jobb, y + FEJ_H, "blokk", utasitas))
            self._fej_rajzol(utasitas, x + 10, y + FEJ_H / 2)
            self._sor_y[utasitas.sorszam] = (y, y + FEJ_H)
            return y + FEJ_H
        # Vezérlőblokk: C alak – fej, törzs(ek), (else), láb. Előbb a háttér, aztán a tartalom.
        teteje = y
        szin, vastag, hatter = self._keret(utasitas, utasitas.sorszam)
        _kerek(v, x, teteje, jobb, teteje + self._magassag(utasitas), 8,
               fill=kitoltes, outline=szin, width=vastag)
        if hatter:
            v.create_rectangle(x + 3, y + 3, jobb - 3, y + FEJ_H - 1, fill=hatter, width=0)
        self._sorszam_rajzol(utasitas.sorszam, y, FEJ_H)
        self._teruletek.append(Terulet(x, y, jobb, y + FEJ_H, "blokk", utasitas))
        self._fej_rajzol(utasitas, x + 10, y + FEJ_H / 2)
        self._sor_y[utasitas.sorszam] = (y, y + FEJ_H)
        y += FEJ_H
        for index, torzs in enumerate(torzsek(utasitas)):
            if index == 1:
                e_hatter = self._keret(utasitas, utasitas.else_sorszam)[2]
                if e_hatter:
                    v.create_rectangle(x + 3, y, jobb - 3, y + ELSE_H, fill=e_hatter, width=0)
                v.create_text(x + 10, y + ELSE_H / 2, anchor="w", text="else",
                              font=self._betu_vastag, fill=stilus.SZOVEG)
                self._sorszam_rajzol(utasitas.else_sorszam, y, ELSE_H)
                self._teruletek.append(Terulet(x, y, jobb, y + ELSE_H, "blokk", utasitas))
                self._sor_y[utasitas.else_sorszam] = (y, y + ELSE_H)
                y += ELSE_H
            v.create_rectangle(x + BEHUZAS - 3, y, jobb - JOBB_LEPCSO + 4, y + self._lista_magassag(torzs),
                               fill=TORZS_HATTER, outline=_szegely)
            y = self._lista_rajzol(torzs, melyseg + 1, y, utasitas)
        self._teruletek.append(Terulet(x, y, jobb, y + LAB_H, "blokk", utasitas))
        return y + LAB_H

    def _magassag(self, utasitas: Utasitas) -> float:
        """A blokk teljes magassága a törzseivel együtt (a rajzolással egyező módon)."""
        if not vezerlo_e(utasitas):
            return FEJ_H
        torzsek_ = torzsek(utasitas)
        magassag = FEJ_H + LAB_H + sum(self._lista_magassag(torzs) for torzs in torzsek_)
        return magassag + (ELSE_H if len(torzsek_) == 2 else 0)

    def _lista_magassag(self, lista: list[Utasitas]) -> float:
        if not lista:
            return URES_H
        return sum(self._magassag(utasitas) + KOZ for utasitas in lista)

    def _jobb(self, melyseg: int) -> float:
        """A blokkok jobb széle: minden szint kicsit beljebb, hogy a C alak látsszon."""
        return self._jobb_szel - melyseg * JOBB_LEPCSO

    def _sorszam_rajzol(self, sorszam: int, y: float, magassag: float) -> None:
        self.vaszon.create_text(BAL_MARGO - 8, y + magassag / 2, anchor="e", text=str(sorszam),
                                fill="#94a3b8", font=stilus.tk_mono(9))

    def _fej_rajzol(self, utasitas: Utasitas, x: float, ykozep: float) -> float:
        return self._elemek_rajzol(utasitas, fej_elemek(utasitas), x, ykozep)

    def _elemek_rajzol(self, utasitas: Utasitas, elemek: list[tuple], x: float, yk: float) -> float:
        v = self.vaszon
        for elem in elemek:
            if elem[0] == "szo":
                v.create_text(x, yk, anchor="w", text=elem[1], font=self._betu_vastag, fill=stilus.SZOVEG)
                x += self._szoveg_szel(elem[1], True) + 8
            elif elem[0] == "muvelet":
                szoveg = mezo_ertek(utasitas, "muvelet")
                szel = self._szoveg_szel(szoveg, True) + 12
                _kerek(v, x, yk - 10, x + szel, yk + 10, 5, fill="#fed7aa", outline=ERTEK_SZIN[1])
                v.create_text(x + szel / 2, yk, text=szoveg, font=self._betu_vastag, fill="#7c2d12")
                self._teruletek.append(Terulet(x, yk - 10, x + szel, yk + 10, "muvelet", utasitas, "muvelet"))
                x += szel + 6
            elif elem[0] == "mezo":
                x = self._mezo_rajzol(utasitas, elem[1], x, yk)
            else:
                szel = self._elemek_szel(utasitas, elem[1]) + CHIP_W + 10
                _kerek(v, x - 2, yk - 14, x + szel, yk + 14, 7, fill=ERTEK_SZIN[0], outline=ERTEK_SZIN[1])
                belso_x = self._elemek_rajzol(utasitas, elem[1], x + 6, yk)
                cx = belso_x
                _kerek(v, cx, yk - 9, cx + CHIP_W, yk + 9, 4, fill="#fdba74", outline="")
                v.create_text(cx + CHIP_W / 2, yk, text="▾", font=stilus.tk_betu(10), fill="#7c2d12")
                self._teruletek.append(Terulet(x - 2, yk - 14, x + szel, yk + 14, "kif_fajta_hatter", utasitas))
                self._teruletek.append(Terulet(cx, yk - 9, cx + CHIP_W, yk + 9, "kif_fajta", utasitas))
                x += szel + 8
        return x

    def _mezo_rajzol(self, utasitas: Utasitas, kulcs: str, x: float, yk: float) -> float:
        v = self.vaszon
        szoveg = mezo_ertek(utasitas, kulcs)
        szel = max(28, self._mono.measure(szoveg) + 14)
        _kerek(v, x, yk - MEZO_H / 2, x + szel, yk + MEZO_H / 2, 5, fill=MEZO_HATTER,
               outline=MEZO_SZEGELY)
        v.create_text(x + szel / 2, yk, text=szoveg, font=self._mono, fill="#0f172a")
        self._teruletek.append(Terulet(x, yk - MEZO_H / 2, x + szel, yk + MEZO_H / 2, "mezo", utasitas, kulcs))
        x += szel + 2
        if leptetheto_e(szoveg):
            for tipus, jel in (("minusz", "−"), ("plusz", "+")):
                _kerek(v, x, yk - 9, x + CHIP_W, yk + 9, 4, fill="#e2e8f0", outline="#94a3b8")
                v.create_text(x + CHIP_W / 2, yk, text=jel, font=stilus.tk_betu(10, True),
                              fill="#0f172a")
                self._teruletek.append(Terulet(x, yk - 9, x + CHIP_W, yk + 9, tipus, utasitas, kulcs))
                x += CHIP_W + 2
            x += 2
        return x + 4

    # ---------- Találatkeresés ----------

    def _talalat(self, x: float, y: float) -> Terulet | None:
        """A legkonkrétabb terület a pont alatt (mező > gomb > blokk)."""
        elsobbseg = {"minusz": 0, "plusz": 0, "kif_fajta": 0, "mezo": 1, "muvelet": 1,
                     "kif_fajta_hatter": 2, "blokk": 3, "ures": 3}
        jeloltek = [t for t in self._teruletek if t.benne(x, y)]
        if not jeloltek:
            return None
        return min(jeloltek, key=lambda t: elsobbseg[t.tipus])

    def _vaszon_pont(self, esemeny) -> tuple[float, float]:
        return self.vaszon.canvasx(esemeny.x), self.vaszon.canvasy(esemeny.y)

    def _mutato(self, esemeny) -> None:
        if self._huzas is not None:
            return
        talalat = self._talalat(*self._vaszon_pont(esemeny))
        kurzor = ""
        if talalat is not None:
            kurzor = {"mezo": "xterm", "blokk": "fleur"}.get(talalat.tipus, "hand2")
        self.vaszon.configure(cursor=kurzor)

    # ---------- Egér: kijelölés, mezők, húzás ----------

    def _nyomas(self, esemeny) -> None:
        self.vaszon.focus_set()
        x, y = self._vaszon_pont(esemeny)
        talalat = self._talalat(x, y)
        self._huzas = None
        if talalat is None:
            self.kijelol(None)
            return
        if talalat.tipus in ("minusz", "plusz"):
            self._leptet(talalat.utasitas, talalat.kulcs, -1 if talalat.tipus == "minusz" else 1)
            return
        if talalat.tipus == "mezo":
            self.kijelol(talalat.utasitas)
            self._mezo_szerkeszt(talalat.utasitas, talalat.kulcs)
            return
        if talalat.tipus == "muvelet":
            self.kijelol(talalat.utasitas)
            self._muvelet_menu(talalat.utasitas, esemeny)
            return
        if talalat.tipus == "kif_fajta":
            self.kijelol(talalat.utasitas)
            self._kif_menu(talalat.utasitas, esemeny)
            return
        self.kijelol(talalat.utasitas)
        if talalat.tipus in ("blokk", "kif_fajta_hatter"):
            self._huzas = {"utasitas": talalat.utasitas, "x": x, "y": y, "aktiv": False, "hely": None}

    def _huzas_mozog(self, esemeny) -> None:
        if self._huzas is None:
            return
        x, y = self._vaszon_pont(esemeny)
        if not self._huzas["aktiv"]:
            if abs(x - self._huzas["x"]) + abs(y - self._huzas["y"]) < HUZAS_KUSZOB:
                return
            self._huzas["aktiv"] = True
            self.vaszon.configure(cursor="fleur")
        self._automatikus_gorgetes(esemeny.y)
        self._jelolo_rajzol(x, y, mozgatott=self._huzas["utasitas"], felirat=fej_szoveg(self._huzas["utasitas"]))

    def _elengedes(self, esemeny) -> None:
        huzas, self._huzas = self._huzas, None
        self._jelolo_torol()
        self.vaszon.configure(cursor="")
        if huzas is None or not huzas["aktiv"]:
            return
        hely: Hely | None = huzas["hely"]
        if hely is None:
            return
        try:
            athelyez(self.program, huzas["utasitas"], hely.lista, hely.index)
        except SzerkesztesiHiba as hiba:
            self._uzenet(f"Nem helyezhető ide: {hiba}", True)
            self._rajzol()
            return
        self._valtozott()
        self.kijelol(huzas["utasitas"])
        self._uzenet("Blokk áthelyezve.", False)

    def _dupla_kattintas(self, esemeny) -> None:
        talalat = self._talalat(*self._vaszon_pont(esemeny))
        if talalat is not None and talalat.tipus == "blokk" and vezerlo_e(talalat.utasitas):
            self._mezo_szerkeszt(talalat.utasitas, "feltetel")

    def _automatikus_gorgetes(self, kepernyo_y: int) -> None:
        magassag = self.vaszon.winfo_height()
        if kepernyo_y < 24:
            self.vaszon.yview_scroll(-1, "units")
        elif kepernyo_y > magassag - 24:
            self.vaszon.yview_scroll(1, "units")

    # ---------- Ledobási hely jelölése ----------

    def _legkozelebbi_hely(self, x: float, y: float) -> Hely | None:
        if not self._helyek:
            return None
        return min(self._helyek, key=lambda h: abs(h.y - y) + 0.35 * abs(h.x - x + 30))

    def _jelolo_torol(self) -> None:
        for azonosito in self._jelolo:
            self.vaszon.delete(azonosito)
        self._jelolo = []

    def _jelolo_rajzol(self, x: float, y: float, mozgatott: Utasitas | None = None,
                       fajta: BlokkFajta | None = None, felirat: str = "") -> None:
        """Kék vonal a ledobás helyén (piros, ha oda nem tehető), mellette a blokk neve."""
        self._jelolo_torol()
        hely = self._legkozelebbi_hely(x, y)
        if self._huzas is not None:
            self._huzas["hely"] = hely
        if hely is None:
            return
        if mozgatott is not None:
            hiba = athelyezes_hiba(self.program, mozgatott, hely.lista)
        else:
            hiba = beszuras_ide_hiba(self.program, hely.lista, fajta)
        szin = SZIN_ROSSZ_HELY if hiba else SZIN_JO_HELY
        v = self.vaszon
        self._jelolo.append(v.create_line(hely.x, hely.y, self._jobb_szel, hely.y, fill=szin, width=4))
        self._jelolo.append(v.create_oval(hely.x - 5, hely.y - 5, hely.x + 5, hely.y + 5, fill=szin, outline=""))
        cimke = hiba if hiba else f"ide kerül: {felirat}"
        szoveg = v.create_text(x + 14, y - 14, anchor="w", text=cimke, fill=szin, font=stilus.tk_betu(10, True))
        doboz = v.bbox(szoveg)
        if doboz:
            hatter = v.create_rectangle(doboz[0] - 4, doboz[1] - 2, doboz[2] + 4, doboz[3] + 2,
                                        fill="#ffffff", outline=szin)
            v.tag_lower(hatter, szoveg)
            self._jelolo.append(hatter)
        self._jelolo.append(szoveg)

    # ---------- Paletta: kattintás vagy húzás ----------

    def _paletta_nyom(self, fajta: BlokkFajta, esemeny) -> None:
        self._szerkesztes_vege(mentes=True)
        self._huzas = {"fajta": fajta, "x": esemeny.x_root, "y": esemeny.y_root,
                       "aktiv": False, "hely": None}

    def _vaszon_alatt(self, x_root: int, y_root: int) -> tuple[float, float] | None:
        v = self.vaszon
        vx, vy = x_root - v.winfo_rootx(), y_root - v.winfo_rooty()
        if 0 <= vx <= v.winfo_width() and 0 <= vy <= v.winfo_height():
            return v.canvasx(vx), v.canvasy(vy)
        return None

    def _paletta_huz(self, esemeny) -> None:
        huzas = self._huzas
        if huzas is None or "fajta" not in huzas:
            return
        if not huzas["aktiv"]:
            if abs(esemeny.x_root - huzas["x"]) + abs(esemeny.y_root - huzas["y"]) < HUZAS_KUSZOB:
                return
            huzas["aktiv"] = True
            self.winfo_toplevel().configure(cursor="fleur")
        pont = self._vaszon_alatt(esemeny.x_root, esemeny.y_root)
        if pont is None:
            self._jelolo_torol()
            huzas["hely"] = None
            return
        self._automatikus_gorgetes(esemeny.y_root - self.vaszon.winfo_rooty())
        self._jelolo_rajzol(*pont, fajta=huzas["fajta"], felirat=FAJTA_NEVEK[huzas["fajta"]])

    def _paletta_enged(self, _esemeny) -> None:
        huzas, self._huzas = self._huzas, None
        self.winfo_toplevel().configure(cursor="")
        self._jelolo_torol()
        if huzas is None or "fajta" not in huzas:
            return
        fajta = huzas["fajta"]
        try:
            if huzas["aktiv"]:
                hely: Hely | None = huzas["hely"]
                if hely is None:
                    return
                uj = beszur_ide(self.program, hely.lista, hely.index, fajta)
            else:
                uj = beszur(self.program, self.kijelolt, BeszurasHelye.MOGE, fajta)
        except SzerkesztesiHiba as hiba:
            self._uzenet(f"Nem szúrható be: {hiba}", True)
            self._rajzol()
            return
        self._uj_blokk_kesz(uj)

    def _uj_blokk_kesz(self, uj: Utasitas) -> None:
        self._valtozott()
        self.kijelol(uj)
        self._lathatova_tesz(uj.sorszam)
        self._uzenet(f"Új blokk: {fej_szoveg(uj)}", False)
        # Vezérlőblokknál és értékadásnál rögtön a legfontosabb mezőt lehet gépelni.
        if vezerlo_e(uj):
            self._mezo_szerkeszt(uj, "feltetel")
        elif isinstance(uj, Ertekadas):
            self._mezo_szerkeszt(uj, "nev")

    # ---------- Mezők szerkesztése ----------

    def _mezo_terulet(self, utasitas: Utasitas, kulcs: str) -> Terulet | None:
        for terulet in self._teruletek:
            if terulet.tipus == "mezo" and terulet.utasitas is utasitas and terulet.kulcs == kulcs:
                return terulet
        return None

    def _mezo_szerkeszt(self, utasitas: Utasitas, kulcs: str) -> None:
        """A mező helyén beviteli mező nyílik; Enter: alkalmaz, Esc: mégse."""
        self._szerkesztes_vege(mentes=True)
        terulet = self._mezo_terulet(utasitas, kulcs)
        if terulet is None:
            return
        mezo = tk.Entry(self.vaszon, font=self._mono, relief="solid", borderwidth=1,
                        highlightthickness=2, highlightcolor=stilus.KIEMELO, justify="center")
        mezo.insert(0, mezo_ertek(utasitas, kulcs))
        mezo.select_range(0, "end")
        szel = max(terulet.x1 - terulet.x0 + 40, 90)
        ablak = self.vaszon.create_window(terulet.x0 - 2, (terulet.y0 + terulet.y1) / 2, anchor="w",
                                          window=mezo, width=szel, height=MEZO_H + 6)
        self._szerkeszto_mezo = mezo
        mezo._adat = (utasitas, kulcs, ablak)  # type: ignore[attr-defined]
        mezo.bind("<Return>", lambda _e: self._szerkesztes_vege(mentes=True))
        mezo.bind("<KP_Enter>", lambda _e: self._szerkesztes_vege(mentes=True))
        mezo.bind("<Escape>", lambda _e: self._szerkesztes_vege(mentes=False))
        mezo.bind("<FocusOut>", lambda _e: self._szerkesztes_vege(mentes=True))
        mezo.bind("<Up>", lambda _e: self._mezo_leptet(mezo, 1))
        mezo.bind("<Down>", lambda _e: self._mezo_leptet(mezo, -1))
        mezo.focus_set()
        self._uzenet("Írd be az új értéket, majd Enter (Esc: mégse). ↑/↓: léptetés. "
                     "Jobb klikk a mezőn: választás a meglévő változók közül.", False)

    def _mezo_leptet(self, mezo: tk.Entry, irany: int) -> str:
        uj = ertek_leptet(mezo.get().strip(), irany)
        mezo.delete(0, "end")
        mezo.insert(0, uj)
        return "break"

    def _szerkesztes_vege(self, mentes: bool) -> None:
        mezo = self._szerkeszto_mezo
        if mezo is None:
            return
        self._szerkeszto_mezo = None
        utasitas, kulcs, ablak = mezo._adat  # type: ignore[attr-defined]
        szoveg = mezo.get().strip()
        self.vaszon.delete(ablak)
        mezo.destroy()
        if not mentes or szoveg == mezo_ertek(utasitas, kulcs):
            self._rajzol()
            return
        hiba = mezo_hiba(kulcs, szoveg)
        if hiba is not None:
            self._uzenet(f"Érvénytelen érték, nem módosult: {hiba}", True)
            self._rajzol()
            return
        mezo_beallit(utasitas, kulcs, szoveg)
        self._valtozott()
        self._uzenet("Mező módosítva.", False)

    def _leptet(self, utasitas: Utasitas, kulcs: str, irany: int) -> None:
        regi = mezo_ertek(utasitas, kulcs)
        uj = ertek_leptet(regi, irany)
        self.kijelol(utasitas)
        if uj == regi:
            self._uzenet("A határon van: a szám 0 és 100 között lehet.", True)
            return
        mezo_beallit(utasitas, kulcs, uj)
        self._valtozott()

    def _valtozonevek(self, lista: list[Utasitas] | None = None, nevek: set[str] | None = None) -> set[str]:
        nevek = set() if nevek is None else nevek
        for utasitas in self.program if lista is None else lista:
            if isinstance(utasitas, Ertekadas):
                nevek.add(utasitas.nev)
            for torzs in torzsek(utasitas):
                self._valtozonevek(torzs, nevek)
        return nevek

    def _mezo_menu(self, utasitas: Utasitas, kulcs: str, esemeny) -> None:
        """Jobb klikk egy mezőn: választható értékek listája."""
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_betu(10))
        nevek = sorted(self._valtozonevek())
        if kulcs != "nev":
            menu.add_command(label="true", command=partial(self._mezo_valaszt, utasitas, kulcs, "true"))
            menu.add_command(label="false", command=partial(self._mezo_valaszt, utasitas, kulcs, "false"))
            for szam in ("0", "1", "2"):
                menu.add_command(label=szam, command=partial(self._mezo_valaszt, utasitas, kulcs, szam))
        if nevek:
            menu.add_separator()
            menu.add_command(label="Meglévő változók:", state="disabled")
            for nev in nevek:
                menu.add_command(label="   " + nev, command=partial(self._mezo_valaszt, utasitas, kulcs, nev))
        menu.add_separator()
        menu.add_command(label="Átírás…", command=partial(self._mezo_szerkeszt, utasitas, kulcs))
        menu.tk_popup(esemeny.x_root, esemeny.y_root)

    def _mezo_valaszt(self, utasitas: Utasitas, kulcs: str, szoveg: str) -> None:
        hiba = mezo_hiba(kulcs, szoveg)
        if hiba is not None:
            self._uzenet(hiba, True)
            return
        mezo_beallit(utasitas, kulcs, szoveg)
        self._valtozott()

    def _muvelet_menu(self, utasitas: Ertekadas, esemeny) -> None:
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_mono(11))
        for muvelet in Muvelet:
            menu.add_command(label=f"  {muvelet.value}  ",
                             command=partial(self._mezo_valaszt, utasitas, "muvelet", muvelet.value))
        menu.tk_popup(esemeny.x_root, esemeny.y_root)

    def _kif_menu(self, utasitas: Ertekadas, esemeny) -> None:
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_betu(10))
        menu.add_command(label="Érték-blokk cseréje:", state="disabled")
        for felirat, fajta in ERTEK_BLOKK_MENU:
            menu.add_command(label="   " + felirat, command=partial(self._kif_valt, utasitas, fajta))
        menu.tk_popup(esemeny.x_root, esemeny.y_root)

    def _kif_valt(self, utasitas: Ertekadas, fajta: str) -> None:
        kif_atalakit(utasitas, fajta)
        self._valtozott()

    # ---------- Jobb klikk ----------

    def _jobb_kattintas(self, esemeny) -> None:
        self._szerkesztes_vege(mentes=True)
        talalat = self._talalat(*self._vaszon_pont(esemeny))
        if talalat is not None and talalat.tipus == "mezo":
            self.kijelol(talalat.utasitas)
            self._mezo_menu(talalat.utasitas, talalat.kulcs, esemeny)
            return
        self.kijelol(talalat.utasitas if talalat else None)
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_betu(10))
        for hely, felirat in ((BeszurasHelye.ELE, "Új blokk elé"), (BeszurasHelye.MOGE, "Új blokk mögé"),
                              (BeszurasHelye.TORZSBE, "Új blokk a törzsbe"),
                              (BeszurasHelye.ELSE_AGBA, "Új blokk az else-ágba")):
            almenu = tk.Menu(menu, tearoff=False, font=stilus.tk_betu(10))
            for fajta in (*FAJTA_NEVEK,):
                hiba = beszuras_hiba(self.program, self.kijelolt, hely, fajta)
                almenu.add_command(label=FAJTA_NEVEK[fajta], state="normal" if hiba is None else "disabled",
                                   command=partial(self._beszur_menu, hely, fajta))
            elerheto = any(beszuras_hiba(self.program, self.kijelolt, hely, f) is None for f in FAJTA_NEVEK)
            menu.add_cascade(label=felirat, menu=almenu, state="normal" if elerheto else "disabled")
        if self.kijelolt is not None:
            menu.add_separator()
            if isinstance(self.kijelolt, Elagazas):
                felirat = "Else-ág eltávolítása" if self.kijelolt.hamis_ag is not None else "Else-ág hozzáadása"
                menu.add_command(label=felirat, command=self._else_valt)
            menu.add_command(label="Feljebb (Alt+↑)", command=partial(self._mozgat, -1))
            menu.add_command(label="Lejjebb (Alt+↓)", command=partial(self._mozgat, 1))
            menu.add_command(label="Törlés (Delete)", command=self._torles)
        menu.tk_popup(esemeny.x_root, esemeny.y_root)

    def _beszur_menu(self, hely: BeszurasHelye, fajta: BlokkFajta) -> None:
        try:
            uj = beszur(self.program, self.kijelolt, hely, fajta)
        except SzerkesztesiHiba as hiba:
            self._uzenet(f"Nem szúrható be: {hiba}", True)
            return
        self._uj_blokk_kesz(uj)

    # ---------- Eszközsor műveletei ----------

    def _torles(self) -> None:
        if self.kijelolt is None:
            self._uzenet("Előbb jelölj ki egy blokkot.", True)
            return
        if any(torzsek(self.kijelolt)) and not messagebox.askyesno(
                "Törlés", "A blokk a teljes tartalmával együtt törlődik. Biztosan?", parent=self):
            return
        torol(self.program, self.kijelolt)
        self.kijelolt = None
        self._valtozott()
        self.kijelol(None)
        self._uzenet("Blokk törölve (Ctrl+Z: visszavonás).", False)

    def _mozgat(self, irany: int) -> None:
        if self.kijelolt is None:
            return
        poz = pozicio_keres(self.program, self.kijelolt)
        uj_index = poz.index + irany
        if not 0 <= uj_index < len(poz.lista):
            self._uzenet("A blokk már a törzs " + ("elején." if irany < 0 else "végén.") +
                         " Más törzsbe húzással helyezhető át.", True)
            return
        poz.lista[poz.index], poz.lista[uj_index] = poz.lista[uj_index], poz.lista[poz.index]
        self._valtozott()
        self.kijelol(self.kijelolt)

    def _else_valt(self) -> None:
        if not isinstance(self.kijelolt, Elagazas):
            return
        if self.kijelolt.hamis_ag and not messagebox.askyesno(
                "Else-ág", "Az else-ág a tartalmával együtt törlődik. Biztosan?", parent=self):
            return
        else_ag_valt(self.kijelolt)
        self._valtozott()
        self.kijelol(self.kijelolt)

    def _szomszed_kijelol(self, irany: int) -> str:
        sorrend: list[Utasitas] = []

        def bejar(lista: list[Utasitas]) -> None:
            for utasitas in lista:
                sorrend.append(utasitas)
                for torzs in torzsek(utasitas):
                    bejar(torzs)
        bejar(self.program)
        if not sorrend:
            return "break"
        if self.kijelolt not in sorrend:
            self.kijelol(sorrend[0 if irany > 0 else -1])
        else:
            index = min(max(sorrend.index(self.kijelolt) + irany, 0), len(sorrend) - 1)
            self.kijelol(sorrend[index])
        self._lathatova_tesz(self.kijelolt.sorszam)
        return "break"

    # ---------- Segédek ----------

    def _sorszam_utasitas(self, lista: list[Utasitas], sorszam: int) -> Utasitas | None:
        for utasitas in lista:
            if utasitas.sorszam == sorszam:
                return utasitas
            if isinstance(utasitas, Elagazas) and utasitas.hamis_ag is not None \
                    and utasitas.else_sorszam == sorszam:
                return utasitas
            for torzs in torzsek(utasitas):
                talalat = self._sorszam_utasitas(torzs, sorszam)
                if talalat is not None:
                    return talalat
        return None

    def _lathatova_tesz(self, sorszam: int) -> None:
        if sorszam not in self._sor_y:
            return
        y0, y1 = self._sor_y[sorszam]
        teteje = self.vaszon.canvasy(0)
        alja = teteje + self.vaszon.winfo_height()
        if y0 < teteje or y1 > alja:
            osszes = max(self._also_y + 40, 1)
            self.vaszon.yview_moveto(max(0.0, (y0 - 3 * FEJ_H) / osszes))
