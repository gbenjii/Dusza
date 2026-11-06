"""Vizuális blokkszerkesztő: a program színes blokkokként, kijelölés, beszúrás menüből, törlés.

A program szerkesztése CSAK itt lehetséges. Minden módosítás után a
`valtozott` függvény hívódik, ami a szöveges nézetet is frissíti.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from tkinter import messagebox, ttk

from gui.tooltip import Tooltip
from gui.tulajdonsag_panel import TulajdonsagPanel
from nyelv.kiiro import fej_szoveg
from nyelv.szerkesztes import (
    VEZERLO_FAJTAK, BeszurasHelye, BlokkFajta, SzerkesztesiHiba, beszur, beszuras_hiba,
    torol, torzsek,
)
from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertekadas, Fordulas, Kiiras, Lepes, Utasitas, vezerlo_e,
)

SOR_MAGASSAG = 30
LAB_MAGASSAG = 12
SOR_KOZ = 2
BEHUZAS_PX = 26
BAL_MARGO = 36
FELSO_MARGO = 8
BLOKK_SZELESSEG = 250
SAV_SZELESSEG = 12
KARAKTER_PX = 8
BLOKK_BETU = ("Consolas", 10, "bold")

FEJ, ELSE, LAB, URES = "fej", "else", "lab", "ures"

BLOKK_SZINEK: dict[type, str] = {
    Lepes: "#4c97ff", Fordulas: "#4c97ff", Banyaszas: "#4c97ff",
    Kiiras: "#9966ff", Ertekadas: "#ff8c1a", Elagazas: "#e6a100", Ciklus: "#2fa83a",
}
SZIN_KIJELOLT = "#0d1b5e"
SZIN_AKTUALIS = "#ff1744"

PARANCS_FAJTAK = (BlokkFajta.LEPES, BlokkFajta.FORDULAS, BlokkFajta.BANYASZAS,
                  BlokkFajta.KIIRAS, BlokkFajta.ERTEKADAS)
FAJTA_FELIRATOK: dict[BlokkFajta, str] = {
    BlokkFajta.LEPES: "step forward – lépés előre",
    BlokkFajta.FORDULAS: "turn by – fordulás balra",
    BlokkFajta.BANYASZAS: "mine here – bányászás",
    BlokkFajta.KIIRAS: "print – kiírás",
    BlokkFajta.ERTEKADAS: "set – értékadás",
    BlokkFajta.HA: "if – elágazás",
    BlokkFajta.HA_KULONBEN: "if-else – kétirányú elágazás",
    BlokkFajta.AMIG: "while – ciklus",
}
HELY_GOMBOK = (
    (BeszurasHelye.ELE, "＋ Elé", "Új blokk a kijelölt blokk ELÉ (ha nincs kijelölés: a program elejére)."),
    (BeszurasHelye.MOGE, "＋ Mögé", "Új blokk a kijelölt blokk MÖGÉ (ha nincs kijelölés: a program végére)."),
    (BeszurasHelye.TORZSBE, "＋ Törzsbe", "Új blokk a kijelölt if / while blokk törzsének végére."),
    (BeszurasHelye.ELSE_AGBA, "＋ Else-ágba", "Új blokk a kijelölt if-else blokk else-ágának végére."),
)
SUGO = ("① Kattints egy blokkra (kijelölés)  ② ＋ menükkel szúrj be új blokkot  "
        "③ Lent írd át a mezőket.  Jobb klikk: helyi menü, Delete: törlés.")


@dataclass
class BlokkSor:
    """A vásznon egy vízszintes sáv: egy blokk feje, else-sora, lába vagy üres törzse."""

    utasitas: Utasitas
    resz: str
    melyseg: int
    y: int
    magassag: int
    sorszam: int | None


class Blokkszerkeszto(ttk.LabelFrame):
    """A blokknézet és a hozzá tartozó szerkesztő vezérlők."""

    def __init__(self, master: tk.Misc, program: list[Utasitas], valtozott: Callable[[], None],
                 kijeloles_valtozott: Callable[[Utasitas | None], None]) -> None:
        super().__init__(master, text="Blokkszerkesztő")
        self.program = program
        self.kijelolt: Utasitas | None = None
        self.aktualis_sorszam: int | None = None
        self._valtozott = valtozott
        self._kijeloles_valtozott = kijeloles_valtozott
        self._sorok: list[BlokkSor] = []
        self._kovetkezo_y = FELSO_MARGO
        self._menuk: list[tuple[tk.Menu, BeszurasHelye]] = []
        self._eszkoztar()
        self._vaszon_letrehoz()
        self.panel = TulajdonsagPanel(self, self._mezo_modosult)
        self.panel.pack(fill="x", padx=4, pady=4)
        self._helyi_menu = self._helyi_menu_letrehoz()

    # ---------- Nyilvános felület ----------

    def program_beallit(self, program: list[Utasitas]) -> None:
        self.program = program
        self.kijelol(None)

    def frissit(self) -> None:
        """Újraépíti és újrarajzolja a blokkokat a modell alapján."""
        self._sorok = []
        self._kovetkezo_y = FELSO_MARGO
        self._blokk_sorai(self.program, 0)
        self._rajzol()

    def kijelol(self, utasitas: Utasitas | None) -> None:
        self.kijelolt = utasitas
        self.panel.megjelenit(utasitas)
        self._rajzol()
        self._kijeloles_valtozott(utasitas)

    def kijelol_sorszam(self, sorszam: int) -> None:
        for sor in self._sorok:
            if sor.sorszam == sorszam:
                self.kijelol(sor.utasitas)
                return

    def kiemel_sorszam(self, sorszam: int | None) -> None:
        """A futás közben végrehajtott sor kiemelése."""
        self.aktualis_sorszam = sorszam
        self._rajzol()
        for sor in self._sorok:
            if sor.sorszam == sorszam:
                self._lathatova_tesz(sor)

    # ---------- Eszköztár és menük ----------

    def _eszkoztar(self) -> None:
        keret = ttk.Frame(self)
        keret.pack(fill="x", padx=4, pady=(4, 0))
        for hely, felirat, sugo in HELY_GOMBOK:
            gomb = ttk.Menubutton(keret, text=felirat)
            gomb["menu"] = self._tipus_menu(gomb, hely)
            gomb.pack(side="left", padx=1)
            Tooltip(gomb, sugo)
        torles = ttk.Button(keret, text="🗑 Törlés", command=self._torles)
        torles.pack(side="left", padx=(8, 0))
        Tooltip(torles, "A kijelölt blokk törlése a teljes tartalmával együtt (Delete).")
        ttk.Label(self, text=SUGO, foreground="#555555", wraplength=380,
                  font=("Segoe UI", 8)).pack(fill="x", padx=6, pady=2)

    def _tipus_menu(self, szulo: tk.Misc, hely: BeszurasHelye) -> tk.Menu:
        """Blokktípus-választó menü; az állapotok megnyitáskor frissülnek."""
        menu = tk.Menu(szulo, tearoff=False)
        menu.add_command(label="Parancsblokkok:", state="disabled")
        for fajta in PARANCS_FAJTAK:
            menu.add_command(label="    " + FAJTA_FELIRATOK[fajta], command=partial(self._beszur, hely, fajta))
        menu.add_separator()
        menu.add_command(label="Vezérlőblokkok:", state="disabled")
        for fajta in VEZERLO_FAJTAK:
            menu.add_command(label="    " + FAJTA_FELIRATOK[fajta], command=partial(self._beszur, hely, fajta))
        menu.add_separator()
        menu.add_command(label="", state="disabled")  # ide kerül a tiltás oka
        menu.configure(postcommand=partial(self._menu_allapot, menu, hely))
        self._menuk.append((menu, hely))
        return menu

    def _menu_allapot(self, menu: tk.Menu, hely: BeszurasHelye) -> None:
        """Tiltja a nem beszúrható blokktípusokat, és kiírja az okát."""
        ok = ""
        for index, fajta in enumerate((*PARANCS_FAJTAK, *VEZERLO_FAJTAK)):
            menu_index = index + 1 if fajta in PARANCS_FAJTAK else index + 3
            hiba = beszuras_hiba(self.program, self.kijelolt, hely, fajta)
            menu.entryconfigure(menu_index, state="normal" if hiba is None else "disabled")
            ok = ok or (hiba or "")
        menu.entryconfigure("end", label=("⚠ " + ok) if ok else "Válassz blokktípust.")

    def _helyi_menu_letrehoz(self) -> tk.Menu:
        menu = tk.Menu(self, tearoff=False)
        for hely, felirat, _sugo in HELY_GOMBOK:
            menu.add_cascade(label=felirat, menu=self._tipus_menu(menu, hely))
        menu.add_separator()
        menu.add_command(label="🗑 Törlés (tartalmával együtt)", command=self._torles)
        return menu

    # ---------- Szerkesztő műveletek ----------

    def _beszur(self, hely: BeszurasHelye, fajta: BlokkFajta) -> None:
        try:
            uj = beszur(self.program, self.kijelolt, hely, fajta)
        except SzerkesztesiHiba as hiba:
            messagebox.showwarning("Nem szúrható be", str(hiba), parent=self)
            return
        self._valtozott()
        self.kijelol(uj)

    def _torles(self) -> None:
        if self.kijelolt is None:
            messagebox.showinfo("Törlés", "Előbb jelölj ki egy blokkot.", parent=self)
            return
        if any(torzsek(self.kijelolt)) and not messagebox.askyesno(
                "Törlés", "A blokk a teljes tartalmával együtt törlődik. Biztosan?", parent=self):
            return
        torol(self.program, self.kijelolt)
        self._valtozott()
        self.kijelol(None)

    def _mezo_modosult(self) -> None:
        self._valtozott()
        self.kijelol(self.kijelolt)

    # ---------- Sorok felépítése ----------

    def _uj_sor(self, utasitas: Utasitas, resz: str, melyseg: int, sorszam: int | None,
                magassag: int = SOR_MAGASSAG) -> None:
        self._sorok.append(BlokkSor(utasitas, resz, melyseg, self._kovetkezo_y, magassag, sorszam))
        self._kovetkezo_y += magassag

    def _blokk_sorai(self, utasitasok: list[Utasitas], melyseg: int) -> None:
        for utasitas in utasitasok:
            self._uj_sor(utasitas, FEJ, melyseg, utasitas.sorszam)
            if isinstance(utasitas, Ciklus):
                self._torzs_sorai(utasitas, utasitas.torzs, melyseg)
            if isinstance(utasitas, Elagazas):
                self._torzs_sorai(utasitas, utasitas.igaz_ag, melyseg)
                if utasitas.hamis_ag is not None:
                    self._uj_sor(utasitas, ELSE, melyseg, utasitas.else_sorszam)
                    self._torzs_sorai(utasitas, utasitas.hamis_ag, melyseg)
            if vezerlo_e(utasitas):
                self._uj_sor(utasitas, LAB, melyseg, None, LAB_MAGASSAG)

    def _torzs_sorai(self, szulo: Utasitas, torzs: list[Utasitas], melyseg: int) -> None:
        if torzs:
            self._blokk_sorai(torzs, melyseg + 1)
        else:
            self._uj_sor(szulo, URES, melyseg + 1, None)

    # ---------- Rajzolás ----------

    def _vaszon_letrehoz(self) -> None:
        keret = ttk.Frame(self)
        keret.pack(fill="both", expand=True, padx=4, pady=4)
        self.vaszon = tk.Canvas(keret, background="#f4f6fb", width=400, highlightthickness=1,
                                highlightbackground="#c5cae9")
        gorgeto = ttk.Scrollbar(keret, orient="vertical", command=self.vaszon.yview)
        self.vaszon.configure(yscrollcommand=gorgeto.set)
        self.vaszon.pack(side="left", fill="both", expand=True)
        gorgeto.pack(side="right", fill="y")
        self.vaszon.bind("<Button-1>", self._kattintas)
        self.vaszon.bind("<Button-3>", self._jobb_kattintas)
        self.vaszon.bind("<Delete>", lambda _e: self._torles())
        self.vaszon.bind("<MouseWheel>", self._gorgetes)

    def _rajzol(self) -> None:
        self.vaszon.delete("all")
        if not self._sorok:
            self.vaszon.create_text(BAL_MARGO, FELSO_MARGO + 10, anchor="w", fill="#777777",
                                    text="Üres program.\nA „＋ Mögé” menüvel szúrd be az első blokkot.")
        self._vezerlo_savok()
        for sor in self._sorok:
            self._sor_rajzol(sor)
        self.vaszon.configure(scrollregion=(0, 0, BLOKK_SZELESSEG * 2, self._kovetkezo_y + FELSO_MARGO))

    def _keret_szin(self, sor: BlokkSor) -> tuple[str, int]:
        if sor.sorszam is not None and sor.sorszam == self.aktualis_sorszam:
            return SZIN_AKTUALIS, 3
        if sor.utasitas is self.kijelolt:
            return SZIN_KIJELOLT, 3
        return "#444444", 1

    def _vezerlo_savok(self) -> None:
        """A vezérlőblokkok bal oldali függőleges sávja (C alak)."""
        elso: dict[int, BlokkSor] = {}
        for sor in self._sorok:
            if sor.resz == FEJ and vezerlo_e(sor.utasitas):
                elso[id(sor.utasitas)] = sor
            if sor.resz == LAB:
                fej = elso[id(sor.utasitas)]
                x0 = BAL_MARGO + fej.melyseg * BEHUZAS_PX
                szin, vastagsag = self._keret_szin(fej)
                self.vaszon.create_rectangle(x0, fej.y, x0 + SAV_SZELESSEG, sor.y + sor.magassag - SOR_KOZ,
                                             fill=BLOKK_SZINEK[type(sor.utasitas)], outline=szin,
                                             width=vastagsag)

    def _sor_rajzol(self, sor: BlokkSor) -> None:
        x0 = BAL_MARGO + sor.melyseg * BEHUZAS_PX
        y0, y1 = sor.y, sor.y + sor.magassag - SOR_KOZ
        szin = BLOKK_SZINEK[type(sor.utasitas)]
        keret, vastagsag = self._keret_szin(sor)
        if sor.resz == URES:
            self.vaszon.create_rectangle(x0, y0, x0 + BLOKK_SZELESSEG, y1, outline="#9e9e9e", dash=(3, 3))
            self.vaszon.create_text(x0 + 8, (y0 + y1) / 2, anchor="w", fill="#9e9e9e",
                                    text="(üres törzs – „＋ Törzsbe”)")
            return
        if sor.resz == LAB:
            self.vaszon.create_rectangle(x0, y0, x0 + BLOKK_SZELESSEG // 3, y1, fill=szin,
                                         outline=keret, width=vastagsag)
            return
        szoveg = "else" if sor.resz == ELSE else fej_szoveg(sor.utasitas)
        szelesseg = max(BLOKK_SZELESSEG, len(szoveg) * KARAKTER_PX + 24)
        self.vaszon.create_rectangle(x0, y0, x0 + szelesseg, y1, fill=szin, outline=keret, width=vastagsag)
        self.vaszon.create_text(x0 + 10, (y0 + y1) / 2, anchor="w", text=szoveg, fill="white", font=BLOKK_BETU)
        self.vaszon.create_text(BAL_MARGO - 6, (y0 + y1) / 2, anchor="e", text=str(sor.sorszam),
                                fill="#9e9e9e", font=("Consolas", 9))

    # ---------- Egér ----------

    def _sor_y_alapjan(self, y: float) -> BlokkSor | None:
        for sor in self._sorok:
            if sor.y <= y < sor.y + sor.magassag:
                return sor
        return None

    def _kattintas(self, esemeny: tk.Event) -> None:
        self.vaszon.focus_set()
        sor = self._sor_y_alapjan(self.vaszon.canvasy(esemeny.y))
        self.kijelol(sor.utasitas if sor else None)

    def _jobb_kattintas(self, esemeny: tk.Event) -> None:
        self._kattintas(esemeny)
        for menu, hely in self._menuk:
            self._menu_allapot(menu, hely)
        self._helyi_menu.tk_popup(esemeny.x_root, esemeny.y_root)

    def _gorgetes(self, esemeny: tk.Event) -> None:
        self.vaszon.yview_scroll(int(-esemeny.delta / 120), "units")

    def _lathatova_tesz(self, sor: BlokkSor) -> None:
        teteje = self.vaszon.canvasy(0)
        alja = teteje + self.vaszon.winfo_height()
        if sor.y < teteje or sor.y + sor.magassag > alja:
            osszes = max(self._kovetkezo_y + FELSO_MARGO, 1)
            self.vaszon.yview_moveto(max(0.0, (sor.y - 3 * SOR_MAGASSAG) / osszes))
