"""Az IDE főablaka: menü, eszköztár, blokkszerkesztő, kódnézet, változótábla, szimulátor, konzol, napló.

Itt kapcsolódik a felület a GUI-tól független logikához (beolvasó, futtató, világ, napló).
"""

from __future__ import annotations

import tkinter as tk
from enum import Enum
from tkinter import filedialog, messagebox, ttk

from beolvaso import beolvas_fajl, beolvas_szoveg, bemenet_szoveg
from futtato import UTASITAS_LIMIT, Futtato, Vegallapot
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
KESLELTETES_MIN_MS = 30
KESLELTETES_MAX_MS = 1500
KESLELTETES_ALAP_MS = 350

SZIN_OK = "#2e7d32"
SZIN_HIBA = "#c62828"
SZIN_FUT = "#ef6c00"
SZIN_INFO = "#37474f"

GYORS_SUGO = """Gyors kezdés

1. Fájl → Megnyitás: térkép + program betöltése (vagy indítás: robot.exe BE KI).
2. Programot CSAK a bal oldali blokkszerkesztővel lehet írni:
   • kattints egy blokkra → kijelölés,
   • „＋ Elé / Mögé / Törzsbe / Else-ágba” menüből válassz blokktípust,
   • a kijelölt blokk mezőit lent írd át, majd Enter / Alkalmaz,
   • Törlés: a blokk a tartalmával együtt törlődik.
   A középső szöveges nézet mindig a blokkokkal egyező kódot mutatja.
3. ▶ Futtatás (F5): lassított, animált futás az elejétől.
   ⏭ Nyomkövetés (F10): soronként lép, kiemeli a sort, mutatja a változókat.
   ■ Leállítás (Esc).
   Minden futás visszaállítja a térképet és a robotot; a napló felülíródik.
4. Kézi vezérlés: fordulás, lépés, bányászás – megszakítja a futást, nem naplóz.

Térkép: világos mező = felfedezett (járt rajta vagy isThere nézte),
szürke = feltérképezetlen. A kék szaggatott keret a szenzor mezője."""

NYELV_SUGO = """MineScript röviden

step forward V   – V mezőt lép előre (falnál megáll: E_BEDROCK_HIT)
turn by V        – V negyedfordulat BALRA
mine here        – arany kibányászása (ha nincs: E_NO_GOLD)
print V          – érték kiírása a konzolra
set X to KIF     – KIF: V | isThere V | V op V | not V
                   op: + - * = <> < <= > >= and or
if V / else      – elágazás,  while V – ciklus (max. 3 szint mélyen)

V: változónév, 0–100 közötti szám, true vagy false.
isThere 0/1/2: üres / fal / arany van-e a robot előtt.
Típusok: egész és logikai; a változó típusa az első set-nél rögzül.
Legfeljebb 1000 sor hajtható végre egy futás alatt."""


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


class Foablak(tk.Tk):
    """Az alkalmazás főablaka."""

    def __init__(self, be_utvonal: str | None, ki_utvonal: str | None) -> None:
        super().__init__()
        self.title(ABLAK_CIM)
        self.geometry("1440x880")
        self.minsize(1150, 720)
        self.naplo_utvonal = ki_utvonal or ALAP_NAPLO
        self.fajl_utvonal: str | None = None
        self.alap_vilag = beolvas_szoveg(ALAP_BEMENET).vilag
        self.vilag = self.alap_vilag.masolat()
        self.program: list[Utasitas] = []
        self.futtato: Futtato | None = None
        self.lepesek = None
        self.mod = Mod.ALL
        self._idozito: str | None = None
        self._menusor()
        self._eszkoztar()
        self._allapotsor()
        self._fo_terulet()
        self._billentyuk()
        self.protocol("WM_DELETE_WINDOW", self._kilepes)
        if be_utvonal:
            self.betolt(be_utvonal)
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)

    # ---------- Felépítés ----------

    def _menusor(self) -> None:
        menusor = tk.Menu(self)
        fajl = tk.Menu(menusor, tearoff=False)
        fajl.add_command(label="Megnyitás…", accelerator="Ctrl+O", command=self._megnyitas)
        fajl.add_command(label="Mentés", accelerator="Ctrl+S", command=self._mentes)
        fajl.add_command(label="Mentés másként…", command=self._mentes_maskent)
        fajl.add_command(label="Napló helye…", command=self._naplo_hely)
        fajl.add_separator()
        fajl.add_command(label="Kilépés", command=self._kilepes)
        futas = tk.Menu(menusor, tearoff=False)
        futas.add_command(label="Futtatás", accelerator="F5", command=self.futtatas)
        futas.add_command(label="Nyomkövetés / következő lépés", accelerator="F10", command=self.nyomkovetes)
        futas.add_command(label="Leállítás", accelerator="Esc", command=self.leallitas)
        sugo = tk.Menu(menusor, tearoff=False)
        sugo.add_command(label="Gyors kezdés", accelerator="F1",
                         command=lambda: messagebox.showinfo("Súgó", GYORS_SUGO, parent=self))
        sugo.add_command(label="A MineScript nyelv",
                         command=lambda: messagebox.showinfo("MineScript", NYELV_SUGO, parent=self))
        menusor.add_cascade(label="Fájl", menu=fajl)
        menusor.add_cascade(label="Futtatás", menu=futas)
        menusor.add_cascade(label="Súgó", menu=sugo)
        self.configure(menu=menusor)

    def _eszkoztar(self) -> None:
        sav = ttk.Frame(self, padding=(6, 4))
        sav.pack(side="top", fill="x")
        self.futtat_gomb = ttk.Button(sav, text="▶ Futtatás (F5)", command=self.futtatas)
        self.lepes_gomb = ttk.Button(sav, text="⏭ Nyomkövetés (F10)", command=self.nyomkovetes, width=24)
        self.leallit_gomb = ttk.Button(sav, text="■ Leállítás (Esc)", command=self.leallitas)
        for gomb in (self.futtat_gomb, self.lepes_gomb, self.leallit_gomb):
            gomb.pack(side="left", padx=3)
        Tooltip(self.futtat_gomb, "Lassított, animált futtatás az elejétől (térkép és robot visszaáll).")
        Tooltip(self.lepes_gomb, "Soronkénti végrehajtás: minden kattintás egy sort futtat. "
                "Animált futás közben szünetel és nyomkövetésre vált.")
        Tooltip(self.leallit_gomb, "Az aktuális futás leállítása.")
        ttk.Label(sav, text="   Animáció késleltetése:").pack(side="left")
        self.kesleltetes = tk.IntVar(value=KESLELTETES_ALAP_MS)
        ttk.Scale(sav, from_=KESLELTETES_MIN_MS, to=KESLELTETES_MAX_MS, variable=self.kesleltetes,
                  length=160).pack(side="left")
        ttk.Label(sav, text="(gyors ↔ lassú)").pack(side="left")
        ttk.Button(sav, text="? Súgó (F1)",
                   command=lambda: messagebox.showinfo("Súgó", GYORS_SUGO, parent=self)).pack(side="right")
        self.naplo_cimke = ttk.Label(sav, text="", foreground="#555555")
        self.naplo_cimke.pack(side="right", padx=8)

    def _allapotsor(self) -> None:
        self.allapot_cimke = tk.Label(self, text="", anchor="w", font=("Segoe UI", 11, "bold"),
                                      foreground="white", background=SZIN_INFO, padx=8, pady=4)
        self.allapot_cimke.pack(side="bottom", fill="x")
        self._allapot("Kész. Szerkeszd a programot a blokkszerkesztőben, majd indítsd el (F5 / F10).", SZIN_INFO)

    def _fo_terulet(self) -> None:
        tabla = ttk.PanedWindow(self, orient="horizontal")
        tabla.pack(fill="both", expand=True, padx=4, pady=2)
        self.szerkeszto = Blokkszerkeszto(tabla, self.program, self._program_valtozott,
                                          self._kijeloles_valtozott)
        tabla.add(self.szerkeszto, weight=3)
        kozep = ttk.PanedWindow(tabla, orient="vertical")
        self.kodnezet = Kodnezet(kozep, self._kod_kattintas)
        kozep.add(self.kodnezet, weight=3)
        kozep.add(self._valtozotabla(kozep), weight=1)
        tabla.add(kozep, weight=2)
        jobb = ttk.Frame(tabla)
        self.szimulator = SzimulatorNezet(jobb, self.kezi_parancs)
        self.szimulator.pack(fill="x")
        self._also_fulek(jobb)
        tabla.add(jobb, weight=3)

    def _valtozotabla(self, szulo: tk.Misc) -> ttk.LabelFrame:
        keret = ttk.LabelFrame(szulo, text="Változók")
        self.valtozo_fa = ttk.Treeview(keret, columns=("nev", "tipus", "ertek"), show="headings", height=6)
        for oszlop, felirat, szelesseg in (("nev", "Név", 110), ("tipus", "Típus", 70), ("ertek", "Érték", 80)):
            self.valtozo_fa.heading(oszlop, text=felirat)
            self.valtozo_fa.column(oszlop, width=szelesseg)
        self.valtozo_fa.pack(fill="both", expand=True)
        return keret

    def _also_fulek(self, szulo: tk.Misc) -> None:
        fulek = ttk.Notebook(szulo)
        fulek.pack(fill="both", expand=True, pady=(4, 0))
        self.konzol = self._szovegdoboz(fulek)
        self.naplo_szoveg = self._szovegdoboz(fulek)
        fulek.add(self.konzol.master, text="Konzol (kimenet és hibák)")
        fulek.add(self.naplo_szoveg.master, text="Napló")
        self.konzol.tag_configure("hiba", foreground=SZIN_HIBA, font=("Consolas", 10, "bold"))
        self.konzol.tag_configure("ok", foreground=SZIN_OK, font=("Consolas", 10, "bold"))
        self.konzol.tag_configure("info", foreground="#757575")

    def _szovegdoboz(self, szulo: tk.Misc) -> tk.Text:
        keret = ttk.Frame(szulo)
        doboz = tk.Text(keret, height=8, font=("Consolas", 10), state="disabled", wrap="word")
        gorgeto = ttk.Scrollbar(keret, orient="vertical", command=doboz.yview)
        doboz.configure(yscrollcommand=gorgeto.set)
        doboz.pack(side="left", fill="both", expand=True)
        gorgeto.pack(side="right", fill="y")
        return doboz

    def _billentyuk(self) -> None:
        self.bind("<F5>", lambda _e: self.futtatas())
        self.bind("<F10>", lambda _e: (self.nyomkovetes(), "break")[1])
        self.bind("<Escape>", lambda _e: self.leallitas())
        self.bind("<F1>", lambda _e: messagebox.showinfo("Súgó", GYORS_SUGO, parent=self))
        self.bind("<Control-o>", lambda _e: self._megnyitas())
        self.bind("<Control-s>", lambda _e: self._mentes())

    # ---------- Kijelzések ----------

    def _allapot(self, szoveg: str, szin: str) -> None:
        self.allapot_cimke.configure(text=szoveg, background=szin)
        self.naplo_cimke.configure(text=f"Naplófájl: {self.naplo_utvonal}")

    def _szoveg_ir(self, doboz: tk.Text, szoveg: str, cimke: str = "") -> None:
        doboz.configure(state="normal")
        doboz.insert("end", szoveg + "\n", cimke)
        doboz.see("end")
        doboz.configure(state="disabled")

    def _szoveg_torol(self, doboz: tk.Text) -> None:
        doboz.configure(state="normal")
        doboz.delete("1.0", "end")
        doboz.configure(state="disabled")

    def _valtozok_frissit(self) -> None:
        self.valtozo_fa.delete(*self.valtozo_fa.get_children())
        if self.futtato is None:
            return
        for nev, ertek in self.futtato.valtozok.items():
            tipus = "logikai" if type(ertek) is bool else "egész"
            self.valtozo_fa.insert("", "end", values=(nev, tipus, ertek_szoveg(ertek)))

    def _gombok_frissit(self) -> None:
        feliratok = {Mod.ALL: "⏭ Nyomkövetés (F10)", Mod.NYOMKOVETES: "⏭ Következő lépés (F10)",
                     Mod.FUTAS: "⏸ Szünet → nyomkövetés (F10)"}
        self.lepes_gomb.configure(text=feliratok[self.mod])
        self.leallit_gomb.configure(state="disabled" if self.mod is Mod.ALL else "normal")

    def _kiemeles_torol(self) -> None:
        self.kodnezet.kiemel(None)
        self.szerkeszto.kiemel_sorszam(None)

    # ---------- Program és kijelölés szinkron ----------

    def _program_valtozott(self) -> None:
        """Bármely szerkesztés után: futás leáll, sorszámok, szöveges nézet, blokkok frissülnek."""
        self.leallit(csendes=True)
        sorszamoz(self.program)
        self.kodnezet.megjelenit(program_sorai(self.program))
        self.szerkeszto.frissit()
        self._kijeloles_valtozott(self.szerkeszto.kijelolt)

    def _kijeloles_valtozott(self, utasitas: Utasitas | None) -> None:
        self.kodnezet.kijelol(blokk_sorszamai(utasitas) if utasitas is not None else [])

    def _kod_kattintas(self, sorszam: int) -> None:
        self.szerkeszto.kijelol_sorszam(sorszam)

    # ---------- Futtatás ----------

    def futtatas(self) -> None:
        self._indit(Mod.FUTAS)
        self._utemez()

    def nyomkovetes(self) -> None:
        if self.mod is Mod.FUTAS:
            self._idozito_torol()
            self.mod = Mod.NYOMKOVETES
            self._allapot("Szünet – nyomkövetés: F10 = következő sor.", SZIN_FUT)
            self._gombok_frissit()
            return
        if self.mod is Mod.ALL:
            self._indit(Mod.NYOMKOVETES)
        self._egy_lepes()

    def leallitas(self) -> None:
        self.leallit(csendes=False)

    def _indit(self, mod: Mod) -> None:
        self.leallit(csendes=True)
        self.vilag = self.alap_vilag.masolat()
        self._szoveg_torol(self.konzol)
        self._szoveg_torol(self.naplo_szoveg)
        self.futtato = Futtato(self.program, self.vilag, kiiro=lambda s: self._szoveg_ir(self.konzol, s))
        self.lepesek = self.futtato.lepesek()
        self.mod = mod
        self._valtozok_frissit()
        self.szimulator.rajzol(self.vilag)
        self._allapot(f"Fut ({mod.value})…", SZIN_FUT)
        self._gombok_frissit()

    def _utemez(self) -> None:
        self._idozito = self.after(int(self.kesleltetes.get()), self._animacio_lepes)

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
        self.kodnezet.kiemel(sor.sorszam, hibas=sor.hiba is not None)
        self.szerkeszto.kiemel_sorszam(sor.sorszam)
        self.szimulator.rajzol(self.vilag)
        self._valtozok_frissit()
        self._szoveg_ir(self.naplo_szoveg, sor.szoveg())
        if self.mod is Mod.NYOMKOVETES:
            self._allapot(f"Nyomkövetés: végrehajtva a(z) {sor.sorszam}. sor "
                          f"({self.futtato.feldolgozott}/{UTASITAS_LIMIT}). F10 = következő.", SZIN_FUT)

    def _befejez(self) -> None:
        futtato = self.futtato
        self._szoveg_torol(self.naplo_szoveg)
        self._szoveg_ir(self.naplo_szoveg, futtato.naplo.szoveg().rstrip("\n"))
        self._naplo_ment()
        self.mod = Mod.ALL
        self.lepesek = None
        self._gombok_frissit()
        if futtato.allapot is Vegallapot.HIBA:
            uzenet = (f"HIBA a(z) {futtato.hiba_sorszam}. sorban: {futtato.hiba.value} – "
                      f"{HIBA_LEIRASOK[futtato.hiba]}")
            self._szoveg_ir(self.konzol, uzenet, "hiba")
            self._allapot(uzenet, SZIN_HIBA)
            return
        self._kiemeles_torol()
        if futtato.allapot is Vegallapot.LIMIT:
            uzenet = f"LEÁLLT: {LIMIT_TULLEPES} – {LIMIT_LEIRAS}"
            self._szoveg_ir(self.konzol, uzenet, "hiba")
            self._allapot(uzenet, SZIN_HIBA)
            return
        uzenet = f"A program hibátlanul lefutott ({futtato.feldolgozott} sor). Arany: {self.vilag.arany_db}"
        self._szoveg_ir(self.konzol, uzenet, "ok")
        self._allapot(uzenet, SZIN_OK)

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
            self._allapot("Leállítva.", SZIN_INFO)

    # ---------- Kézi vezérlés ----------

    def kezi_parancs(self, parancs: str) -> None:
        if self.mod is not Mod.ALL:
            self.leallit(csendes=True)
            self._szoveg_ir(self.konzol, "A futás megszakadt (kézi vezérlés).", "info")
        if parancs == "alaphelyzet":
            self.vilag = self.alap_vilag.masolat()
            self._allapot("A térkép és a robot visszaállt a kiinduló állapotba.", SZIN_INFO)
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
                self._allapot("Kézi vezérlés: a robot előtt fal vagy a térkép széle van – nem lépett.", SZIN_FUT)
            else:
                self._allapot("Kézi vezérlés: ezen a mezőn nincs arany.", SZIN_FUT)
            return
        self._allapot("Kézi vezérlés végrehajtva.", SZIN_INFO)

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
        self.program = program
        self.szerkeszto.program_beallit(program)
        self._program_valtozott()
        self.szimulator.rajzol(self.vilag)
        self.title(f"{ABLAK_CIM} – {utvonal}")
        self._allapot(f"Betöltve: {utvonal}", SZIN_INFO)

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
        self._allapot(f"Mentve: {self.fajl_utvonal}", SZIN_OK)

    def _mentes_maskent(self) -> None:
        utvonal = filedialog.asksaveasfilename(parent=self, title="Mentés másként", defaultextension=".txt",
                                               filetypes=[("Szövegfájl", "*.txt")])
        if utvonal:
            self.fajl_utvonal = utvonal
            self._mentes()

    def _naplo_hely(self) -> None:
        utvonal = filedialog.asksaveasfilename(parent=self, title="Naplófájl helye", defaultextension=".txt",
                                               initialfile=self.naplo_utvonal, filetypes=[("Szövegfájl", "*.txt")])
        if utvonal:
            self.naplo_utvonal = utvonal
            self._allapot(f"A napló ide kerül: {utvonal}", SZIN_INFO)

    def _kilepes(self) -> None:
        self.leallit(csendes=True)
        self.destroy()


def inditas(be_utvonal: str | None, ki_utvonal: str | None) -> None:
    """Az IDE elindítása (a main.py hívja)."""
    ablak = Foablak(be_utvonal, ki_utvonal)
    ablak.mainloop()
