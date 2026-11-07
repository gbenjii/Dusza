"""Sortörő elrendezés: az elemek balról jobbra sorakoznak, ami már nem fér ki, új sorba kerül.

A `pack(side="left")` keskeny ablakban egyszerűen levágja a sor végét (eltűnő gombok,
félbevágott feliratok). Ez a keret minden átméretezéskor újraszámolja a sorokat,
és a saját magasságát is ehhez igazítja.

A gyerekeket a Tk saját `place_configure`-jával helyezzük el valódi képpontokban
(a customtkinter `place`-e a koordinátákat még egyszer skálázná, szélességet pedig
nem fogad el), így nagyított (pl. 125%-os) Windowson is pontos.
"""

from __future__ import annotations

import tkinter as tk


class FolyoKeret(tk.Frame):
    """`hozzaad`-dal felvett gyerekek sortöréses elrendezése.

    kitolt=True: minden sor elemei arányosan kinyúlnak a teljes szélességre
    (pl. egyforma széles információs kártyák).
    """

    def __init__(self, master, hatter: str, vizszintes_koz: int = 6, fuggoleges_koz: int = 6,
                 kitolt: bool = False) -> None:
        super().__init__(master, background=hatter, height=1, borderwidth=0, highlightthickness=0)
        self._hkoz = vizszintes_koz
        self._fkoz = fuggoleges_koz
        self._kitolt = kitolt
        self._elemek: list[tuple[tk.Misc, int]] = []
        self._utemezve = False
        self.bind("<Configure>", lambda _e: self._atrendez(), add="+")

    def hozzaad(self, elem: tk.Misc, plusz_koz: int = 0) -> tk.Misc:
        """Új elem a sor végére; `plusz_koz`: ennyivel nagyobb hely előtte (csoportok között)."""
        self._elemek.append((elem, plusz_koz))
        elem.bind("<Configure>", lambda _e: self.ujrarendez(), add="+")
        self.ujrarendez()
        return elem

    def ujrarendez(self) -> None:
        """Átrendezés a következő üresjáratban (pl. ha egy gomb felirata megváltozott)."""
        if not self._utemezve:
            self._utemezve = True
            self.after_idle(self._atrendez)

    def _atrendez(self) -> None:
        self._utemezve = False
        szelesseg = self.winfo_width()
        if szelesseg <= 1 or not self._elemek:
            return
        sorok: list[list[tuple[tk.Misc, int, int]]] = []
        sor: list[tuple[tk.Misc, int, int]] = []
        x = 0
        for elem, plusz in self._elemek:
            szel = elem.winfo_reqwidth()
            koz = self._hkoz + plusz if sor else 0
            if sor and x + koz + szel > szelesseg:
                sorok.append(sor)
                sor, x, koz = [], 0, 0
            sor.append((elem, koz, szel))
            x += koz + szel
        if sor:
            sorok.append(sor)
        y = 0
        for sor in sorok:
            magassag = max(elem.winfo_reqheight() for elem, _k, _s in sor)
            hasznalt = sum(koz + szel for _e, koz, szel in sor)
            plusz_szel = (szelesseg - hasznalt) / len(sor) if self._kitolt else 0
            x = 0.0
            for elem, koz, szel in sor:
                x += koz
                elem_mag = elem.winfo_reqheight()
                opciok = {"x": round(x), "y": y + (magassag - elem_mag) // 2}
                if self._kitolt:
                    opciok["width"] = round(szel + plusz_szel)
                tk.Place.place_configure(elem, **opciok)
                x += szel + plusz_szel
            y += magassag + self._fkoz
        uj_magassag = max(y - self._fkoz, 1)
        if int(self.cget("height")) != uj_magassag:
            self.configure(height=uj_magassag)
