"""A szimulátor nézet: térkép, robot, felfedezett mezők, szenzor, aranyszámláló és kézi vezérlés."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from gui.tooltip import Tooltip
from terkep import Mezo, Vilag

CELLA_PX = 34
MARGO_PX = 2
ROBOT_MERET = 0.36
ARANY_MERET = 0.26

SZIN_URES_FELFEDEZETT = "#fff8e1"
SZIN_URES_ISMERETLEN = "#b0bec5"
SZIN_FAL_FELFEDEZETT = "#5d4037"
SZIN_FAL_ISMERETLEN = "#78868f"
SZIN_ARANY_FELFEDEZETT = "#ffc107"
SZIN_ARANY_ISMERETLEN = "#c9b26b"
SZIN_ROBOT = "#d32f2f"
SZIN_SZENZOR = "#1565c0"
SZIN_RACS = "#607d8b"

SZENZOR_SZOVEG = {Mezo.URES: "üres (0)", Mezo.FAL: "fal (1)", Mezo.ARANY: "arany (2)"}

KEZI_PARANCSOK = (
    ("⟲ Balra", "balra", "Fordulás balra 90°-kal (turn by 1)."),
    ("⟳ Jobbra", "jobbra", "Fordulás jobbra 90°-kal (turn by 3)."),
    ("⬆ Lépés", "lepes", "Egy mező előre (step forward 1). Falnál nem lép."),
    ("⛏ Bányászás", "banyasz", "Az arany kibányászása a robot mezőjén (mine here)."),
    ("↺ Alaphelyzet", "alaphelyzet", "A térkép és a robot visszaállítása a betöltött állapotra."),
)


class SzimulatorNezet(ttk.LabelFrame):
    """A világ kirajzolása; a kézi gombok a `kezi_parancs` függvényt hívják."""

    def __init__(self, master: tk.Misc, kezi_parancs: Callable[[str], None]) -> None:
        super().__init__(master, text="Szimulátor")
        self.vaszon = tk.Canvas(self, background="#eceff1", highlightthickness=0)
        self.vaszon.pack(padx=6, pady=6)
        self._informacios_sor()
        self._kezi_vezerles(kezi_parancs)
        self._jelmagyarazat()

    def _informacios_sor(self) -> None:
        sor = ttk.Frame(self)
        sor.pack(fill="x", padx=6)
        self.arany_cimke = ttk.Label(sor, text="Arany: 0", font=("Segoe UI", 11, "bold"))
        self.arany_cimke.pack(side="left")
        self.szenzor_cimke = tk.Label(sor, text="", font=("Segoe UI", 10), padx=6)
        self.szenzor_cimke.pack(side="right")
        Tooltip(self.szenzor_cimke, "Szenzor: ezt látná most az isThere a robot előtti "
                "mezőn (a térkép széle falnak számít). Nem teszi felfedezetté a mezőt.")

    def _kezi_vezerles(self, kezi_parancs: Callable[[str], None]) -> None:
        keret = ttk.LabelFrame(self, text="Kézi vezérlés (megszakítja a futást, nem naplóz)")
        keret.pack(fill="x", padx=6, pady=6)
        for felirat, parancs, sugo in KEZI_PARANCSOK:
            gomb = ttk.Button(keret, text=felirat, command=lambda p=parancs: kezi_parancs(p))
            gomb.pack(side="left", padx=2, pady=4)
            Tooltip(gomb, sugo)

    def _jelmagyarazat(self) -> None:
        keret = ttk.Frame(self)
        keret.pack(fill="x", padx=6, pady=(0, 6))
        elemek = (
            (SZIN_URES_FELFEDEZETT, "felfedezett"), (SZIN_URES_ISMERETLEN, "feltérképezetlen"),
            (SZIN_FAL_FELFEDEZETT, "fal"), (SZIN_ARANY_FELFEDEZETT, "arany"),
        )
        for szin, felirat in elemek:
            tk.Label(keret, background=szin, width=2, relief="solid", borderwidth=1).pack(side="left")
            ttk.Label(keret, text=f" {felirat}   ").pack(side="left")
        tk.Label(keret, text="┅┅", foreground=SZIN_SZENZOR, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(keret, text=" szenzor mezője").pack(side="left")

    # ---------- Kirajzolás ----------

    def rajzol(self, vilag: Vilag) -> None:
        """A teljes világ újrarajzolása."""
        terkep = vilag.terkep
        self.vaszon.configure(width=terkep.oszlopok * CELLA_PX + 2 * MARGO_PX,
                              height=terkep.sorok * CELLA_PX + 2 * MARGO_PX)
        self.vaszon.delete("all")
        for sor in range(terkep.sorok):
            for oszlop in range(terkep.oszlopok):
                felfedezett = (sor, oszlop) in vilag.felfedezett
                self._mezo_rajzol(sor, oszlop, terkep.mezo(sor, oszlop), felfedezett)
        self._szenzor_keret(vilag)
        self._robot_rajzol(vilag)
        self.arany_cimke.configure(text=f"Kibányászott arany: {vilag.arany_db}")
        self._szenzor_frissit(vilag)

    def _cella_sarkai(self, sor: int, oszlop: int) -> tuple[int, int, int, int]:
        x0 = MARGO_PX + oszlop * CELLA_PX
        y0 = MARGO_PX + sor * CELLA_PX
        return x0, y0, x0 + CELLA_PX, y0 + CELLA_PX

    def _mezo_rajzol(self, sor: int, oszlop: int, mezo: Mezo, felfedezett: bool) -> None:
        x0, y0, x1, y1 = self._cella_sarkai(sor, oszlop)
        hatter = SZIN_URES_FELFEDEZETT if felfedezett else SZIN_URES_ISMERETLEN
        if mezo is Mezo.FAL:
            hatter = SZIN_FAL_FELFEDEZETT if felfedezett else SZIN_FAL_ISMERETLEN
        self.vaszon.create_rectangle(x0, y0, x1, y1, fill=hatter, outline=SZIN_RACS)
        if mezo is Mezo.ARANY:
            szin = SZIN_ARANY_FELFEDEZETT if felfedezett else SZIN_ARANY_ISMERETLEN
            sugar = CELLA_PX * ARANY_MERET
            kx, ky = (x0 + x1) / 2, (y0 + y1) / 2
            self.vaszon.create_oval(kx - sugar, ky - sugar, kx + sugar, ky + sugar,
                                    fill=szin, outline="#8d6e00")

    def _szenzor_keret(self, vilag: Vilag) -> None:
        sor, oszlop = vilag.elotte()
        if vilag.terkep.bent_van(sor, oszlop):
            x0, y0, x1, y1 = self._cella_sarkai(sor, oszlop)
            self.vaszon.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, outline=SZIN_SZENZOR,
                                         width=2, dash=(4, 2))

    def _robot_rajzol(self, vilag: Vilag) -> None:
        robot = vilag.robot
        x0, y0, x1, y1 = self._cella_sarkai(robot.sor, robot.oszlop)
        kx, ky = (x0 + x1) / 2, (y0 + y1) / 2
        meret = CELLA_PX * ROBOT_MERET
        dx, dy = robot.irany.doszlop, robot.irany.dsor
        merx, mery = -dy, dx  # merőleges irány
        csucs = (kx + dx * meret, ky + dy * meret)
        bal = (kx - dx * meret + merx * meret, ky - dy * meret + mery * meret)
        jobb = (kx - dx * meret - merx * meret, ky - dy * meret - mery * meret)
        self.vaszon.create_polygon(*csucs, *bal, *jobb, fill=SZIN_ROBOT, outline="#7f0000", width=2)

    def _szenzor_frissit(self, vilag: Vilag) -> None:
        sor, oszlop = vilag.elotte()
        mezo = vilag.szenzor()
        szoveg = SZENZOR_SZOVEG[mezo]
        if not vilag.terkep.bent_van(sor, oszlop):
            szoveg = "fal (1) – térkép széle"
        hatter = {Mezo.URES: "#e8f5e9", Mezo.FAL: "#d7ccc8", Mezo.ARANY: "#fff3c4"}[mezo]
        self.szenzor_cimke.configure(text=f"Szenzor (előtte): {szoveg}", background=hatter)
