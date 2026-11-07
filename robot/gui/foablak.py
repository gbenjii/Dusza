"""Az IDE főablaka (customtkinter): eszközsor, blokkszerkesztő, kódnézet, változók,
szimulátor, konzol, napló és állapotsor.

Itt kapcsolódik a felület a GUI-tól független logikához (beolvasó, futtató, világ, napló).
A futtatás egy generátoron lép végig (`Futtato.lepesek(elore_jelez=True)`):
a `SorElott` esemény mondja meg, melyik sor következik (töréspont, ▶ jel),
a `NaploSor` pedig a már végrehajtott sort (kiemelés, animáció, napló).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from enum import Enum
from tkinter import filedialog, messagebox

import customtkinter as ctk

from beolvaso import Bemenet, beolvas_fajl, beolvas_szoveg, bemenet_szoveg
from futtato import UTASITAS_LIMIT, Futtato, SorElott, Vegallapot
from gui import stilus
from gui.blokkszerkeszto import Blokkszerkeszto
from gui.folyo_keret import FolyoKeret
from gui.kodnezet import Kodnezet
from gui.szimulator_nezet import SzimulatorNezet
from gui.tooltip import Tooltip
from hibak import HIBA_LEIRASOK, LIMIT_LEIRAS, LIMIT_TULLEPES, FutasiHiba, HibaKod
from naplo import Naplo, NaploSor, ertek_szoveg
from nyelv.elemzo import elemez
from nyelv.kiiro import program_sorai, sorszamoz
from nyelv.szerkesztes import torzsek
from nyelv.utasitasok import Elagazas, Utasitas
from peldaprogramok import PELDAK, Pelda
from terkep import Mezo

ABLAK_CIM = "MineScript robotszimulátor – IDE"
ALAP_NAPLO = "naplo.txt"
ALAP_BEMENET = "5 5\n>....\n.....\n.....\n.....\n.....\n"
KESLELTETES_MIN_MS = 20
KESLELTETES_MAX_MS = 1200
KESLELTETES_ALAP_MS = 350
ELOZMENY_MAX = 200
NYOMKOVETES_CELLA_MS = 170
KEZI_CELLA_MS = 140
FUTAS_CELLA_MIN_MS = 30
FUTAS_CELLA_MAX_MS = 200

GYORS_SUGO = """GYORS KEZDÉS

1. Megnyitás (Ctrl+O): térkép + program betöltése (vagy indítás: robot.exe BE KI).
   Példák: kész térképek és programok egy kattintással.  Új: üres program.

2. A programot CSAK a bal oldali blokkszerkesztővel lehet írni:
   • Új blokk: húzd a palettáról a kívánt helyre – a kék vonal mutatja, hová kerül
     (piros vonal: oda nem tehető, pl. 3 szintnél mélyebb lenne).
     Kattintásra a kijelölt blokk mögé kerül (ha nincs kijelölés, a program végére).
   • Áthelyezés: fogd meg a blokkot (a feliratánál) és húzd máshová. Az if / while
     a teljes törzsével együtt mozog. Alt+↑ / Alt+↓: mozgatás egy hellyel.
   • Mezők: kattints a fehér mezőre és írd át (Enter: kész, Esc: mégse).
     A szám és true/false mezők mellett −/+ gomb van; szerkesztés közben ↑/↓ is léptet.
     Jobb klikk a mezőn: választás a meglévő változók, true/false közül.
   • A set narancs érték-blokkjának ▾ gombjával választható: érték, isThere,
     not, illetve + − * = <> < <= > >= and or. A műveleti jelre kattintva is cserélhető.
   • if ↔ if-else: az eszközsor gombjával vagy jobb klikkel.
   • Törlés: Delete. Visszavonás: Ctrl+Z, újra: Ctrl+Y.
   A középső szöveges nézet mindig a blokkokkal egyező kódot mutatja.

3. Futtatás – minden új futás visszaállítja a térképet és a robotot:
   ▶ Futtatás (F5): lassított, animált futás (a csúszkával állítható).
   ▷ Lépésenként (F10): nyomkövetés. A ▶ jel a KÖVETKEZŐ sort mutatja, minden
     F10 egy sort hajt végre; a sárga sor az épp végrehajtott, a változók táblája
     sárgával jelzi, ami változott.
   ▶▶ Végig (F8): azonnal lefut a végéig (vagy a következő töréspontig).
   Töréspont (●): kattints a sorszámra a szöveges nézetben vagy a blokkok mellett
     (F9: a kijelölt blokk sora). A futás a töréspontos sor ELŐTT megáll; innen
     F10 = lépés, F5 = animált folytatás, F8 = folytatás a végéig.
   ■ Leállítás (Esc).
   A naplófájl futás közben soronként íródik, bármikor megnyitható.

4. Kézi vezérlés: a gombokkal, vagy a térképre kattintva a nyilakkal / szóközzel.
   Megszakítja a futást, és nem naplóz. Falnál hiba nélkül megáll.

5. Térkép szerkesztése (a szimulátor fejlécében): fal / arany / üres / robot
   festése egérrel, átméretezés. A Mentés a térképet is menti.

Térkép: élénk mező = felfedezett (járt rajta vagy isThere nézte), szürke =
feltérképezetlen. A szaggatott keret a szenzor mezője (zöld: üres, piros: fal,
sárga: arany); a kék vonal a robot eddigi útja."""

NYELV_SUGO = """A MINESCRIPT NYELV RÖVIDEN

step forward n   – n mezőt lép előre (falnál megáll: E_BEDROCK_HIT)
turn by n        – n negyedfordulat BALRA
mine here        – arany kibányászása (ha nincs: E_NO_GOLD)
print x          – érték kiírása a konzolra
set v to KIF     – KIF: x | isThere x | x op y | not x
                   op: + - * = <> < <= > >= and or
if x … else …    – elágazás
while x …        – ciklus (legfeljebb 3 vezérlőblokk ágyazható egymásba)

Egy érték (simpleval): változónév, 0–100 közötti egész, true vagy false.
isThere 0/1/2: üres kamra / fal / arany van-e a robot előtt.
Típusok: egész és logikai; a változó típusa az első set-nél rögzül.
Az if és a while feltétele logikai változó vagy true/false kell legyen,
ezért pl. a „while i < 5” helyett:  set tovabb to i < 5,  while tovabb.
Legfeljebb 1000 sor hajtható végre egy futás alatt.

Tokenizálás: minden sor egy utasítás; a sor eleji szóközök a behúzás
(ez adja a blokkokat), a tokeneket pontosan egy szóköz választja el.

Hibakódok:
E_TYPE_MISMATCH      – a változó típusa már rögzült, más típus nem adható
E_UNINITIALIZED      – értékadás előtt olvasott változó
E_NON_BOOL_CONDITION – az if / while feltétele nem logikai
E_BAD_OPERAND        – rossz típusú operandus
E_BEDROCK_HIT        – falnak vagy a térkép szélének ütközés
E_NO_GOLD            – nincs arany a mezőn
E_BAD_ARG            – hibás API-paraméter (pl. isThere 3, turn by true)

Parancssor:
robot.exe BE KI       – IDE, BE betöltése, napló: KI
robot.exe -q BE KI    – csendes futtatás, napló: KI
robot.exe -m MAPPA    – minden input_NNN.txt → output_NNN.txt egy menetben"""

BILLENTYUK = """BILLENTYŰK

F5        animált futtatás (szünetnél: folytatás animálva)
F10       nyomkövetés: következő sor (animált futás közben: szünet)
F8        végig: azonnali futás a végéig / a következő töréspontig
F9        töréspont a kijelölt blokk során
Esc       leállítás
Ctrl+O    megnyitás        Ctrl+S   mentés        Ctrl+N   új program
Ctrl+Z    visszavonás      Ctrl+Y   újra
Delete    a kijelölt blokk törlése (tartalmával)
Alt+↑/↓   a kijelölt blokk mozgatása
↑ / ↓     előző / következő blokk kijelölése
F1        súgó

A térképre kattintva:  ← → fordulás,  ↑ lépés,  szóköz bányászás"""


class Mod(Enum):
    ALL = "áll"
    FUTAS = "futás"
    NYOMKOVETES = "nyomkövetés"


def blokk_sorszamai(utasitas: Utasitas) -> list[int]:
    """Egy blokk és a teljes tartalma forrássorainak sorszámai."""
    sorszamok = [utasitas.sorszam]
    if isinstance(utasitas, Elagazas) and utasitas.hamis_ag is not None:
        sorszamok.append(utasitas.else_sorszam)
    for torzs in torzsek(utasitas):
        for belso in torzs:
            sorszamok.extend(blokk_sorszamai(belso))
    return sorted(sorszamok)


def fajl_megnyitasa(utvonal: str) -> None:
    """A fájl megnyitása az operációs rendszer alapértelmezett programjával."""
    if sys.platform.startswith("win"):
        os.startfile(utvonal)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", utvonal])
    else:
        subprocess.Popen(["xdg-open", utvonal])


class Foablak(ctk.CTk):
    """Az alkalmazás főablaka."""

    def __init__(self, be_utvonal: str | None, ki_utvonal: str | None) -> None:
        stilus.ctk_alap()
        super().__init__(fg_color=stilus.HATTER)
        stilus.beallit(self)
        self.title(ABLAK_CIM)
        self.geometry("1600x940")
        self.minsize(1250, 760)
        self.naplo_utvonal = ki_utvonal or ALAP_NAPLO
        self.fajl_utvonal: str | None = None
        self.alap_vilag = beolvas_szoveg(ALAP_BEMENET).vilag
        self.vilag = self.alap_vilag.masolat()
        self.program: list[Utasitas] = []
        self.futtato: Futtato | None = None
        self.lepesek = None
        self.mod = Mod.ALL
        self.torespontok: set[int] = set()
        self._fuggo: SorElott | None = None
        self._idozito: str | None = None
        self._elozmeny: list[list[str]] = [[]]
        self._elozmeny_index = 0
        self._elozo_valtozok: dict[str, int | bool] = {}
        self._mentett_allapot: list[str] = self._allapot_kep()
        self._eszkoztar()
        self._allapotsor()
        self._fo_terulet()
        self._billentyuk()
        self.protocol("WM_DELETE_WINDOW", self._kilepes)
        if be_utvonal:
            self.betolt(be_utvonal)
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)
        if sys.platform.startswith("win"):
            self.after(0, lambda: self.state("zoomed"))
        if stilus.XFT_HIANYZIK:
            print(stilus.XFT_UZENET, file=sys.stderr)
            self._allapot(stilus.XFT_UZENET, stilus.SZIN_FUT)

    # ---------- Felépítés ----------

    def _gomb(self, szulo, szoveg: str, parancs, szin=None, sugo: str = "", szel: int = 0) -> ctk.CTkButton:
        szin = szin or stilus.GOMB_SEMLEGES
        gomb = ctk.CTkButton(szulo, text=szoveg, command=parancs, height=34, width=szel or 10,
                             font=stilus.betu(12, True), fg_color=szin[0], hover_color=szin[1],
                             corner_radius=8)
        if sugo:
            Tooltip(gomb, sugo)
        return gomb

    def _atlatszo_gomb(self, szulo, szoveg: str, parancs, sugo: str) -> ctk.CTkButton:
        gomb = ctk.CTkButton(szulo, text=szoveg, command=parancs, height=34, width=10,
                             font=stilus.betu(12), corner_radius=8, fg_color="transparent", border_width=1,
                             border_color=stilus.SZEGELY, text_color=stilus.SZOVEG, hover_color="#e2e8f0")
        Tooltip(gomb, sugo)
        return gomb

    def _eszkoztar(self) -> None:
        """Az eszközsor sortörő: keskeny ablakban a gombok új sorba kerülnek, nem vágódnak le."""
        sav = ctk.CTkFrame(self, fg_color=stilus.PANEL, corner_radius=0)
        sav.pack(side="top", fill="x")
        sor = FolyoKeret(sav, hatter=stilus.PANEL, vizszintes_koz=6, fuggoleges_koz=6)
        sor.pack(fill="x", padx=12, pady=10)
        cim = tk.Frame(sor, background=stilus.PANEL)
        logo = tk.Canvas(cim, width=30, height=30, background=stilus.PANEL, highlightthickness=0)
        logo.create_oval(3, 3, 27, 27, fill="#dc2626", outline="#7f1d1d", width=2)
        logo.create_polygon(26, 15, 15, 8, 15, 22, fill="#fde047", outline="#7f1d1d", width=2)
        logo.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(cim, text="MineScript IDE", font=stilus.betu(16, True),
                     text_color=stilus.SZOVEG).pack(side="left")
        sor.hozzaad(cim)
        for index, (szoveg, parancs, sugo) in enumerate((
                ("Új", self._uj_program, "Új, üres program (a térkép megmarad). Ctrl+N"),
                ("Megnyitás", self._megnyitas, "Bemeneti fájl (térkép + program) betöltése. Ctrl+O"),
                ("Mentés", self._mentes, "A térkép és a program mentése a bemeneti fájl formátumában. Ctrl+S"),
                ("Példák ▾", self._peldak_menu, "Beépített példák: térkép + program egy kattintással."),
                ("Napló helye", self._naplo_hely, "Hová kerüljön a futás naplója."))):
            gomb = self._atlatszo_gomb(sor, szoveg, parancs, sugo)
            sor.hozzaad(gomb, plusz_koz=10 if index == 0 else 0)
            if szoveg.startswith("Példák"):
                self._peldak_gomb = gomb
        sor.hozzaad(ctk.CTkFrame(sor, width=2, height=30, fg_color=stilus.SZEGELY), plusz_koz=4)
        self.futtat_gomb = self._gomb(sor, "▶  Futtatás (F5)", self.futtatas, stilus.GOMB_FUTTAT,
                                      "Lassított, animált futtatás az elejétől (térkép és robot visszaáll). "
                                      "Töréspontnál megállva: animált folytatás.", szel=150)
        self.lepes_gomb = self._gomb(sor, "▷  Lépésenként (F10)", self.nyomkovetes, stilus.GOMB_LEPES,
                                     "Nyomkövetés: a ▶ jel a következő sort mutatja, minden kattintás egy "
                                     "sort hajt végre. Animált futás közben szünetet tart.", szel=180)
        self.vegig_gomb = self._gomb(sor, "▶▶  Végig (F8)", self.vegig, ("#7c3aed", "#6d28d9"),
                                     "Azonnali futás a végéig vagy a következő töréspontig "
                                     "(nyomkövetés közben: folytatás).")
        self.leallit_gomb = self._gomb(sor, "■  Leállítás (Esc)", self.leallitas, stilus.GOMB_ALLJ,
                                       "Az aktuális futás leállítása.")
        for index, gomb in enumerate((self.futtat_gomb, self.lepes_gomb, self.vegig_gomb, self.leallit_gomb)):
            sor.hozzaad(gomb, plusz_koz=4 if index == 0 else 0)
        sebesseg = ctk.CTkFrame(sor, fg_color="transparent")
        ctk.CTkLabel(sebesseg, text="lassú", font=stilus.betu(11),
                     text_color=stilus.HALVANY).pack(side="left")
        self.sebesseg = ctk.CTkSlider(sebesseg, from_=KESLELTETES_MIN_MS, to=KESLELTETES_MAX_MS, width=110)
        self.sebesseg.set(KESLELTETES_MAX_MS + KESLELTETES_MIN_MS - KESLELTETES_ALAP_MS)
        self.sebesseg.pack(side="left", padx=4)
        ctk.CTkLabel(sebesseg, text="gyors", font=stilus.betu(11),
                     text_color=stilus.HALVANY).pack(side="left")
        Tooltip(self.sebesseg, "Az animált futtatás sebessége.")
        sor.hozzaad(sebesseg, plusz_koz=10)
        sugo = self._atlatszo_gomb(sor, "Súgó ▾", self._sugo_menu,
                                   "Súgó (F1), a MineScript nyelv és a billentyűparancsok.")
        self._sugo_gomb = sugo
        sor.hozzaad(sugo, plusz_koz=10)

    def _sugo_menu(self) -> None:
        """A súgók egy legördülő menüben (kevesebb hely az eszközsorban)."""
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_betu(10))
        for szoveg, tartalom, cim in (("Súgó (F1)", GYORS_SUGO, "Súgó"),
                                      ("A MineScript nyelv", NYELV_SUGO, "A MineScript nyelv"),
                                      ("Billentyűparancsok", BILLENTYUK, "Billentyűparancsok")):
            menu.add_command(label=szoveg, command=lambda t=tartalom, c=cim: self._sugo(c, t))
        gomb = self._sugo_gomb
        menu.tk_popup(gomb.winfo_rootx(), gomb.winfo_rooty() + gomb.winfo_height())

    def _allapotsor(self) -> None:
        self.allapot_sav = ctk.CTkFrame(self, fg_color=stilus.SZIN_INFO, corner_radius=0, height=34)
        self.allapot_sav.pack(side="bottom", fill="x")
        self.allapot_cimke = ctk.CTkLabel(self.allapot_sav, text="", anchor="w", font=stilus.betu(12, True),
                                          text_color="#ffffff")
        self.allapot_cimke.pack(side="left", fill="x", expand=True, padx=12, pady=4)
        self.naplo_cimke = ctk.CTkLabel(self.allapot_sav, text="", font=stilus.betu(11), text_color="#e2e8f0")
        self.naplo_cimke.pack(side="right", padx=12)
        self._allapot("Kész. Építsd fel a programot a blokkszerkesztőben, majd indítsd el (F5 / F10 / F8).",
                      stilus.SZIN_INFO)

    def _fo_terulet(self) -> None:
        tabla = tk.PanedWindow(self, orient="horizontal", background=stilus.HATTER, sashwidth=8,
                               borderwidth=0, sashrelief="flat")
        tabla.pack(fill="both", expand=True, padx=8, pady=8)
        self.szerkeszto = Blokkszerkeszto(tabla, self.program, self._program_valtozott,
                                          self._kijeloles_valtozott, self._uzenet,
                                          self._visszavonas, self._ujra)
        self.szerkeszto.torespontok = self.torespontok
        self.szerkeszto.torespont_valt = self._torespont_valt
        tabla.add(self.szerkeszto, minsize=520, width=660, stretch="always")
        kozep = tk.PanedWindow(tabla, orient="vertical", background=stilus.HATTER, sashwidth=8,
                               borderwidth=0, sashrelief="flat")
        self.kodnezet = Kodnezet(kozep, self._kod_kattintas, self._torespont_valt)
        kozep.add(self.kodnezet, minsize=200, height=480, stretch="always")
        kozep.add(self._valtozotabla(kozep), minsize=140, stretch="always")
        tabla.add(kozep, minsize=300, width=370, stretch="always")
        jobb = tk.PanedWindow(tabla, orient="vertical", background=stilus.HATTER, sashwidth=8,
                              borderwidth=0, sashrelief="flat")
        self.szimulator = SzimulatorNezet(jobb, self.kezi_parancs, self._terkep_kattintas,
                                          self._terkep_szerkeszto, self._terkep_meret)
        jobb.add(self.szimulator, minsize=420, height=580, stretch="always")
        jobb.add(self._also_fulek(jobb), minsize=150, stretch="always")
        tabla.add(jobb, minsize=460, stretch="always")

    def _valtozotabla(self, szulo) -> ctk.CTkFrame:
        keret = ctk.CTkFrame(szulo, fg_color=stilus.PANEL, corner_radius=10,
                             border_width=1, border_color=stilus.SZEGELY)
        fejlec = ctk.CTkFrame(keret, fg_color="transparent")
        fejlec.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(fejlec, text="Változók", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(side="left")
        self.szamlalo_cimke = ctk.CTkLabel(fejlec, text="", font=stilus.betu(11), text_color=stilus.HALVANY)
        self.szamlalo_cimke.pack(side="right")
        self.limit_sav = ctk.CTkProgressBar(keret, height=6, progress_color="#2563eb")
        self.limit_sav.set(0)
        self.limit_sav.pack(fill="x", padx=12, pady=(4, 0))
        Tooltip(self.limit_sav, f"Végrehajtott sorok a {UTASITAS_LIMIT} soros korláthoz képest.")
        self.valtozo_doboz = ctk.CTkTextbox(keret, font=stilus.mono(12), wrap="none", fg_color="#fbfcfe",
                                            border_width=1, border_color=stilus.SZEGELY,
                                            text_color=stilus.SZOVEG, height=120)
        self.valtozo_doboz.pack(fill="both", expand=True, padx=8, pady=8)
        belso = self.valtozo_doboz._textbox
        belso.tag_configure("fejlec", foreground=stilus.HALVANY)
        belso.tag_configure("valtozott", background="#fef3c7", foreground="#92400e")
        belso.tag_configure("ures", foreground=stilus.HALVANY)
        self._valtozok_frissit()
        return keret

    def _also_fulek(self, szulo) -> ctk.CTkFrame:
        keret = ctk.CTkFrame(szulo, fg_color=stilus.PANEL, corner_radius=10,
                             border_width=1, border_color=stilus.SZEGELY)
        fulek = ctk.CTkTabview(keret, fg_color=stilus.PANEL, segmented_button_selected_color=stilus.KIEMELO,
                               height=180)
        fulek.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        konzol_ful = fulek.add("Konzol (kimenet, hibák)")
        naplo_ful = fulek.add("Napló")
        fulek._segmented_button.configure(font=stilus.betu(12, True))
        self.konzol = self._szovegdoboz(konzol_ful)
        naplo_sav = ctk.CTkFrame(naplo_ful, fg_color="transparent")
        naplo_sav.pack(fill="x")
        self.naplo_hely_cimke = ctk.CTkLabel(naplo_sav, text="", font=stilus.betu(10),
                                             text_color=stilus.HALVANY, anchor="w")
        self.naplo_hely_cimke.pack(side="left", fill="x", expand=True)
        megnyit = ctk.CTkButton(naplo_sav, text="Naplófájl megnyitása", height=26, width=10,
                                font=stilus.betu(11), command=self._naplo_megnyit)
        megnyit.pack(side="right")
        Tooltip(megnyit, "A naplófájl megnyitása a Jegyzettömbben. Futás közben is: a fájl soronként íródik.")
        self.naplo_szoveg = self._szovegdoboz(naplo_ful)
        belso = self.konzol._textbox
        belso.tag_configure("hiba", foreground=stilus.SZIN_HIBA, font=stilus.tk_mono(11, True))
        belso.tag_configure("ok", foreground=stilus.SZIN_OK, font=stilus.tk_mono(11, True))
        belso.tag_configure("info", foreground=stilus.HALVANY)
        belso.tag_configure("kimenet", foreground="#0f172a", font=stilus.tk_mono(12, True))
        return keret

    def _szovegdoboz(self, szulo) -> ctk.CTkTextbox:
        doboz = ctk.CTkTextbox(szulo, font=stilus.mono(12), wrap="word", fg_color="#fbfcfe",
                               border_width=1, border_color=stilus.SZEGELY, text_color=stilus.SZOVEG)
        doboz.pack(fill="both", expand=True, pady=(4, 0))
        doboz.configure(state="disabled")
        return doboz

    def _billentyuk(self) -> None:
        self.bind("<F5>", lambda _e: self.futtatas())
        self.bind("<F10>", lambda _e: (self.nyomkovetes(), "break")[1])
        self.bind("<F8>", lambda _e: self.vegig())
        self.bind("<F9>", lambda _e: self._torespont_kijelolt())
        self.bind("<Escape>", lambda _e: self.leallitas())
        self.bind("<F1>", lambda _e: self._sugo("Súgó", GYORS_SUGO))
        self.bind("<Control-o>", lambda _e: self._megnyitas())
        self.bind("<Control-s>", lambda _e: self._mentes())
        self.bind("<Control-n>", lambda _e: self._uj_program())
        self.bind("<Control-z>", lambda _e: self._visszavonas())
        self.bind("<Control-y>", lambda _e: self._ujra())
        self.bind("<Control-Z>", lambda _e: self._ujra())

    def _sugo(self, cim: str, szoveg: str) -> None:
        ablak = ctk.CTkToplevel(self)
        ablak.title(cim)
        ablak.geometry("780x660")
        ablak.transient(self)
        doboz = ctk.CTkTextbox(ablak, font=stilus.mono(12), wrap="word")
        doboz.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        doboz.insert("1.0", szoveg)
        doboz.configure(state="disabled")
        ctk.CTkButton(ablak, text="Bezárás", command=ablak.destroy, font=stilus.betu(12)).pack(pady=(0, 10))
        ablak.after(50, ablak.lift)

    # ---------- Kijelzések ----------

    def _allapot(self, szoveg: str, szin: str) -> None:
        self.allapot_sav.configure(fg_color=szin)
        self.allapot_cimke.configure(text=szoveg)
        self.naplo_cimke.configure(text=f"Naplófájl: {os.path.basename(self.naplo_utvonal)}")
        if hasattr(self, "naplo_hely_cimke"):
            self.naplo_hely_cimke.configure(text=f"Fájl: {os.path.abspath(self.naplo_utvonal)}")

    def _uzenet(self, szoveg: str, hiba: bool) -> None:
        """A blokkszerkesztő rövid visszajelzései az állapotsorban."""
        self._allapot(szoveg, stilus.SZIN_HIBA if hiba else stilus.SZIN_INFO)

    def _szoveg_ir(self, doboz: ctk.CTkTextbox, szoveg: str, cimke: str = "") -> None:
        doboz.configure(state="normal")
        doboz._textbox.insert("end", szoveg + "\n", cimke)
        doboz._textbox.see("end")
        doboz.configure(state="disabled")

    def _szoveg_torol(self, doboz: ctk.CTkTextbox) -> None:
        doboz.configure(state="normal")
        doboz.delete("1.0", "end")
        doboz.configure(state="disabled")

    def _valtozok_frissit(self) -> None:
        doboz = self.valtozo_doboz
        belso = doboz._textbox
        doboz.configure(state="normal")
        belso.delete("1.0", "end")
        if self.futtato is None:
            belso.insert("end", "Futtatás / nyomkövetés\nközben itt látszanak\na változók értékei.", "ures")
            self.szamlalo_cimke.configure(text="")
            self.limit_sav.set(0)
            doboz.configure(state="disabled")
            return
        valtozok = self.futtato.valtozok
        belso.insert("end", f"{'név':<14}{'típus':<10}érték\n", "fejlec")
        if not valtozok:
            belso.insert("end", "(még nincs változó)", "ures")
        for nev, ertek in valtozok.items():
            tipus = "logikai" if type(ertek) is bool else "egész"
            valtozott = nev not in self._elozo_valtozok or self._elozo_valtozok[nev] != ertek \
                or type(self._elozo_valtozok[nev]) is not type(ertek)
            belso.insert("end", f"{nev:<14}{tipus:<10}{ertek_szoveg(ertek)}\n",
                         "valtozott" if valtozott and self.mod is not Mod.ALL else "")
        self._elozo_valtozok = dict(valtozok)
        feldolgozott = self.futtato.feldolgozott
        self.szamlalo_cimke.configure(text=f"végrehajtott sorok: {feldolgozott} / {UTASITAS_LIMIT}")
        self.limit_sav.set(feldolgozott / UTASITAS_LIMIT)
        doboz.configure(state="disabled")

    def _gombok_frissit(self) -> None:
        feliratok = {Mod.ALL: "▷  Lépésenként (F10)", Mod.NYOMKOVETES: "▷  Következő sor (F10)",
                     Mod.FUTAS: "‖  Szünet (F10)"}
        self.lepes_gomb.configure(text=feliratok[self.mod])
        self.futtat_gomb.configure(text="▶  Folytatás (F5)" if self.mod is Mod.NYOMKOVETES
                                   else "▶  Futtatás (F5)")
        self.vegig_gomb.configure(text="▶▶  Folytatás végig (F8)" if self.mod is Mod.NYOMKOVETES
                                  else "▶▶  Végig (F8)")
        self.leallit_gomb.configure(state="disabled" if self.mod is Mod.ALL else "normal")

    def _kiemeles_torol(self) -> None:
        self.kodnezet.kiemel(None)
        self.kodnezet.kovetkezo_jelol(None)
        self.szerkeszto.kiemel_sorszam(None)

    # ---------- Program, kijelölés, visszavonás, töréspontok ----------

    def _allapot_kep(self) -> list[str]:
        """A mentéshez tartozó tartalom (térkép + program) – a módosítás figyeléséhez."""
        return [*self.alap_vilag.terkep_sorai(), "|", *program_sorai(self.program)]

    def _modositott(self) -> bool:
        return self._allapot_kep() != self._mentett_allapot

    def _cim_frissit(self) -> None:
        nev = os.path.basename(self.fajl_utvonal) if self.fajl_utvonal else "névtelen"
        jelzo = " •" if self._modositott() else ""
        self.title(f"{ABLAK_CIM} – {nev}{jelzo}")

    def _program_valtozott(self) -> None:
        """Bármely szerkesztés után: futás leáll, sorszámok, szöveges nézet, blokkok frissülnek."""
        self.leallit(csendes=True)
        self._kiemeles_torol()
        sorszamoz(self.program)
        sorok = program_sorai(self.program)
        if sorok != self._elozmeny[self._elozmeny_index]:
            del self._elozmeny[self._elozmeny_index + 1:]
            self._elozmeny.append(sorok)
            if len(self._elozmeny) > ELOZMENY_MAX:
                self._elozmeny.pop(0)
            self._elozmeny_index = len(self._elozmeny) - 1
        self.torespontok.intersection_update(range(1, len(sorok) + 1))
        self.kodnezet.megjelenit(sorok, self.torespontok)
        self.szerkeszto.frissit()
        self._kijeloles_valtozott(self.szerkeszto.kijelolt)
        self._cim_frissit()

    def _elozmeny_betolt(self, index: int) -> None:
        self._elozmeny_index = index
        self.program[:] = elemez(self._elozmeny[index])
        self.szerkeszto.kijelolt = None
        self._program_valtozott()

    def _visszavonas(self) -> None:
        if self._elozmeny_index == 0:
            self._uzenet("Nincs mit visszavonni.", False)
            return
        self._elozmeny_betolt(self._elozmeny_index - 1)
        self._uzenet("Visszavonva.", False)

    def _ujra(self) -> None:
        if self._elozmeny_index >= len(self._elozmeny) - 1:
            self._uzenet("Nincs mit újra végrehajtani.", False)
            return
        self._elozmeny_betolt(self._elozmeny_index + 1)
        self._uzenet("Újra végrehajtva.", False)

    def _kijeloles_valtozott(self, utasitas: Utasitas | None) -> None:
        self.kodnezet.kijelol(blokk_sorszamai(utasitas) if utasitas is not None else [])

    def _kod_kattintas(self, sorszam: int) -> None:
        self.szerkeszto.kijelol_sorszam(sorszam)

    def _torespont_valt(self, sorszam: int) -> None:
        if sorszam in self.torespontok:
            self.torespontok.discard(sorszam)
            self._uzenet(f"Töréspont törölve: {sorszam}. sor.", False)
        else:
            self.torespontok.add(sorszam)
            self._uzenet(f"Töréspont: {sorszam}. sor – a futás a sor végrehajtása előtt megáll.", False)
        self.kodnezet.torespontok_beallit(self.torespontok)
        self.szerkeszto.frissit()

    def _torespont_kijelolt(self) -> None:
        if self.szerkeszto.kijelolt is None:
            self._uzenet("Töréspont: előbb jelölj ki egy blokkot (vagy kattints egy sorszámra).", False)
            return
        self._torespont_valt(self.szerkeszto.kijelolt.sorszam)

    # ---------- Futtatás: indítás, léptetés, befejezés ----------

    def _kesleltetes(self) -> int:
        return int(KESLELTETES_MAX_MS + KESLELTETES_MIN_MS - self.sebesseg.get())

    def futtatas(self) -> None:
        """F5: animált futás az elejétől; töréspontnál / szünetben: animált folytatás."""
        if self.mod is Mod.NYOMKOVETES:
            self.mod = Mod.FUTAS
            self._allapot("Folytatás (animált futás)…", stilus.SZIN_FUT)
            self._gombok_frissit()
            self._futas_tick(torespont_figyel=False)
            return
        self._indit(Mod.FUTAS)
        if self._elore_nez():
            if self._torespontnal_all():
                return
            self._utemez()

    def nyomkovetes(self) -> None:
        """F10: nyomkövetés indítása, következő sor, vagy animált futás közben szünet."""
        if self.mod is Mod.FUTAS:
            self._idozito_torol()
            self.mod = Mod.NYOMKOVETES
            self._allapot("Szünet – F10 = következő sor, F5 = folytatás, F8 = végig.", stilus.SZIN_FUT)
            self._gombok_frissit()
            return
        if self.mod is Mod.ALL:
            self._indit(Mod.NYOMKOVETES)
            if self._elore_nez():
                self._allapot(f"Nyomkövetés elindult. A ▶ jel a következő sort mutatja "
                              f"({self._fuggo.sorszam}. sor) – F10 = végrehajtás.", stilus.SZIN_FUT)
            return
        sor = self._vegrehajt_egy_sort()
        if sor is not None and self.mod is Mod.NYOMKOVETES:
            self._lepes_megjelenit(sor, NYOMKOVETES_CELLA_MS, self._nyomkovetes_utan)

    def _nyomkovetes_utan(self) -> None:
        if self.mod is Mod.NYOMKOVETES and self._fuggo is None:
            self._elore_nez()

    def vegig(self) -> None:
        """F8: azonnali futás a végéig vagy a következő töréspontig."""
        if self.mod is Mod.ALL:
            self._indit(Mod.FUTAS)
            if not self._elore_nez() or self._torespontnal_all():
                return
        self._idozito_torol()
        self.mod = Mod.FUTAS
        elso = True
        while self.mod is Mod.FUTAS:
            if not elso and self._torespontnal_all():
                break
            elso = False
            sor = self._vegrehajt_egy_sort(megjelenit=False)
            if sor is None or self.futtato.hiba is not None:
                break
            if not self._elore_nez(megjelenit=False):
                break
        if self.mod is not Mod.ALL:
            self._allapot_szinkron()

    def leallitas(self) -> None:
        self.leallit(csendes=False)

    def _indit(self, mod: Mod) -> None:
        self.leallit(csendes=True)
        self.focus_set()
        if self.szimulator.szerkeszto_mod:
            self.szimulator.szerkeszto_mod_beallit(False)
        self.vilag = self.alap_vilag.masolat()
        self._szoveg_torol(self.konzol)
        self._szoveg_torol(self.naplo_szoveg)
        naplo = self._naplo_nyit()
        self.futtato = Futtato(self.program, self.vilag, kiiro=self._kimenet, naplo=naplo)
        self.lepesek = self.futtato.lepesek(elore_jelez=True)
        self._fuggo = None
        self.mod = mod
        self._elozo_valtozok = {}
        self._valtozok_frissit()
        self.szimulator.rajzol(self.vilag)
        self._allapot(f"Fut ({mod.value})…", stilus.SZIN_FUT)
        self._gombok_frissit()

    def _naplo_nyit(self) -> Naplo:
        """Élő napló a naplófájlba; ha a fájl nem írható, csak memóriában naplózunk."""
        try:
            return Naplo(elo_fajl=self.naplo_utvonal)
        except OSError as hiba:
            self._szoveg_ir(self.konzol, f"A naplófájl nem írható ({hiba}); a napló csak itt látszik.", "hiba")
            return Naplo()

    def _kimenet(self, szoveg: str) -> None:
        self._szoveg_ir(self.konzol, szoveg, "kimenet")

    def _elore_nez(self, megjelenit: bool = True) -> bool:
        """A következő esemény: `SorElott` (▶ jel) vagy a futás vége. Igaz, ha van következő sor."""
        try:
            esemeny = next(self.lepesek)
        except StopIteration:
            self._befejez()
            return False
        self._fuggo = esemeny
        if megjelenit:
            self.kodnezet.kovetkezo_jelol(esemeny.sorszam)
        return True

    def _vegrehajt_egy_sort(self, megjelenit: bool = True) -> NaploSor | None:
        """Végrehajtja a függő sort; hibánál a futást is lezárja. None, ha nincs több sor."""
        try:
            if self._fuggo is None:
                self._fuggo = next(self.lepesek)
            sor = next(self.lepesek)
        except StopIteration:
            self._befejez()
            return None
        self._fuggo = None
        if self.futtato.hiba is not None:
            for _ in self.lepesek:
                pass
            self._befejez()
        return sor

    def _torespontnal_all(self) -> bool:
        """Ha a következő sor töréspontos, szünetre vált. Igaz, ha megállt."""
        if self._fuggo is None or self._fuggo.sorszam not in self.torespontok:
            return False
        self._idozito_torol()
        self.mod = Mod.NYOMKOVETES
        self._allapot_szinkron()
        self._allapot(f"Töréspont: a {self._fuggo.sorszam}. sor következik.  F10 = lépés, "
                      "F5 = animált folytatás, F8 = folytatás a végéig.", "#7c3aed")
        self._gombok_frissit()
        return True

    def _allapot_szinkron(self) -> None:
        """Animáció nélküli, teljes frissítés (azonnali futás után)."""
        self.szimulator.rajzol(self.vilag)
        self._valtozok_frissit()
        self._szoveg_torol(self.naplo_szoveg)
        self._szoveg_ir(self.naplo_szoveg, "\n".join(self.futtato.naplo.sorok))
        if self._fuggo is not None:
            self.kodnezet.kovetkezo_jelol(self._fuggo.sorszam)
            self.kodnezet.kiemel(None)
            self.szerkeszto.kiemel_sorszam(self._fuggo.sorszam)

    def _utemez(self) -> None:
        self._idozito = self.after(self._kesleltetes(), self._futas_tick)

    def _idozito_torol(self) -> None:
        if self._idozito is not None:
            self.after_cancel(self._idozito)
            self._idozito = None

    def _futas_tick(self, torespont_figyel: bool = True) -> None:
        """Animált futás: egy sor végrehajtása, animáció, majd a következő ütemezése."""
        self._idozito = None
        if self.mod is not Mod.FUTAS:
            return
        if torespont_figyel and self._torespontnal_all():
            return
        sor = self._vegrehajt_egy_sort()
        if sor is None or self.mod is not Mod.FUTAS:
            return
        cella_ms = max(FUTAS_CELLA_MIN_MS, min(FUTAS_CELLA_MAX_MS, int(self._kesleltetes() * 0.6)))
        self._lepes_megjelenit(sor, cella_ms, self._futas_kovetkezo)

    def _futas_kovetkezo(self) -> None:
        if self.mod is Mod.FUTAS and self._fuggo is None and self._elore_nez():
            self._utemez()

    def _lepes_megjelenit(self, sor: NaploSor, cella_ms: int, kesz) -> None:
        hibas = sor.hiba is not None
        self.kodnezet.kiemel(sor.sorszam, hibas=hibas)
        self.kodnezet.kovetkezo_jelol(None)
        self.szerkeszto.kiemel_sorszam(sor.sorszam, hibas=hibas)
        self._valtozok_frissit()
        self._szoveg_ir(self.naplo_szoveg, sor.szoveg())
        if self.mod is Mod.NYOMKOVETES:
            self._allapot(f"Nyomkövetés: végrehajtva a(z) {sor.sorszam}. sor  →  napló: „{sor.szoveg()}”.  "
                          "F10 = következő sor.", stilus.SZIN_FUT)
        self.szimulator.animal(self.vilag, cella_ms, kesz)

    def _befejez(self) -> None:
        futtato = self.futtato
        self._szoveg_torol(self.naplo_szoveg)
        self._szoveg_ir(self.naplo_szoveg, futtato.naplo.szoveg().rstrip("\n"))
        self.mod = Mod.ALL
        self.lepesek = None
        self._fuggo = None
        self._idozito_torol()
        self.kodnezet.kovetkezo_jelol(None)
        self._gombok_frissit()
        self._valtozok_frissit()
        self.szimulator.rajzol(self.vilag)
        if futtato.allapot is Vegallapot.HIBA:
            uzenet = (f"HIBA a(z) {futtato.hiba_sorszam}. sorban: {futtato.hiba.value} – "
                      f"{HIBA_LEIRASOK[futtato.hiba]}")
            self.kodnezet.kiemel(futtato.hiba_sorszam, hibas=True)
            self.szerkeszto.kiemel_sorszam(futtato.hiba_sorszam, hibas=True)
            self._szoveg_ir(self.konzol, uzenet, "hiba")
            self._allapot(uzenet, stilus.SZIN_HIBA)
            return
        self._kiemeles_torol()
        if futtato.allapot is Vegallapot.LIMIT:
            uzenet = f"LEÁLLT: {LIMIT_TULLEPES} – {LIMIT_LEIRAS}"
            self._szoveg_ir(self.konzol, uzenet, "hiba")
            self._allapot(uzenet, stilus.SZIN_HIBA)
            return
        uzenet = (f"A program hibátlanul lefutott ({futtato.feldolgozott} sor). "
                  f"Kibányászott arany: {self.vilag.arany_db} / {self.vilag.osszes_arany()}")
        self._szoveg_ir(self.konzol, uzenet, "ok")
        self._allapot(uzenet, stilus.SZIN_OK)

    def leallit(self, csendes: bool) -> None:
        """Megszakítja a futást (a naplófájlban a részleges napló marad)."""
        if self.mod is Mod.ALL:
            return
        self._idozito_torol()
        self.lepesek.close()
        self.lepesek = None
        self._fuggo = None
        self.futtato.naplo.bezar()
        self.mod = Mod.ALL
        self._kiemeles_torol()
        self._gombok_frissit()
        self.szimulator.rajzol(self.vilag)
        if not csendes:
            self._szoveg_ir(self.konzol, "A futás leállítva.", "info")
            self._allapot("Leállítva.", stilus.SZIN_INFO)

    # ---------- Kézi vezérlés ----------

    def kezi_parancs(self, parancs: str) -> None:
        if self.szimulator.szerkeszto_mod:
            self._allapot("Térképszerkesztés közben a robot nem vezérelhető – kattints a „Kész” gombra.",
                          stilus.SZIN_FUT)
            return
        if self.mod is not Mod.ALL:
            self.leallit(csendes=True)
            self._szoveg_ir(self.konzol, "A futás megszakadt (kézi vezérlés).", "info")
        if parancs == "alaphelyzet":
            self.vilag = self.alap_vilag.masolat()
            self.szimulator.rajzol(self.vilag)
            self._allapot("A térkép és a robot visszaállt a kiinduló állapotba.", stilus.SZIN_INFO)
            return
        self._kezi_vegrehajt(parancs)
        self.szimulator.animal(self.vilag, KEZI_CELLA_MS)

    def _kezi_vegrehajt(self, parancs: str) -> None:
        try:
            if parancs == "balra":
                self.vilag.fordul(1)
            elif parancs == "jobbra":
                self.vilag.fordul(3)
            elif parancs == "lepes":
                self.vilag.lep(1)
            elif parancs == "banyasz":
                self.vilag.banyasz()
        except FutasiHiba as hiba:
            if hiba.kod is HibaKod.E_BEDROCK_HIT:
                self._allapot("Kézi vezérlés: a robot előtt fal vagy a térkép széle van – megállt.",
                              stilus.SZIN_FUT)
            else:
                self._allapot("Kézi vezérlés: ezen a mezőn nincs arany.", stilus.SZIN_FUT)
            return
        nevek = {"balra": "fordulás balra", "jobbra": "fordulás jobbra", "lepes": "lépés előre",
                 "banyasz": "bányászás"}
        self._allapot(f"Kézi vezérlés: {nevek[parancs]}.  Arany: {self.vilag.arany_db} / "
                      f"{self.vilag.osszes_arany()}", stilus.SZIN_INFO)

    # ---------- Térképszerkesztés ----------

    def _terkep_szerkeszto(self, bekapcsolva: bool) -> None:
        self.leallit(csendes=True)
        self.vilag = self.alap_vilag.masolat()
        self.szimulator.rajzol(self.vilag)
        if bekapcsolva:
            self._allapot("Térképszerkesztés: válassz eszközt, majd kattints / húzz a térképen. "
                          "Kész: „✓ Kész”.", "#7c3aed")
        else:
            self._allapot("Térképszerkesztés befejezve. Mentés: Ctrl+S.", stilus.SZIN_INFO)

    def _terkep_kattintas(self, sor: int, oszlop: int, eszkoz: str) -> None:
        if eszkoz == "robot":
            sikeres = self.alap_vilag.robot_athelyez(sor, oszlop)
        else:
            mezo = {"ures": Mezo.URES, "fal": Mezo.FAL, "arany": Mezo.ARANY}[eszkoz]
            sikeres = self.alap_vilag.mezo_szerkeszt(sor, oszlop, mezo)
        if not sikeres:
            self._allapot("A robot mezője csak üres lehet – előbb helyezd át a robotot.", stilus.SZIN_FUT)
        self._terkep_frissit()

    def _terkep_meret(self, dsor: int, doszlop: int) -> None:
        terkep = self.alap_vilag.terkep
        self.alap_vilag = self.alap_vilag.atmeretezve(terkep.sorok + dsor, terkep.oszlopok + doszlop)
        uj = self.alap_vilag.terkep
        self._allapot(f"Térkép mérete: {uj.sorok} × {uj.oszlopok} (1–15).", "#7c3aed")
        self._terkep_frissit()

    def _terkep_frissit(self) -> None:
        self.vilag = self.alap_vilag.masolat()
        self.szimulator.rajzol(self.vilag)
        self._cim_frissit()

    # ---------- Fájlműveletek ----------

    def _mentes_kerdes(self) -> bool:
        """Mentetlen változásnál rákérdez. Igaz, ha folytatható a művelet."""
        if not self._modositott():
            return True
        valasz = messagebox.askyesnocancel("Mentetlen változások",
                                           "A programot (vagy a térképet) módosítottad. Mented?", parent=self)
        if valasz is None:
            return False
        if valasz:
            return self._mentes()
        return True

    def _bemenet_alkalmaz(self, bemenet: Bemenet, program: list[Utasitas], forras: str) -> None:
        self.leallit(csendes=True)
        self.szimulator.szerkeszto_mod_beallit(False)
        self.alap_vilag = bemenet.vilag
        self.vilag = self.alap_vilag.masolat()
        self.program[:] = program
        self.futtato = None
        self.torespontok.clear()
        self._valtozok_frissit()
        self._szoveg_torol(self.konzol)
        self._szoveg_torol(self.naplo_szoveg)
        self.szerkeszto.program_beallit(self.program)
        self._elozmeny = [program_sorai(self.program)]
        self._elozmeny_index = 0
        self._mentett_allapot = self._allapot_kep()
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)
        self._allapot(f"Betöltve: {forras}", stilus.SZIN_INFO)

    def betolt(self, utvonal: str) -> None:
        try:
            bemenet = beolvas_fajl(utvonal)
            program = elemez(bemenet.program_sorok)
        except Exception as hiba:  # bármilyen hibás fájl: üzenet, a régi állapot marad
            messagebox.showerror("Megnyitás", f"A fájl nem tölthető be:\n{utvonal}\n\n{hiba}", parent=self)
            return
        self.fajl_utvonal = utvonal
        self._bemenet_alkalmaz(bemenet, program, utvonal)

    def _pelda_betolt(self, pelda: Pelda) -> None:
        if not self._mentes_kerdes():
            return
        bemenet = beolvas_szoveg(pelda.szoveg)
        self.fajl_utvonal = None
        self._bemenet_alkalmaz(bemenet, elemez(bemenet.program_sorok), f"példa – {pelda.nev}")
        self._allapot(f"Példa betöltve: {pelda.nev}.  {pelda.leiras}", stilus.SZIN_INFO)

    def _peldak_menu(self) -> None:
        menu = tk.Menu(self, tearoff=False, font=stilus.tk_betu(11))
        for pelda in PELDAK:
            menu.add_command(label=pelda.nev, command=lambda p=pelda: self._pelda_betolt(p))
        gomb = self._peldak_gomb
        menu.tk_popup(gomb.winfo_rootx(), gomb.winfo_rooty() + gomb.winfo_height())

    def _uj_program(self) -> None:
        if not self.program:
            self._uzenet("A program már üres.", False)
            return
        if not messagebox.askyesno("Új program", "Törlöd a teljes programot? (A térkép megmarad; "
                                                 "Ctrl+Z-vel visszavonható.)", parent=self):
            return
        self.program.clear()
        self.szerkeszto.kijelolt = None
        self._program_valtozott()
        self._uzenet("Új, üres program. Húzz be blokkokat a palettáról!", False)

    def _megnyitas(self) -> None:
        if not self._mentes_kerdes():
            return
        utvonal = filedialog.askopenfilename(parent=self, title="Bemeneti fájl megnyitása",
                                             filetypes=[("Szövegfájl", "*.txt"), ("Minden fájl", "*.*")])
        if utvonal:
            self.betolt(utvonal)

    def _mentes(self) -> bool:
        if self.fajl_utvonal is None:
            return self._mentes_maskent()
        szoveg = bemenet_szoveg(self.alap_vilag, program_sorai(self.program))
        try:
            with open(self.fajl_utvonal, "w", encoding="utf-8", newline="\n") as fajl:
                fajl.write(szoveg)
        except OSError as hiba:
            messagebox.showerror("Mentés", f"Nem sikerült menteni:\n{hiba}", parent=self)
            return False
        self._mentett_allapot = self._allapot_kep()
        self._cim_frissit()
        self._allapot(f"Mentve: {self.fajl_utvonal}", stilus.SZIN_OK)
        return True

    def _mentes_maskent(self) -> bool:
        utvonal = filedialog.asksaveasfilename(parent=self, title="Mentés másként", defaultextension=".txt",
                                               filetypes=[("Szövegfájl", "*.txt")])
        if not utvonal:
            return False
        self.fajl_utvonal = utvonal
        return self._mentes()

    def _naplo_hely(self) -> None:
        utvonal = filedialog.asksaveasfilename(parent=self, title="Naplófájl helye", defaultextension=".txt",
                                               initialfile=os.path.basename(self.naplo_utvonal),
                                               filetypes=[("Szövegfájl", "*.txt")])
        if utvonal:
            self.naplo_utvonal = utvonal
            self._allapot(f"A napló ide kerül: {utvonal}", stilus.SZIN_INFO)

    def _naplo_megnyit(self) -> None:
        if not os.path.exists(self.naplo_utvonal):
            self._allapot("A naplófájl még nem létezik – előbb futtasd a programot.", stilus.SZIN_FUT)
            return
        try:
            fajl_megnyitasa(os.path.abspath(self.naplo_utvonal))
        except OSError as hiba:
            self._allapot(f"A naplófájl nem nyitható meg: {hiba}", stilus.SZIN_HIBA)

    def _kilepes(self) -> None:
        if not self._mentes_kerdes():
            return
        self.leallit(csendes=True)
        self.destroy()


def inditas(be_utvonal: str | None, ki_utvonal: str | None) -> None:
    """Az IDE elindítása (a main.py hívja)."""
    ablak = Foablak(be_utvonal, ki_utvonal)
    ablak.mainloop()
