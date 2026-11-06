"""Programsorok → utasításfa. A blokkokat a behúzás határozza meg."""

from __future__ import annotations

from nyelv.tokenizalo import TokenSor, tokenizal
from nyelv.utasitasok import (
    Banyaszas, Ciklus, Elagazas, Ertek, Ertekadas, ErtekKif, Fordulas,
    IsThereKif, Kifejezes, Kiiras, Lepes, Muvelet, MuveletKif, NotKif, Utasitas,
)


class ElemzesiHiba(Exception):
    """Szintaktikailag hibás program (helyes bemenetnél nem fordul elő)."""


def elemez(sorok: list[str]) -> list[Utasitas]:
    """A program sorait utasításfává alakítja."""
    elemzo = _Elemzo(tokenizal(sorok))
    return elemzo.program()


def kifejezes_elemez(tokenek: list[str]) -> Kifejezes:
    """A set jobb oldalának elemzése (a 'to' utáni tokenek)."""
    if len(tokenek) == 1:
        return ErtekKif(Ertek(tokenek[0]))
    if len(tokenek) == 2 and tokenek[0] == "isThere":
        return IsThereKif(Ertek(tokenek[1]))
    if len(tokenek) == 2 and tokenek[0] == "not":
        return NotKif(Ertek(tokenek[1]))
    if len(tokenek) == 3:
        return MuveletKif(Ertek(tokenek[0]), Muvelet(tokenek[1]), Ertek(tokenek[2]))
    raise ElemzesiHiba(f"Érvénytelen kifejezés: {' '.join(tokenek)}")


class _Elemzo:
    """Rekurzív elemző: a `pozicio` a következő feldolgozandó sor indexe."""

    def __init__(self, sorok: list[TokenSor]) -> None:
        self.sorok = sorok
        self.pozicio = 0

    def program(self) -> list[Utasitas]:
        if not self.sorok:
            return []
        utasitasok = self.blokk(self.sorok[0].behuzas)
        if self.pozicio < len(self.sorok):
            hibas = self.sorok[self.pozicio].sorszam
            raise ElemzesiHiba(f"Hibás behúzás a(z) {hibas}. sorban.")
        return utasitasok

    def _aktualis(self) -> TokenSor | None:
        if self.pozicio < len(self.sorok):
            return self.sorok[self.pozicio]
        return None

    def blokk(self, behuzas: int) -> list[Utasitas]:
        """Az azonos behúzású, egymást követő utasítások."""
        utasitasok: list[Utasitas] = []
        sor = self._aktualis()
        while sor is not None and sor.behuzas == behuzas and sor.tokenek[0] != "else":
            utasitasok.append(self.utasitas())
            sor = self._aktualis()
        return utasitasok

    def torzs(self, fej_behuzas: int) -> list[Utasitas]:
        """Egy vezérlőblokk törzse: a fejnél beljebb kezdődő blokk."""
        sor = self._aktualis()
        if sor is None or sor.behuzas <= fej_behuzas:
            return []
        return self.blokk(sor.behuzas)

    def utasitas(self) -> Utasitas:
        sor = self.sorok[self.pozicio]
        self.pozicio += 1
        tokenek = sor.tokenek
        kulcsszo = tokenek[0]
        if kulcsszo == "step":
            return Lepes(Ertek(tokenek[2]), sor.sorszam)
        if kulcsszo == "turn":
            return Fordulas(Ertek(tokenek[2]), sor.sorszam)
        if kulcsszo == "mine":
            return Banyaszas(sor.sorszam)
        if kulcsszo == "print":
            return Kiiras(Ertek(tokenek[1]), sor.sorszam)
        if kulcsszo == "set":
            return Ertekadas(tokenek[1], kifejezes_elemez(tokenek[3:]), sor.sorszam)
        if kulcsszo == "if":
            return self.elagazas(sor)
        if kulcsszo == "while":
            return Ciklus(Ertek(tokenek[1]), self.torzs(sor.behuzas), sor.sorszam)
        raise ElemzesiHiba(f"Ismeretlen utasítás a(z) {sor.sorszam}. sorban: {kulcsszo}")

    def elagazas(self, fej: TokenSor) -> Elagazas:
        elagazas = Elagazas(Ertek(fej.tokenek[1]), self.torzs(fej.behuzas), None, fej.sorszam)
        sor = self._aktualis()
        if sor is not None and sor.behuzas == fej.behuzas and sor.tokenek[0] == "else":
            self.pozicio += 1
            elagazas.else_sorszam = sor.sorszam
            elagazas.hamis_ag = self.torzs(fej.behuzas)
        return elagazas
