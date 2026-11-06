"""Az IDE főablaka (customtkinter): eszközsor, blokkszerkesztő, kódnézet, változók,
szimulátor, konzol, napló és állapotsor.

Itt kapcsolódik a felület a GUI-tól független logikához (beolvasó, futtató, világ, napló).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from enum import Enum
from tkinter import filedialog, messagebox

import customtkinter as ctk

from beolvaso import beolvas_fajl, beolvas_szoveg, bemenet_szoveg
from futtato import UTASITAS_LIMIT, Futtato, Vegallapot
from gui import stilus
from gui.blokkszerkeszto import Blokkszerkeszto
from gui.kodnezet import Kodnezet
from gui.szimulator_nezet import SzimulatorNezet
from gui.tooltip import Tooltip
from hibak import HIBA_LEIRASOK, LIMIT_LEIRAS, LIMIT_TULLEPES, FutasiHiba, HibaKod
from naplo import NaploSor, ertek_szoveg
from nyelv.elemzo import elemez
from nyelv.kiiro import program_sorai, sorszamoz
from nyelv.szerkesztes import torzsek
from nyelv.utasitasok import Elagazas, Utasitas

ABLAK_CIM = "MineScript robotszimulátor – IDE"
ALAP_NAPLO = "naplo.txt"
ALAP_BEMENET = "5 5\n>....\n.....\n.....\n.....\n.....\n"
KESLELTETES_MIN_MS = 20
KESLELTETES_MAX_MS = 1200
KESLELTETES_ALAP_MS = 350
ELOZMENY_MAX = 200

GYORS_SUGO = """GYORS KEZDÉS

1. Megnyitás (Ctrl+O): térkép + program betöltése (vagy indítás: robot.exe BE KI).

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

3. ▶ Futtatás (F5): lassított, animált futás az elejétől (a csúszkával állítható).
   ▷ Lépésenként (F10): nyomkövetés – minden lenyomás egy sort hajt végre,
   kiemeli a sort, és mutatja a változók értékét. Futás közben F10 = szünet.
   ■ Leállítás (Esc).
   Minden futás visszaállítja a térképet és a robotot; a napló felülíródik.

4. Kézi vezérlés: a gombokkal, vagy a térképre kattintva a nyilakkal / szóközzel.
   Megszakítja a futást, és nem naplóz.

Térkép: élénk mező = felfedezett (járt rajta vagy isThere nézte),
szürke = feltérképezetlen. A kék szaggatott keret a szenzor mezője."""

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
E_BAD_ARG            – hibás API-paraméter (pl. isThere 3, turn by true)"""


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
        self.geometry("1500x900")
        self.minsize(1200, 740)
        self.naplo_utvonal = ki_utvonal or ALAP_NAPLO
        self.fajl_utvonal: str | None = None
        self.alap_vilag = beolvas_szoveg(ALAP_BEMENET).vilag
        self.vilag = self.alap_vilag.masolat()
        self.program: list[Utasitas] = []
        self.futtato: Futtato | None = None
        self.lepesek = None
        self.mod = Mod.ALL
        self._idozito: str | None = None
        self._elozmeny: list[list[str]] = [[]]
        self._elozmeny_index = 0
        self._elozo_valtozok: dict[str, int | bool] = {}
        self._eszkoztar()
        self._allapotsor()
        self._fo_terulet()
        self._billentyuk()
        self.protocol("WM_DELETE_WINDOW", self._kilepes)
        if be_utvonal:
            self.betolt(be_utvonal)
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)
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

    def _eszkoztar(self) -> None:
        sav = ctk.CTkFrame(self, fg_color=stilus.PANEL, corner_radius=0, height=56)
        sav.pack(side="top", fill="x")
        ctk.CTkLabel(sav, text="MineScript IDE", font=stilus.betu(16, True),
                     text_color=stilus.SZOVEG).pack(side="left", padx=(14, 18), pady=10)
        atlatszo = dict(fg_color="transparent", border_width=1, border_color=stilus.SZEGELY,
                        text_color=stilus.SZOVEG, hover_color="#e2e8f0")
        for szoveg, parancs, sugo in (("Megnyitás", self._megnyitas, "Bemeneti fájl (térkép + program) betöltése. Ctrl+O"),
                                      ("Mentés", self._mentes, "A térkép és a program mentése. Ctrl+S"),
                                      ("Napló helye", self._naplo_hely, "Hová kerüljön a futás naplója.")):
            gomb = ctk.CTkButton(sav, text=szoveg, command=parancs, height=34, width=10,
                                 font=stilus.betu(12), corner_radius=8, **atlatszo)
            gomb.pack(side="left", padx=3)
            Tooltip(gomb, sugo)
        ctk.CTkFrame(sav, width=2, height=30, fg_color=stilus.SZEGELY).pack(side="left", padx=12)
        self.futtat_gomb = self._gomb(sav, "▶  Futtatás (F5)", self.futtatas, stilus.GOMB_FUTTAT,
                                      "Lassított, animált futtatás az elejétől (térkép és robot visszaáll).")
        self.lepes_gomb = self._gomb(sav, "▷  Lépésenként (F10)", self.nyomkovetes, stilus.GOMB_LEPES,
                                     "Nyomkövetés: minden kattintás egy sort hajt végre, és mutatja a "
                                     "változókat. Animált futás közben szünetet tart.", szel=230)
        self.leallit_gomb = self._gomb(sav, "■  Leállítás (Esc)", self.leallitas, stilus.GOMB_ALLJ,
                                       "Az aktuális futás leállítása.")
        for gomb in (self.futtat_gomb, self.lepes_gomb, self.leallit_gomb):
            gomb.pack(side="left", padx=3)
        sebesseg = ctk.CTkFrame(sav, fg_color="transparent")
        sebesseg.pack(side="left", padx=(16, 0))
        ctk.CTkLabel(sebesseg, text="Animáció:  lassú", font=stilus.betu(11),
                     text_color=stilus.HALVANY).pack(side="left")
        self.sebesseg = ctk.CTkSlider(sebesseg, from_=KESLELTETES_MIN_MS, to=KESLELTETES_MAX_MS, width=150)
        self.sebesseg.set(KESLELTETES_MAX_MS + KESLELTETES_MIN_MS - KESLELTETES_ALAP_MS)
        self.sebesseg.pack(side="left", padx=6)
        ctk.CTkLabel(sebesseg, text="gyors", font=stilus.betu(11),
                     text_color=stilus.HALVANY).pack(side="left")
        for szoveg, tartalom, cim in (("Nyelv", NYELV_SUGO, "A MineScript nyelv"),
                                      ("? Súgó (F1)", GYORS_SUGO, "Súgó")):
            gomb = ctk.CTkButton(sav, text=szoveg, height=34, width=10, font=stilus.betu(12),
                                 corner_radius=8, command=lambda t=tartalom, c=cim: self._sugo(c, t),
                                 **atlatszo)
            gomb.pack(side="right", padx=(0, 10))

    def _allapotsor(self) -> None:
        self.allapot_sav = ctk.CTkFrame(self, fg_color=stilus.SZIN_INFO, corner_radius=0, height=34)
        self.allapot_sav.pack(side="bottom", fill="x")
        self.allapot_cimke = ctk.CTkLabel(self.allapot_sav, text="", anchor="w", font=stilus.betu(12, True),
                                          text_color="#ffffff")
        self.allapot_cimke.pack(side="left", fill="x", expand=True, padx=12, pady=4)
        self.naplo_cimke = ctk.CTkLabel(self.allapot_sav, text="", font=stilus.betu(11), text_color="#e2e8f0")
        self.naplo_cimke.pack(side="right", padx=12)
        self._allapot("Kész. Építsd fel a programot a blokkszerkesztőben, majd indítsd el (F5 / F10).",
                      stilus.SZIN_INFO)

    def _fo_terulet(self) -> None:
        tabla = tk.PanedWindow(self, orient="horizontal", background=stilus.HATTER, sashwidth=8,
                               borderwidth=0, sashrelief="flat")
        tabla.pack(fill="both", expand=True, padx=8, pady=8)
        self.szerkeszto = Blokkszerkeszto(tabla, self.program, self._program_valtozott,
                                          self._kijeloles_valtozott, self._uzenet,
                                          self._visszavonas, self._ujra)
        tabla.add(self.szerkeszto, minsize=520, width=640, stretch="always")
        kozep = tk.PanedWindow(tabla, orient="vertical", background=stilus.HATTER, sashwidth=8,
                               borderwidth=0, sashrelief="flat")
        self.kodnezet = Kodnezet(kozep, self._kod_kattintas)
        kozep.add(self.kodnezet, minsize=200, height=470, stretch="always")
        kozep.add(self._valtozotabla(kozep), minsize=140, stretch="always")
        tabla.add(kozep, minsize=300, width=360, stretch="always")
        jobb = tk.PanedWindow(tabla, orient="vertical", background=stilus.HATTER, sashwidth=8,
                              borderwidth=0, sashrelief="flat")
        self.szimulator = SzimulatorNezet(jobb, self.kezi_parancs)
        jobb.add(self.szimulator, minsize=380, height=520, stretch="always")
        jobb.add(self._also_fulek(jobb), minsize=150, stretch="always")
        tabla.add(jobb, minsize=420, stretch="always")

    def _valtozotabla(self, szulo) -> ctk.CTkFrame:
        keret = ctk.CTkFrame(szulo, fg_color=stilus.PANEL, corner_radius=10,
                             border_width=1, border_color=stilus.SZEGELY)
        fejlec = ctk.CTkFrame(keret, fg_color="transparent")
        fejlec.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(fejlec, text="Változók", font=stilus.betu(14, True),
                     text_color=stilus.SZOVEG).pack(side="left")
        self.szamlalo_cimke = ctk.CTkLabel(fejlec, text="", font=stilus.betu(11), text_color=stilus.HALVANY)
        self.szamlalo_cimke.pack(side="right")
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
        ctk.CTkButton(naplo_sav, text="Naplófájl megnyitása", height=26, width=10, font=stilus.betu(11),
                      command=self._naplo_megnyit).pack(side="right")
        self.naplo_szoveg = self._szovegdoboz(naplo_ful)
        belso = self.konzol._textbox
        belso.tag_configure("hiba", foreground=stilus.SZIN_HIBA, font=stilus.tk_mono(11, True))
        belso.tag_configure("ok", foreground=stilus.SZIN_OK, font=stilus.tk_mono(11, True))
        belso.tag_configure("info", foreground=stilus.HALVANY)
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
        self.bind("<Escape>", lambda _e: self.leallitas())
        self.bind("<F1>", lambda _e: self._sugo("Súgó", GYORS_SUGO))
        self.bind("<Control-o>", lambda _e: self._megnyitas())
        self.bind("<Control-s>", lambda _e: self._mentes())
        self.bind("<Control-z>", lambda _e: self._visszavonas())
        self.bind("<Control-y>", lambda _e: self._ujra())
        self.bind("<Control-Z>", lambda _e: self._ujra())

    def _sugo(self, cim: str, szoveg: str) -> None:
        ablak = ctk.CTkToplevel(self)
        ablak.title(cim)
        ablak.geometry("760x640")
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
            belso.insert("end", "Futtatás / nyomkövetés közben itt látszanak\na változók aktuális értékei.", "ures")
            self.szamlalo_cimke.configure(text="")
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
        self.szamlalo_cimke.configure(text=f"végrehajtott sorok: {self.futtato.feldolgozott} / {UTASITAS_LIMIT}")
        doboz.configure(state="disabled")

    def _gombok_frissit(self) -> None:
        feliratok = {Mod.ALL: "▷  Lépésenként (F10)", Mod.NYOMKOVETES: "▷  Következő sor (F10)",
                     Mod.FUTAS: "‖  Szünet (F10)"}
        self.lepes_gomb.configure(text=feliratok[self.mod])
        self.leallit_gomb.configure(state="disabled" if self.mod is Mod.ALL else "normal")

    def _kiemeles_torol(self) -> None:
        self.kodnezet.kiemel(None)
        self.szerkeszto.kiemel_sorszam(None)

    # ---------- Program, kijelölés, visszavonás ----------

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
        self.kodnezet.megjelenit(sorok)
        self.szerkeszto.frissit()
        self._kijeloles_valtozott(self.szerkeszto.kijelolt)

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

    # ---------- Futtatás ----------

    def _kesleltetes(self) -> int:
        return int(KESLELTETES_MAX_MS + KESLELTETES_MIN_MS - self.sebesseg.get())

    def futtatas(self) -> None:
        self._indit(Mod.FUTAS)
        self._utemez()

    def nyomkovetes(self) -> None:
        if self.mod is Mod.FUTAS:
            self._idozito_torol()
            self.mod = Mod.NYOMKOVETES
            self._allapot("Szünet – nyomkövetés: F10 = következő sor, F5 = újraindítás.", stilus.SZIN_FUT)
            self._gombok_frissit()
            return
        if self.mod is Mod.ALL:
            self._indit(Mod.NYOMKOVETES)
        self._egy_lepes()

    def leallitas(self) -> None:
        self.leallit(csendes=False)

    def _indit(self, mod: Mod) -> None:
        self.leallit(csendes=True)
        self.focus_set()
        self.vilag = self.alap_vilag.masolat()
        self._szoveg_torol(self.konzol)
        self._szoveg_torol(self.naplo_szoveg)
        self.futtato = Futtato(self.program, self.vilag, kiiro=lambda s: self._szoveg_ir(self.konzol, s))
        self.lepesek = self.futtato.lepesek()
        self.mod = mod
        self._elozo_valtozok = {}
        self._valtozok_frissit()
        self.szimulator.rajzol(self.vilag)
        self._allapot(f"Fut ({mod.value})…", stilus.SZIN_FUT)
        self._gombok_frissit()

    def _utemez(self) -> None:
        self._idozito = self.after(self._kesleltetes(), self._animacio_lepes)

    def _idozito_torol(self) -> None:
        if self._idozito is not None:
            self.after_cancel(self._idozito)
            self._idozito = None

    def _animacio_lepes(self) -> None:
        self._idozito = None
        if self.mod is Mod.FUTAS and self._egy_lepes():
            self._utemez()

    def _egy_lepes(self) -> bool:
        """Egy forrássor végrehajtása; False, ha a futás véget ért."""
        try:
            sor = next(self.lepesek)
        except StopIteration:
            self._befejez()
            return False
        self._lepes_megjelenit(sor)
        if self.futtato.hiba is not None:
            for _ in self.lepesek:
                pass
            self._befejez()
            return False
        return True

    def _lepes_megjelenit(self, sor: NaploSor) -> None:
        hibas = sor.hiba is not None
        self.kodnezet.kiemel(sor.sorszam, hibas=hibas)
        self.szerkeszto.kiemel_sorszam(sor.sorszam, hibas=hibas)
        self.szimulator.rajzol(self.vilag)
        self._valtozok_frissit()
        self._szoveg_ir(self.naplo_szoveg, sor.szoveg())
        if self.mod is Mod.NYOMKOVETES:
            self._allapot(f"Nyomkövetés: végrehajtva a(z) {sor.sorszam}. sor  →  napló: „{sor.szoveg()}”.  "
                          "F10 = következő sor.", stilus.SZIN_FUT)

    def _befejez(self) -> None:
        futtato = self.futtato
        self._szoveg_torol(self.naplo_szoveg)
        self._szoveg_ir(self.naplo_szoveg, futtato.naplo.szoveg().rstrip("\n"))
        self._naplo_ment()
        self.mod = Mod.ALL
        self.lepesek = None
        self._gombok_frissit()
        self._valtozok_frissit()
        if futtato.allapot is Vegallapot.HIBA:
            uzenet = (f"HIBA a(z) {futtato.hiba_sorszam}. sorban: {futtato.hiba.value} – "
                      f"{HIBA_LEIRASOK[futtato.hiba]}")
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
                  f"Kibányászott arany: {self.vilag.arany_db}")
        self._szoveg_ir(self.konzol, uzenet, "ok")
        self._allapot(uzenet, stilus.SZIN_OK)

    def _naplo_ment(self) -> None:
        try:
            self.futtato.naplo.fajlba_ir(self.naplo_utvonal)
        except OSError as hiba:
            self._szoveg_ir(self.konzol, f"A naplót nem sikerült menteni: {hiba}", "hiba")

    def leallit(self, csendes: bool) -> None:
        """Megszakítja a futást (a részleges napló mentésre kerül)."""
        if self.mod is Mod.ALL:
            return
        self._idozito_torol()
        self.lepesek.close()
        self.lepesek = None
        self.mod = Mod.ALL
        self._naplo_ment()
        self._kiemeles_torol()
        self._gombok_frissit()
        if not csendes:
            self._szoveg_ir(self.konzol, "A futás leállítva.", "info")
            self._allapot("Leállítva.", stilus.SZIN_INFO)

    # ---------- Kézi vezérlés ----------

    def kezi_parancs(self, parancs: str) -> None:
        if self.mod is not Mod.ALL:
            self.leallit(csendes=True)
            self._szoveg_ir(self.konzol, "A futás megszakadt (kézi vezérlés).", "info")
        if parancs == "alaphelyzet":
            self.vilag = self.alap_vilag.masolat()
            self._allapot("A térkép és a robot visszaállt a kiinduló állapotba.", stilus.SZIN_INFO)
        else:
            self._kezi_vegrehajt(parancs)
        self.szimulator.rajzol(self.vilag)

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
        self._allapot(f"Kézi vezérlés: {nevek[parancs]}.", stilus.SZIN_INFO)

    # ---------- Fájlműveletek ----------

    def betolt(self, utvonal: str) -> None:
        try:
            bemenet = beolvas_fajl(utvonal)
            program = elemez(bemenet.program_sorok)
        except Exception as hiba:  # bármilyen hibás fájl: üzenet, a régi állapot marad
            messagebox.showerror("Megnyitás", f"A fájl nem tölthető be:\n{utvonal}\n\n{hiba}", parent=self)
            return
        self.leallit(csendes=True)
        self.fajl_utvonal = utvonal
        self.alap_vilag = bemenet.vilag
        self.vilag = self.alap_vilag.masolat()
        self.program[:] = program
        self.futtato = None
        self._valtozok_frissit()
        self.szerkeszto.program_beallit(self.program)
        self._elozmeny = [program_sorai(self.program)]
        self._elozmeny_index = 0
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)
        self.title(f"{ABLAK_CIM} – {utvonal}")
        self._allapot(f"Betöltve: {utvonal}", stilus.SZIN_INFO)

    def _megnyitas(self) -> None:
        utvonal = filedialog.askopenfilename(parent=self, title="Bemeneti fájl megnyitása",
                                             filetypes=[("Szövegfájl", "*.txt"), ("Minden fájl", "*.*")])
        if utvonal:
            self.betolt(utvonal)

    def _mentes(self) -> None:
        if self.fajl_utvonal is None:
            self._mentes_maskent()
            return
        szoveg = bemenet_szoveg(self.alap_vilag, program_sorai(self.program))
        try:
            with open(self.fajl_utvonal, "w", encoding="utf-8", newline="\n") as fajl:
                fajl.write(szoveg)
        except OSError as hiba:
            messagebox.showerror("Mentés", f"Nem sikerült menteni:\n{hiba}", parent=self)
            return
        self._allapot(f"Mentve: {self.fajl_utvonal}", stilus.SZIN_OK)

    def _mentes_maskent(self) -> None:
        utvonal = filedialog.asksaveasfilename(parent=self, title="Mentés másként", defaultextension=".txt",
                                               filetypes=[("Szövegfájl", "*.txt")])
        if utvonal:
            self.fajl_utvonal = utvonal
            self._mentes()

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
        self.leallit(csendes=True)
        self.destroy()


def inditas(be_utvonal: str | None, ki_utvonal: str | None) -> None:
    """Az IDE elindítása (a main.py hívja)."""
    ablak = Foablak(be_utvonal, ki_utvonal)
    ablak.mainloop()
