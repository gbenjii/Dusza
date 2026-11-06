"""A szimulátor nézet: térkép, robot, felfedezett mezők, szenzor, aranyszámláló és kézi vezérlés."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from gui import stilus
from gui.tooltip import Tooltip
from terkep import Irany, Mezo, Vilag

MAX_CELLA_PX = 44
MIN_CELLA_PX = 16

SZIN_URES = "#fffbeb"
SZIN_ISMERETLEN = "#a3adba"
SZIN_ISMERETLEN_RACS = "#8b95a3"
SZIN_FAL = "#78350f"
SZIN_FAL_MINTA = "#92400e"
SZIN_FAL_ISMERETLEN = "#57534e"
SZIN_ARANY = "#facc15"
SZIN_ARANY_ISMERETLEN = "#d9c27a"
SZIN_ARANY_SZEGELY = "#a16207"
SZIN_ROBOT = "#dc2626"
SZIN_SZENZOR = "#2563eb"
SZIN_RACS = "#e7dcc0"

SZENZOR_SZOVEG = {Mezo.URES: "üres kamra (0)", Mezo.FAL: "fal (1)", Mezo.ARANY: "aranyrög (2)"}
SZENZOR_SZIN = {Mezo.URES: "#dcfce7", Mezo.FAL: "#fde68a", Mezo.ARANY: "#fef08a"}
IRANY_NEV = {Irany.KELET: "kelet →", Irany.ESZAK: "észak ↑", Irany.NYUGAT: "nyugat ←", Irany.DEL: "dél ↓"}

KEZI_PARANCSOK = (
    ("← Balra", "balra", "Fordulás balra 90°-kal (turn by 1).  Billentyű: ←"),
    ("↑ Lépés", "lepes", "Egy mező előre (step forward 1). Falnál nem lép.  Billentyű: ↑"),
    ("→ Jobbra", "jobbra", "Fordulás jobbra 90°-kal (turn by 3).  Billentyű: →"),
    ("Bányászás", "banyasz", "Az arany kibányászása a robot mezőjén (mine here).  Billentyű: szóköz"),
    ("↺ Alaphelyzet", "alaphelyzet", "A térkép és a robot visszaállítása a betöltött állapotra."),
)


class SzimulatorNezet(ctk.CTkFrame):
    """A világ kirajzolása; a kézi gombok a `kezi_parancs` függvényt hívják."""

    def __init__(self, master, kezi_parancs: Callable[[str], None]) -> None:
        super().__init__(master, fg_color=stilus.PANEL, corner_radius=10,
                         border_width=1, border_color=stilus.SZEGELY)
        self._vilag: Vilag | None = None
        self._kezi_parancs = kezi_parancs
        ctk.CTkLabel(self, text="Robot szimulátor", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(anchor="w", padx=12, pady=(8, 0))
        self._informacios_sor()
        self.vaszon = tk.Canvas(self, background=stilus.PANEL, highlightthickness=0, height=260)
        self.vaszon.pack(fill="both", expand=True, padx=10, pady=4)
        self.vaszon.bind("<Configure>", lambda _e: self._ujrarajzol())
        self.vaszon.bind("<Button-1>", lambda _e: self.vaszon.focus_set())
        for billentyu, parancs in (("<Left>", "balra"), ("<Right>", "jobbra"), ("<Up>", "lepes"),
                                   ("<space>", "banyasz")):
            self.vaszon.bind(billentyu, lambda _e, p=parancs: self._kezi_parancs(p))
        self._jelmagyarazat()
        self._kezi_vezerles()

    def _kartya(self, szulo, cim: str) -> ctk.CTkLabel:
        keret = ctk.CTkFrame(szulo, fg_color="#f1f5f9", corner_radius=8)
        keret.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(keret, text=cim, font=stilus.betu(10), text_color=stilus.HALVANY,
                     height=16).pack(anchor="w", padx=8, pady=(4, 0))
        ertek = ctk.CTkLabel(keret, text="–", font=stilus.betu(13, True), text_color=stilus.SZOVEG,
                             height=22, anchor="w")
        ertek.pack(anchor="w", padx=8, pady=(0, 4))
        return ertek

    def _informacios_sor(self) -> None:
        sor = ctk.CTkFrame(self, fg_color="transparent")
        sor.pack(fill="x", padx=8, pady=(4, 0))
        self.arany_cimke = self._kartya(sor, "Kibányászott arany")
        self.szenzor_cimke = self._kartya(sor, "Szenzor (a robot előtt)")
        self.irany_cimke = self._kartya(sor, "Helyzet / irány")
        Tooltip(self.szenzor_cimke, "Ezt adná most vissza az isThere a robot előtti mezőre "
                "(a térkép széle falnak számít). A szenzor nem teszi felfedezetté a mezőt.")

    def _kezi_vezerles(self) -> None:
        keret = ctk.CTkFrame(self, fg_color="#f1f5f9", corner_radius=8)
        keret.pack(fill="x", padx=10, pady=(4, 10))
        cim = ctk.CTkLabel(keret, text="Kézi vezérlés  (megszakítja a futást, nem naplóz)",
                           font=stilus.betu(10), text_color=stilus.HALVANY)
        cim.pack(anchor="w", padx=8, pady=(4, 0))
        Tooltip(cim, "A térképre kattintva a nyilakkal (←, ↑, →) és a szóközzel is irányítható.")
        gombsor = ctk.CTkFrame(keret, fg_color="transparent")
        gombsor.pack(fill="x", padx=6, pady=(2, 6))
        for felirat, parancs, sugo in KEZI_PARANCSOK:
            szin = stilus.GOMB_SEMLEGES if parancs == "alaphelyzet" else ("#0f766e", "#115e59")
            gomb = ctk.CTkButton(gombsor, text=felirat, width=40, height=30, font=stilus.betu(11, True),
                                 fg_color=szin[0], hover_color=szin[1],
                                 command=lambda p=parancs: self._kezi_parancs(p))
            gomb.pack(side="left", padx=2, fill="x", expand=True)
            Tooltip(gomb, sugo)

    def _jelmagyarazat(self) -> None:
        keret = ctk.CTkFrame(self, fg_color="transparent")
        keret.pack(fill="x", padx=12)
        elemek = ((SZIN_URES, "felfedezett"), (SZIN_ISMERETLEN, "feltérképezetlen"),
                  (SZIN_FAL, "fal"), (SZIN_ARANY, "arany"), (SZIN_ROBOT, "robot"))
        for szin, felirat in elemek:
            ctk.CTkFrame(keret, fg_color=szin, width=14, height=14, corner_radius=3,
                         border_width=1, border_color="#94a3b8").pack(side="left")
            ctk.CTkLabel(keret, text=f" {felirat}   ", font=stilus.betu(10),
                         text_color=stilus.HALVANY).pack(side="left")
        ctk.CTkFrame(keret, fg_color="transparent", width=14, height=14, corner_radius=3,
                     border_width=2, border_color=SZIN_SZENZOR).pack(side="left")
        ctk.CTkLabel(keret, text=" szenzor mezője", font=stilus.betu(10),
                     text_color=stilus.HALVANY).pack(side="left")

    # ---------- Kirajzolás ----------

    def rajzol(self, vilag: Vilag) -> None:
        self._vilag = vilag
        self._ujrarajzol()

    def _cella_meret(self, terkep) -> int:
        szel = max(self.vaszon.winfo_width(), 100)
        mag = max(self.vaszon.winfo_height(), 100)
        meret = min(szel // max(terkep.oszlopok, 1), mag // max(terkep.sorok, 1))
        return max(MIN_CELLA_PX, min(MAX_CELLA_PX, meret))

    def _ujrarajzol(self) -> None:
        vilag = self._vilag
        if vilag is None:
            return
        terkep = vilag.terkep
        v = self.vaszon
        v.delete("all")
        cella = self._cella_meret(terkep)
        self._cella = cella
        self._x0 = (max(v.winfo_width(), 100) - cella * terkep.oszlopok) // 2
        self._y0 = (max(v.winfo_height(), 100) - cella * terkep.sorok) // 2
        for sor in range(terkep.sorok):
            for oszlop in range(terkep.oszlopok):
                felfedezett = (sor, oszlop) in vilag.felfedezett
                self._mezo_rajzol(sor, oszlop, terkep.mezo(sor, oszlop), felfedezett)
        x1 = self._x0 + cella * terkep.oszlopok
        y1 = self._y0 + cella * terkep.sorok
        v.create_rectangle(self._x0, self._y0, x1, y1, outline="#1f2937", width=2)
        self._szenzor_keret(vilag)
        self._robot_rajzol(vilag)
        self._feliratok(vilag)

    def _sarkok(self, sor: int, oszlop: int) -> tuple[int, int, int, int]:
        x0 = self._x0 + oszlop * self._cella
        y0 = self._y0 + sor * self._cella
        return x0, y0, x0 + self._cella, y0 + self._cella

    def _mezo_rajzol(self, sor: int, oszlop: int, mezo: Mezo, felfedezett: bool) -> None:
        """A feltérképezetlen mezők szürkék és halványak, a felfedezettek élénkek."""
        v = self.vaszon
        x0, y0, x1, y1 = self._sarkok(sor, oszlop)
        if mezo is Mezo.FAL:
            kitoltes, minta = (SZIN_FAL, SZIN_FAL_MINTA) if felfedezett else (SZIN_FAL_ISMERETLEN, "#6b6560")
            v.create_rectangle(x0, y0, x1, y1, fill=kitoltes, outline=minta)
            v.create_line(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, fill=minta)
            v.create_line((x0 + x1) / 2, y0, (x0 + x1) / 2, (y0 + y1) / 2, fill=minta)
            return
        if felfedezett:
            v.create_rectangle(x0, y0, x1, y1, fill=SZIN_URES, outline=SZIN_RACS)
        else:
            v.create_rectangle(x0, y0, x1, y1, fill=SZIN_ISMERETLEN, outline=SZIN_ISMERETLEN_RACS)
        if mezo is Mezo.ARANY:
            r = self._cella * 0.24
            kx, ky = (x0 + x1) / 2, (y0 + y1) / 2
            pontok = (kx, ky - r * 1.2, kx + r, ky, kx, ky + r * 1.2, kx - r, ky)
            szin = SZIN_ARANY if felfedezett else SZIN_ARANY_ISMERETLEN
            v.create_polygon(pontok, fill=szin, outline=SZIN_ARANY_SZEGELY, width=2 if felfedezett else 1)

    def _szenzor_keret(self, vilag: Vilag) -> None:
        sor, oszlop = vilag.elotte()
        if vilag.terkep.bent_van(sor, oszlop):
            x0, y0, x1, y1 = self._sarkok(sor, oszlop)
            self.vaszon.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, outline=SZIN_SZENZOR,
                                         width=3, dash=(5, 3))

    def _robot_rajzol(self, vilag: Vilag) -> None:
        robot = vilag.robot
        x0, y0, x1, y1 = self._sarkok(robot.sor, robot.oszlop)
        kx, ky = (x0 + x1) / 2, (y0 + y1) / 2
        meret = self._cella * 0.36
        dx, dy = robot.irany.doszlop, robot.irany.dsor
        merx, mery = -dy, dx
        csucs = (kx + dx * meret, ky + dy * meret)
        bal = (kx - dx * meret + merx * meret, ky - dy * meret + mery * meret)
        jobb = (kx - dx * meret - merx * meret, ky - dy * meret - mery * meret)
        self.vaszon.create_polygon(*csucs, *bal, *jobb, fill=SZIN_ROBOT, outline="#7f1d1d", width=2)

    def _feliratok(self, vilag: Vilag) -> None:
        self.arany_cimke.configure(text=f"{vilag.arany_db} db")
        sor, oszlop = vilag.elotte()
        mezo = vilag.szenzor()
        szoveg = SZENZOR_SZOVEG[mezo]
        if not vilag.terkep.bent_van(sor, oszlop):
            szoveg = "fal (1) – térkép széle"
        self.szenzor_cimke.configure(text=szoveg)
        self.szenzor_cimke.master.configure(fg_color=SZENZOR_SZIN[mezo])
        robot = vilag.robot
        self.irany_cimke.configure(text=f"{robot.sor + 1}. sor, {robot.oszlop + 1}. oszlop, "
                                        f"{IRANY_NEV[robot.irany]}")
