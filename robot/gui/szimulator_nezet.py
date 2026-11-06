"""A szimulátor nézet: térkép, animált robot, nyomvonal, felfedezett mezők, szenzor,
aranyszámláló, statisztika, kézi vezérlés és térképszerkesztő mód.

Az animáció csak a megjelenítést érinti: a világ (Vilag) állapota már a végleges,
a nézet a korábban kirajzolt állapotból „úsztatja át” a robotot az új helyére.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from gui import stilus
from gui.tooltip import Tooltip
from terkep import Irany, Mezo, Vilag

MAX_CELLA_PX = 64
MIN_CELLA_PX = 14
FELIRAT_MARGO = 18
KEPKOCKA_MS = 16
FELIRAT_MIN_CELLA = 22

SZIN_URES = "#fff8e6"
SZIN_URES_RACS = "#eadcb8"
SZIN_ISMERETLEN = "#b8c2cf"
SZIN_ISMERETLEN_RACS = "#a3aebc"
SZIN_FAL = "#7c4a21"
SZIN_FAL_MINTA = "#9a5f2c"
SZIN_FAL_FENY = "#b07440"
SZIN_FAL_ISMERETLEN = "#5b5f66"
SZIN_FAL_ISMERETLEN_MINTA = "#6d7178"
SZIN_ARANY = "#facc15"
SZIN_ARANY_FENY = "#fef9c3"
SZIN_ARANY_ISMERETLEN = "#d6c27c"
SZIN_ARANY_SZEGELY = "#a16207"
SZIN_KIBANYASZOTT = "#d97706"
SZIN_ROBOT = "#dc2626"
SZIN_ROBOT_SOTET = "#7f1d1d"
SZIN_ROBOT_BELSO = "#f87171"
SZIN_LAMPA = "#fde047"
SZIN_NYOM = "#60a5fa"
SZIN_SZERKESZTO = "#7c3aed"

SZENZOR_SZOVEG = {Mezo.URES: "üres kamra (0)", Mezo.FAL: "fal (1)", Mezo.ARANY: "aranyrög (2)"}
SZENZOR_HATTER = {Mezo.URES: "#dcfce7", Mezo.FAL: "#fde2c8", Mezo.ARANY: "#fef08a"}
SZENZOR_KERET = {Mezo.URES: "#16a34a", Mezo.FAL: "#dc2626", Mezo.ARANY: "#ca8a04"}
IRANY_NYIL = {Irany.KELET: "→", Irany.ESZAK: "↑", Irany.NYUGAT: "←", Irany.DEL: "↓"}

KEZI_PARANCSOK = (
    ("← Balra", "balra", "Fordulás balra 90°-kal (turn by 1).  Billentyű: ←"),
    ("↑ Lépés", "lepes", "Egy mező előre (step forward 1). Falnál hiba nélkül megáll.  Billentyű: ↑"),
    ("→ Jobbra", "jobbra", "Fordulás jobbra 90°-kal (turn by 3).  Billentyű: →"),
    ("Bányászás", "banyasz", "Az arany kibányászása a robot mezőjén (mine here).  Billentyű: szóköz"),
    ("↺ Alaphelyzet", "alaphelyzet", "A térkép és a robot visszaállítása a betöltött állapotra."),
)
ESZKOZOK = {"Üres": "ures", "Fal": "fal", "Arany": "arany", "Robot": "robot"}


class SzimulatorNezet(ctk.CTkFrame):
    """A világ kirajzolása és animálása; a gombok a kapott függvényeket hívják."""

    def __init__(self, master, kezi_parancs: Callable[[str], None],
                 terkep_kattintas: Callable[[int, int, str], None],
                 szerkeszto_mod_valt: Callable[[bool], None],
                 meret_valt: Callable[[int, int], None]) -> None:
        super().__init__(master, fg_color=stilus.PANEL, corner_radius=10,
                         border_width=1, border_color=stilus.SZEGELY)
        self._vilag: Vilag | None = None
        self._kezi_parancs = kezi_parancs
        self._terkep_kattintas = terkep_kattintas
        self._szerkeszto_mod_valt = szerkeszto_mod_valt
        self._meret_valt = meret_valt
        self.szerkeszto_mod = False
        self._cella = 32
        self._x0 = self._y0 = 0
        self._anim_id: str | None = None
        self._utolso_festett: tuple[int, int] | None = None
        self._megj_poz = (0.0, 0.0)
        self._megj_szog = 0.0
        self._megj_felfedezett: set[tuple[int, int]] = set()
        self._fejlec()
        self._informacios_sor()
        self._szerkeszto_sav()
        self.vaszon = tk.Canvas(self, background=stilus.PANEL, highlightthickness=0, height=260)
        self.vaszon.pack(fill="both", expand=True, padx=10, pady=4)
        self._vaszon_kotesek()
        self._jelmagyarazat()
        self._kezi_vezerles()

    # ---------- Felépítés ----------

    def _fejlec(self) -> None:
        sor = ctk.CTkFrame(self, fg_color="transparent")
        sor.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(sor, text="Robot szimulátor", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(side="left")
        self.szerkeszto_gomb = ctk.CTkButton(sor, text="✎ Térkép szerkesztése", width=10, height=28,
                                             font=stilus.betu(11), fg_color="transparent", border_width=1,
                                             border_color=stilus.SZEGELY, text_color=stilus.SZOVEG,
                                             hover_color="#ede9fe", command=self._szerkeszto_kapcsol)
        self.szerkeszto_gomb.pack(side="right")
        Tooltip(self.szerkeszto_gomb, "Térképszerkesztő mód: falak, aranyrögök és a robot elhelyezése, "
                "a térkép átméretezése (1–15). A Mentés a térképet is elmenti.")

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
        sor.pack(fill="x", padx=8, pady=(6, 0))
        self.arany_cimke = self._kartya(sor, "Kibányászott arany")
        self.szenzor_cimke = self._kartya(sor, "Szenzor (a robot előtt)")
        self.irany_cimke = self._kartya(sor, "Helyzet / irány")
        self.stat_cimke = self._kartya(sor, "Megtett út")
        Tooltip(self.szenzor_cimke, "Ezt adná most vissza az isThere a robot előtti mezőre "
                "(a térkép széle falnak számít). A szenzor nem teszi felfedezetté a mezőt.")
        Tooltip(self.stat_cimke, "A robot megtett lépései és fordulásai (a futás / kézi vezérlés óta).")

    def _szerkeszto_sav(self) -> None:
        """Két sor: eszközválasztó + Kész, alatta az átméretezés és a tudnivalók."""
        self._szerk_sav = ctk.CTkFrame(self, fg_color="#f5f3ff", corner_radius=8,
                                       border_width=1, border_color="#c4b5fd")
        felso = ctk.CTkFrame(self._szerk_sav, fg_color="transparent")
        felso.pack(fill="x", padx=6, pady=(6, 2))
        ctk.CTkLabel(felso, text="Eszköz:", font=stilus.betu(11, True),
                     text_color=SZIN_SZERKESZTO).pack(side="left", padx=(2, 4))
        self.eszkoz = ctk.CTkSegmentedButton(felso, values=list(ESZKOZOK), font=stilus.betu(11),
                                             selected_color=SZIN_SZERKESZTO, selected_hover_color="#6d28d9")
        self.eszkoz.set("Fal")
        self.eszkoz.pack(side="left", padx=4)
        ctk.CTkButton(felso, text="✓ Kész", width=10, height=26, font=stilus.betu(11, True),
                      fg_color=SZIN_SZERKESZTO, hover_color="#6d28d9",
                      command=self._szerkeszto_kapcsol).pack(side="right", padx=2)
        also = ctk.CTkFrame(self._szerk_sav, fg_color="transparent")
        also.pack(fill="x", padx=6, pady=(0, 6))
        ctk.CTkLabel(also, text="Méret:", font=stilus.betu(11, True),
                     text_color=SZIN_SZERKESZTO).pack(side="left", padx=(2, 4))
        for felirat, dsor, doszlop in (("Sor −", -1, 0), ("Sor +", 1, 0), ("Oszlop −", 0, -1), ("Oszlop +", 0, 1)):
            ctk.CTkButton(also, text=felirat, width=10, height=24, font=stilus.betu(10),
                          fg_color="#ddd6fe", text_color="#4c1d95", hover_color="#c4b5fd",
                          command=lambda s=dsor, o=doszlop: self._meret_valt(s, o)).pack(side="left", padx=2)
        ctk.CTkLabel(also, text="kattints / húzz a térképen; Robot: áthelyezés, rajta kattintva fordul",
                     font=stilus.betu(10), text_color=stilus.HALVANY).pack(side="left", padx=8)

    def _vaszon_kotesek(self) -> None:
        v = self.vaszon
        v.bind("<Configure>", lambda _e: self._ujrarajzol())
        v.bind("<Button-1>", self._kattintas)
        v.bind("<B1-Motion>", self._festes)
        v.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_utolso_festett", None))
        v.bind("<Motion>", self._mutato)
        for billentyu, parancs in (("<Left>", "balra"), ("<Right>", "jobbra"), ("<Up>", "lepes"),
                                   ("<space>", "banyasz")):
            v.bind(billentyu, lambda _e, p=parancs: self._kezi_parancs(p))

    def _kezi_vezerles(self) -> None:
        keret = ctk.CTkFrame(self, fg_color="#f1f5f9", corner_radius=8)
        keret.pack(fill="x", padx=10, pady=(4, 10))
        cim = ctk.CTkLabel(keret, text="Kézi vezérlés  (megszakítja a futást, nem naplóz; "
                                       "a térképre kattintva: ← ↑ → és szóköz)",
                           font=stilus.betu(10), text_color=stilus.HALVANY)
        cim.pack(anchor="w", padx=8, pady=(4, 0))
        gombsor = ctk.CTkFrame(keret, fg_color="transparent")
        gombsor.pack(fill="x", padx=6, pady=(2, 6))
        for felirat, parancs, sugo in KEZI_PARANCSOK:
            szin = stilus.GOMB_SEMLEGES if parancs == "alaphelyzet" else ("#0f766e", "#115e59")
            if parancs == "banyasz":
                szin = ("#b45309", "#92400e")
            gomb = ctk.CTkButton(gombsor, text=felirat, width=40, height=32, font=stilus.betu(11, True),
                                 fg_color=szin[0], hover_color=szin[1],
                                 command=lambda p=parancs: self._kezi_parancs(p))
            gomb.pack(side="left", padx=2, fill="x", expand=True)
            Tooltip(gomb, sugo)

    def _jelmagyarazat(self) -> None:
        keret = ctk.CTkFrame(self, fg_color="transparent")
        keret.pack(fill="x", padx=12)
        elemek = ((SZIN_URES, "felfedezett"), (SZIN_ISMERETLEN, "feltérképezetlen"),
                  (SZIN_FAL, "fal"), (SZIN_ARANY, "arany"), (SZIN_ROBOT, "robot"), (SZIN_NYOM, "nyomvonal"))
        for szin, felirat in elemek:
            ctk.CTkFrame(keret, fg_color=szin, width=14, height=14, corner_radius=3,
                         border_width=1, border_color="#94a3b8").pack(side="left")
            cimke = ctk.CTkLabel(keret, text=f" {felirat}  ", font=stilus.betu(10),
                                 text_color=stilus.HALVANY)
            cimke.pack(side="left")
            if felirat == "felfedezett":
                self.felfedezett_cimke = cimke
        ctk.CTkFrame(keret, fg_color="transparent", width=14, height=14, corner_radius=3,
                     border_width=2, border_color=SZENZOR_KERET[Mezo.URES]).pack(side="left")
        ctk.CTkLabel(keret, text=" szenzor  ", font=stilus.betu(10),
                     text_color=stilus.HALVANY).pack(side="left")
        ctk.CTkFrame(keret, fg_color="transparent", width=14, height=14, corner_radius=7,
                     border_width=2, border_color=SZIN_KIBANYASZOTT).pack(side="left")
        ctk.CTkLabel(keret, text=" kibányászva", font=stilus.betu(10),
                     text_color=stilus.HALVANY).pack(side="left")

    # ---------- Térképszerkesztő mód ----------

    def _szerkeszto_kapcsol(self) -> None:
        self.szerkeszto_mod_beallit(not self.szerkeszto_mod)
        self._szerkeszto_mod_valt(self.szerkeszto_mod)

    def szerkeszto_mod_beallit(self, bekapcsolva: bool) -> None:
        self.szerkeszto_mod = bekapcsolva
        if bekapcsolva:
            self._szerk_sav.pack(fill="x", padx=10, pady=(6, 0), after=self.arany_cimke.master.master)
            self.szerkeszto_gomb.configure(fg_color="#ede9fe", border_color=SZIN_SZERKESZTO,
                                           text_color=SZIN_SZERKESZTO)
        else:
            self._szerk_sav.pack_forget()
            self.szerkeszto_gomb.configure(fg_color="transparent", border_color=stilus.SZEGELY,
                                           text_color=stilus.SZOVEG)
        self._ujrarajzol()

    def _cella_pont_alatt(self, x: int, y: int) -> tuple[int, int] | None:
        if self._vilag is None:
            return None
        sor = math.floor((y - self._y0) / self._cella)
        oszlop = math.floor((x - self._x0) / self._cella)
        if self._vilag.terkep.bent_van(sor, oszlop):
            return sor, oszlop
        return None

    def _kattintas(self, esemeny) -> None:
        self.vaszon.focus_set()
        if self.szerkeszto_mod:
            self._utolso_festett = None
            self._festes(esemeny)

    def _festes(self, esemeny) -> None:
        if not self.szerkeszto_mod:
            return
        cella = self._cella_pont_alatt(esemeny.x, esemeny.y)
        eszkoz = ESZKOZOK[self.eszkoz.get()]
        if cella is None or cella == self._utolso_festett:
            return
        if eszkoz == "robot" and self._utolso_festett is not None:
            return  # a robotot húzás közben nem pörgetjük
        self._utolso_festett = cella
        self._terkep_kattintas(cella[0], cella[1], eszkoz)

    def _mutato(self, esemeny) -> None:
        self.vaszon.delete("hover")
        if not self.szerkeszto_mod:
            self.vaszon.configure(cursor="")
            return
        self.vaszon.configure(cursor="crosshair")
        cella = self._cella_pont_alatt(esemeny.x, esemeny.y)
        if cella is not None:
            x0, y0, x1, y1 = self._sarkok(*cella)
            self.vaszon.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, outline=SZIN_SZERKESZTO,
                                         width=3, tags="hover")

    # ---------- Nyilvános rajzolás ----------

    def rajzol(self, vilag: Vilag) -> None:
        """Azonnali, teljes újrarajzolás (a futó animáció megszakad)."""
        self._anim_megszakit()
        self._vilag = vilag
        self._megjelenites_szinkron()
        self._ujrarajzol()

    def animal(self, vilag: Vilag, cellankent_ms: int, kesz: Callable[[], None] | None = None) -> None:
        """A korábban kirajzolt állapotból animálva jut el `vilag` állapotáig."""
        self._anim_megszakit()
        if vilag is not self._vilag or cellankent_ms <= 0 or not self.winfo_ismapped():
            self.rajzol(vilag)
            if kesz is not None:
                kesz()
            return
        utvonal = self._animacios_utvonal(vilag)
        fordulas = (vilag.robot.irany.szog - self._megj_szog) % 360
        fordulas = -90.0 if fordulas == 270 else fordulas
        if not utvonal and fordulas == 0:
            self.rajzol(vilag)
            if kesz is not None:
                kesz()
            return
        self._valtozott_cellak_rajzol(vilag, utvonal)
        self.vaszon.delete("szenzor")
        idotartam = max(1, (len(utvonal) + abs(fordulas) / 90) * cellankent_ms)
        allapot = {"kezdet": time.perf_counter(), "idotartam": idotartam / 1000, "utvonal": utvonal,
                   "honnan": self._megj_poz, "szog0": self._megj_szog, "fordulas": fordulas,
                   "kesz": kesz, "elert": 0}
        self._kepkocka(allapot)

    # ---------- Animáció ----------

    def _megjelenites_szinkron(self) -> None:
        vilag = self._vilag
        if vilag is None:
            return
        self._megj_poz = (float(vilag.robot.sor), float(vilag.robot.oszlop))
        self._megj_szog = float(vilag.robot.irany.szog)
        self._megj_felfedezett = set(vilag.felfedezett)

    def _animacios_utvonal(self, vilag: Vilag) -> list[tuple[int, int]]:
        cel = (vilag.robot.sor, vilag.robot.oszlop)
        if cel == (round(self._megj_poz[0]), round(self._megj_poz[1])):
            return []
        if vilag.utvonal and vilag.utvonal[-1] == cel:
            return list(vilag.utvonal)
        return [cel]

    def _valtozott_cellak_rajzol(self, vilag: Vilag, utvonal: list[tuple[int, int]]) -> None:
        """A nem az útvonalon lévő változások (bányászás, isThere) azonnal látszanak."""
        for cella in vilag.felfedezett - self._megj_felfedezett - set(utvonal):
            self._megj_felfedezett.add(cella)
            self._cella_rajzol(*cella)
        sor, oszlop = round(self._megj_poz[0]), round(self._megj_poz[1])
        if vilag.terkep.bent_van(sor, oszlop):
            self._cella_rajzol(sor, oszlop)
        self._retegek_rendez()

    def _kepkocka(self, allapot: dict) -> None:
        eltelt = (time.perf_counter() - allapot["kezdet"]) / allapot["idotartam"]
        t = min(1.0, eltelt)
        utvonal = allapot["utvonal"]
        fordulasi_resz = abs(allapot["fordulas"]) / 90
        osszes = fordulasi_resz + len(utvonal)
        haladas = t * osszes
        szog = allapot["szog0"] + allapot["fordulas"] * min(1.0, haladas / fordulasi_resz if fordulasi_resz else 1)
        pozicio = allapot["honnan"]
        if utvonal:
            pozicio = self._ut_pont(allapot, max(0.0, haladas - fordulasi_resz))
        self._robot_rajzol(pozicio[0], pozicio[1], szog)
        if t >= 1.0:
            self._anim_id = None
            self.rajzol(self._vilag)
            if allapot["kesz"] is not None:
                allapot["kesz"]()
            return
        self._anim_id = self.after(KEPKOCKA_MS, lambda: self._kepkocka(allapot))

    def _ut_pont(self, allapot: dict, haladas: float) -> tuple[float, float]:
        """Az útvonal mentén `haladas` cellányira lévő pont; az elért cellák felfedezetté válnak."""
        utvonal = allapot["utvonal"]
        pontok = [allapot["honnan"], *[(float(s), float(o)) for s, o in utvonal]]
        szakasz = min(int(haladas), len(utvonal) - 1)
        resz = min(1.0, haladas - szakasz)
        while allapot["elert"] < min(len(utvonal), int(haladas + 0.5)):
            cella = utvonal[allapot["elert"]]
            allapot["elert"] += 1
            self._megj_felfedezett.add(cella)
            self._cella_rajzol(*cella)
            self._retegek_rendez()
        (s0, o0), (s1, o1) = pontok[szakasz], pontok[szakasz + 1]
        return s0 + (s1 - s0) * resz, o0 + (o1 - o0) * resz

    def _anim_megszakit(self) -> None:
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None

    # ---------- Kirajzolás ----------

    def _cella_meret(self, terkep) -> int:
        szel = max(self.vaszon.winfo_width(), 100) - FELIRAT_MARGO - 4
        mag = max(self.vaszon.winfo_height(), 100) - FELIRAT_MARGO - 4
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
        self._x0 = (max(v.winfo_width(), 100) - cella * terkep.oszlopok + FELIRAT_MARGO) // 2
        self._y0 = (max(v.winfo_height(), 100) - cella * terkep.sorok + FELIRAT_MARGO) // 2
        for sor in range(terkep.sorok):
            for oszlop in range(terkep.oszlopok):
                self._cella_rajzol(sor, oszlop)
        self._koordinatak(terkep)
        x1 = self._x0 + cella * terkep.oszlopok
        y1 = self._y0 + cella * terkep.sorok
        keret_szin = SZIN_SZERKESZTO if self.szerkeszto_mod else "#1f2937"
        v.create_rectangle(self._x0, self._y0, x1, y1, outline=keret_szin, width=3 if self.szerkeszto_mod else 2,
                           tags="keret")
        self._nyomvonal_rajzol(vilag)
        if not self.szerkeszto_mod:
            self._szenzor_rajzol(vilag)
        self._robot_rajzol(self._megj_poz[0], self._megj_poz[1], self._megj_szog)
        self._feliratok(vilag)

    def _koordinatak(self, terkep) -> None:
        if self._cella < FELIRAT_MIN_CELLA:
            return
        betu = stilus.tk_betu(8)
        for oszlop in range(terkep.oszlopok):
            x = self._x0 + (oszlop + 0.5) * self._cella
            self.vaszon.create_text(x, self._y0 - 9, text=str(oszlop + 1), fill="#94a3b8", font=betu)
        for sor in range(terkep.sorok):
            y = self._y0 + (sor + 0.5) * self._cella
            self.vaszon.create_text(self._x0 - 9, y, text=str(sor + 1), fill="#94a3b8", font=betu)

    def _sarkok(self, sor: int, oszlop: int) -> tuple[int, int, int, int]:
        x0 = self._x0 + oszlop * self._cella
        y0 = self._y0 + sor * self._cella
        return x0, y0, x0 + self._cella, y0 + self._cella

    def _retegek_rendez(self) -> None:
        for reteg in ("keret", "nyom", "szenzor", "robot", "hover"):
            if self.vaszon.find_withtag(reteg):
                self.vaszon.tag_raise(reteg)

    def _cella_rajzol(self, sor: int, oszlop: int) -> None:
        """Egy mező újrarajzolása (felfedezett: élénk, feltérképezetlen: szürke)."""
        vilag = self._vilag
        cimke = f"c{sor}_{oszlop}"
        self.vaszon.delete(cimke)
        mezo = vilag.terkep.mezo(sor, oszlop)
        felfedezett = (sor, oszlop) in self._megj_felfedezett or self.szerkeszto_mod
        if mezo is Mezo.FAL:
            self._fal_rajzol(sor, oszlop, felfedezett, cimke)
            return
        x0, y0, x1, y1 = self._sarkok(sor, oszlop)
        kitoltes, racs = (SZIN_URES, SZIN_URES_RACS) if felfedezett else (SZIN_ISMERETLEN, SZIN_ISMERETLEN_RACS)
        self.vaszon.create_rectangle(x0, y0, x1, y1, fill=kitoltes, outline=racs, tags=cimke)
        if mezo is Mezo.ARANY:
            self._arany_rajzol(x0, y0, felfedezett, cimke)
        elif (sor, oszlop) in vilag.kibanyaszott:
            r = self._cella * 0.17
            kx, ky = (x0 + x1) / 2, (y0 + y1) / 2
            self.vaszon.create_oval(kx - r, ky - r, kx + r, ky + r, outline=SZIN_KIBANYASZOTT,
                                    width=2, dash=(3, 2), tags=cimke)

    def _fal_rajzol(self, sor: int, oszlop: int, felfedezett: bool, cimke: str) -> None:
        """Téglamintás fal; a feltérképezetlen fal szürke."""
        v = self.vaszon
        x0, y0, x1, y1 = self._sarkok(sor, oszlop)
        alap, minta = (SZIN_FAL, SZIN_FAL_MINTA) if felfedezett else (SZIN_FAL_ISMERETLEN, SZIN_FAL_ISMERETLEN_MINTA)
        v.create_rectangle(x0, y0, x1, y1, fill=alap, outline=minta, tags=cimke)
        harmad = (y1 - y0) / 3
        for i in (1, 2):
            v.create_line(x0, y0 + i * harmad, x1, y0 + i * harmad, fill=minta, tags=cimke)
        kozep = (x0 + x1) / 2
        v.create_line(kozep, y0, kozep, y0 + harmad, fill=minta, tags=cimke)
        v.create_line(x0 + (x1 - x0) / 4, y0 + harmad, x0 + (x1 - x0) / 4, y0 + 2 * harmad, fill=minta, tags=cimke)
        v.create_line(x1 - (x1 - x0) / 4, y0 + harmad, x1 - (x1 - x0) / 4, y0 + 2 * harmad, fill=minta, tags=cimke)
        v.create_line(kozep, y0 + 2 * harmad, kozep, y1, fill=minta, tags=cimke)
        if felfedezett:
            v.create_line(x0 + 1, y0 + 1, x1 - 1, y0 + 1, fill=SZIN_FAL_FENY, tags=cimke)

    def _arany_rajzol(self, x0: float, y0: float, felfedezett: bool, cimke: str) -> None:
        """Szabálytalan aranyrög csillanással."""
        c = self._cella
        kx, ky = x0 + c / 2, y0 + c / 2
        r = c * 0.27
        alak = ((-1.0, 0.1), (-0.6, -0.65), (0.1, -0.85), (0.8, -0.45), (1.0, 0.25),
                (0.45, 0.8), (-0.45, 0.75))
        pontok = [ertek for dx, dy in alak for ertek in (kx + dx * r, ky + dy * r)]
        kitoltes = SZIN_ARANY if felfedezett else SZIN_ARANY_ISMERETLEN
        self.vaszon.create_polygon(pontok, fill=kitoltes, outline=SZIN_ARANY_SZEGELY,
                                   width=2 if felfedezett else 1, tags=cimke)
        if felfedezett:
            self.vaszon.create_oval(kx - r * 0.55, ky - r * 0.55, kx - r * 0.1, ky - r * 0.2,
                                    fill=SZIN_ARANY_FENY, outline="", tags=cimke)

    def _kozeppont(self, sor: float, oszlop: float) -> tuple[float, float]:
        return self._x0 + (oszlop + 0.5) * self._cella, self._y0 + (sor + 0.5) * self._cella

    def _nyomvonal_rajzol(self, vilag: Vilag) -> None:
        if self.szerkeszto_mod or len(vilag.nyomvonal) < 2:
            return
        pontok = [ertek for sor, oszlop in vilag.nyomvonal for ertek in self._kozeppont(sor, oszlop)]
        self.vaszon.create_line(*pontok, fill=SZIN_NYOM, width=max(2, self._cella * 0.08),
                                capstyle="round", joinstyle="round", tags="nyom")

    def _szenzor_rajzol(self, vilag: Vilag) -> None:
        """A szenzor mezője a tartalma szerinti színnel; a térkép széle piros vonal."""
        sor, oszlop = vilag.elotte()
        mezo = vilag.szenzor()
        szin = SZENZOR_KERET[mezo]
        if vilag.terkep.bent_van(sor, oszlop):
            x0, y0, x1, y1 = self._sarkok(sor, oszlop)
            self.vaszon.create_rectangle(x0 + 3, y0 + 3, x1 - 3, y1 - 3, outline=szin,
                                         width=3, dash=(6, 3), tags="szenzor")
            return
        rs, ro = vilag.robot.sor, vilag.robot.oszlop
        x0, y0, x1, y1 = self._sarkok(rs, ro)
        irany = vilag.robot.irany
        szelek = {Irany.KELET: (x1, y0, x1, y1), Irany.NYUGAT: (x0, y0, x0, y1),
                  Irany.ESZAK: (x0, y0, x1, y0), Irany.DEL: (x0, y1, x1, y1)}
        self.vaszon.create_line(*szelek[irany], fill=szin, width=6, capstyle="round", tags="szenzor")

    def _robot_rajzol(self, sor: float, oszlop: float, szog: float) -> None:
        """Kerek robottest, sárga „lámpa” mutatja az irányt; tetszőleges szögben rajzolható."""
        v = self.vaszon
        v.delete("robot")
        kx, ky = self._kozeppont(sor, oszlop)
        r = self._cella * 0.36
        rad = math.radians(szog)
        dx, dy = math.cos(rad), -math.sin(rad)
        mx, my = -dy, dx
        v.create_oval(kx - r, ky - r, kx + r, ky + r, fill=SZIN_ROBOT, outline=SZIN_ROBOT_SOTET,
                      width=2, tags="robot")
        b = r * 0.55
        v.create_oval(kx - b, ky - b, kx + b, ky + b, fill=SZIN_ROBOT_BELSO, outline="", tags="robot")
        csucs = (kx + dx * r * 1.15, ky + dy * r * 1.15)
        bal = (kx + dx * r * 0.15 + mx * r * 0.6, ky + dy * r * 0.15 + my * r * 0.6)
        jobb = (kx + dx * r * 0.15 - mx * r * 0.6, ky + dy * r * 0.15 - my * r * 0.6)
        v.create_polygon(*csucs, *bal, *jobb, fill=SZIN_LAMPA, outline=SZIN_ROBOT_SOTET, width=2, tags="robot")

    def _feliratok(self, vilag: Vilag) -> None:
        self.arany_cimke.configure(text=f"{vilag.arany_db} / {vilag.osszes_arany()} db")
        sor, oszlop = vilag.elotte()
        mezo = vilag.szenzor()
        szoveg = SZENZOR_SZOVEG[mezo]
        if not vilag.terkep.bent_van(sor, oszlop):
            szoveg = "fal (1) – térkép széle"
        self.szenzor_cimke.configure(text=szoveg)
        self.szenzor_cimke.master.configure(fg_color=SZENZOR_HATTER[mezo])
        robot = vilag.robot
        self.irany_cimke.configure(text=f"{robot.sor + 1}. sor, {robot.oszlop + 1}. oszlop, "
                                        f"{robot.irany.nev} {IRANY_NYIL[robot.irany]}")
        terulet = vilag.terkep.sorok * vilag.terkep.oszlopok
        self.stat_cimke.configure(text=f"{vilag.lepesszam} lépés · {vilag.fordulasszam} fordulás")
        self.felfedezett_cimke.configure(text=f" felfedezett ({len(vilag.felfedezett)}/{terulet})  ")
