"""A MineScript program végrehajtása soronként, generátorral.

A `Futtato.lepesek()` minden végrehajtott forrássor után visszaad egy
`NaploSor`-t. A -q mód, az animált futás és a nyomkövetés is erre épül.
A futtató nem tud a felületről: a kiírást egy opcionális függvény kapja meg.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from enum import Enum
from functools import partial

from hibak import FutasiHiba, HibaKod
from naplo import Naplo, NaploSor, ertek_szoveg
from nyelv.utasitasok import (
    EGESZ_OPERANDUSU, LOGIKAI_OPERANDUSU, Banyaszas, Ciklus, Elagazas, Ertek,
    ErtekFajta, Ertekadas, ErtekKif, Fordulas, IsThereKif, Kifejezes, Kiiras,
    Lepes, Muvelet, MuveletKif, NotKif, Utasitas,
)
from terkep import Mezo, Vilag

UTASITAS_LIMIT = 1000
"""Legfeljebb ennyi forrássor dolgozható fel egy futás során."""

ISTHERE_KODOK = tuple(mezo.value for mezo in Mezo)

ErtekTipus = int | bool


class Vegallapot(Enum):
    """Hol tart / hogyan ért véget a futás."""

    FUT = "fut"
    RENDBEN = "rendben"
    HIBA = "hiba"
    LIMIT = "limit"


class _Leallas(Exception):
    """Belső jelzés: hiba miatt le kell állni."""


class _LimitTullepes(Exception):
    """Belső jelzés: elfogyott az utasításkeret."""


def egesz_e(ertek: ErtekTipus) -> bool:
    return type(ertek) is int


def logikai_e(ertek: ErtekTipus) -> bool:
    return type(ertek) is bool


def szamol(muvelet: Muvelet, bal: ErtekTipus, jobb: ErtekTipus) -> ErtekTipus:
    """Egy már típusellenőrzött kétoperandusú művelet eredménye."""
    match muvelet:
        case Muvelet.PLUSZ:
            return bal + jobb
        case Muvelet.MINUSZ:
            return bal - jobb
        case Muvelet.SZOR:
            return bal * jobb
        case Muvelet.EGYENLO:
            return bal == jobb
        case Muvelet.NEM_EGYENLO:
            return bal != jobb
        case Muvelet.KISEBB:
            return bal < jobb
        case Muvelet.KISEBB_EGYENLO:
            return bal <= jobb
        case Muvelet.NAGYOBB:
            return bal > jobb
        case Muvelet.NAGYOBB_EGYENLO:
            return bal >= jobb
        case Muvelet.ES:
            return bal and jobb
        case Muvelet.VAGY:
            return bal or jobb
    raise ValueError(muvelet)


class Futtato:
    """Egy program egyszeri végrehajtása egy világon."""

    def __init__(self, program: list[Utasitas], vilag: Vilag,
                 kiiro: Callable[[str], None] | None = None) -> None:
        self.program = program
        self.vilag = vilag
        self.valtozok: dict[str, ErtekTipus] = {}
        self.kimenet: list[str] = []
        self.naplo = Naplo()
        self.feldolgozott = 0
        self.allapot = Vegallapot.FUT
        self.hiba: HibaKod | None = None
        self.hiba_sorszam: int | None = None
        self._kiiro = kiiro

    # ---------- Nyilvános felület ----------

    def lepesek(self) -> Iterator[NaploSor]:
        """Soronként végrehajtja a programot; minden sor után visszaadja a naplósort."""
        try:
            yield from self._blokk(self.program)
            self.allapot = Vegallapot.RENDBEN
        except _Leallas:
            self.allapot = Vegallapot.HIBA
        except _LimitTullepes:
            self.allapot = Vegallapot.LIMIT
        if self.allapot is Vegallapot.LIMIT:
            self.naplo.lezar_limit()
        else:
            self.naplo.lezar_eor()

    def futtat_vegig(self) -> None:
        """Felület nélküli futtatás a végéig."""
        for _ in self.lepesek():
            pass

    # ---------- Vezérlés ----------

    def _blokk(self, utasitasok: list[Utasitas]) -> Iterator[NaploSor]:
        for utasitas in utasitasok:
            if isinstance(utasitas, Ciklus):
                yield from self._ciklus(utasitas)
            elif isinstance(utasitas, Elagazas):
                yield from self._elagazas(utasitas)
            else:
                yield from self._sor(utasitas.sorszam, partial(self._egyszeru, utasitas))

    def _ciklus(self, ciklus: Ciklus) -> Iterator[NaploSor]:
        while True:
            feltetel = yield from self._sor(ciklus.sorszam, partial(self._feltetel, ciklus.feltetel))
            if not feltetel:
                return
            yield from self._blokk(ciklus.torzs)

    def _elagazas(self, elagazas: Elagazas) -> Iterator[NaploSor]:
        feltetel = yield from self._sor(elagazas.sorszam, partial(self._feltetel, elagazas.feltetel))
        if feltetel:
            yield from self._blokk(elagazas.igaz_ag)
        elif elagazas.hamis_ag is not None:
            yield from self._sor(elagazas.else_sorszam, self._semmi)
            yield from self._blokk(elagazas.hamis_ag)

    def _sor(self, sorszam: int, muvelet: Callable[[NaploSor], object]):
        """Egy forrássor feldolgozása: naplósor készítése, hiba esetén leállás."""
        if self.feldolgozott >= UTASITAS_LIMIT:
            raise _LimitTullepes()
        self.feldolgozott += 1
        sor = NaploSor(sorszam)
        try:
            eredmeny = muvelet(sor)
        except FutasiHiba as hiba:
            sor.hiba = hiba.kod
            self.hiba = hiba.kod
            self.hiba_sorszam = sorszam
            self.naplo.hozzaad(sor)
            yield sor
            raise _Leallas() from hiba
        self.naplo.hozzaad(sor)
        yield sor
        return eredmeny

    def _semmi(self, _sor: NaploSor) -> None:
        """Az else sora: nincs teendő, csak naplózódik."""

    def _feltetel(self, ertek: Ertek, _sor: NaploSor) -> bool:
        feltetel = self._olvas(ertek)
        if not logikai_e(feltetel):
            raise FutasiHiba(HibaKod.E_NON_BOOL_CONDITION)
        return feltetel

    # ---------- Egyszerű utasítások ----------

    def _egyszeru(self, utasitas: Utasitas, sor: NaploSor) -> None:
        if isinstance(utasitas, Lepes):
            sor.hozzaad("step forward")
            self.vilag.lep(self._nemnegativ_param(utasitas.ertek, sor))
        elif isinstance(utasitas, Fordulas):
            sor.hozzaad("turn by")
            self.vilag.fordul(self._nemnegativ_param(utasitas.ertek, sor))
        elif isinstance(utasitas, Banyaszas):
            sor.hozzaad("mine here")
            self.vilag.banyasz()
        elif isinstance(utasitas, Kiiras):
            sor.hozzaad("print")
            self._kiir(ertek_szoveg(self._api_param(utasitas.ertek, sor)))
        elif isinstance(utasitas, Ertekadas):
            self._ertekad(utasitas.nev, self._kifejezes(utasitas.kif, sor))

    def _kiir(self, szoveg: str) -> None:
        self.kimenet.append(szoveg)
        if self._kiiro is not None:
            self._kiiro(szoveg)

    def _ertekad(self, nev: str, ertek: ErtekTipus) -> None:
        """Az első értékadás rögzíti a változó típusát."""
        if nev in self.valtozok and type(self.valtozok[nev]) is not type(ertek):
            raise FutasiHiba(HibaKod.E_TYPE_MISMATCH)
        self.valtozok[nev] = ertek

    # ---------- API-paraméterek ----------

    def _api_param(self, ertek: Ertek, sor: NaploSor) -> ErtekTipus:
        """Kiértékeli a paramétert és a naplósorba írja (ha inicializált)."""
        kiertekelt = self._olvas(ertek)
        sor.hozzaad(ertek_szoveg(kiertekelt))
        return kiertekelt

    def _nemnegativ_param(self, ertek: Ertek, sor: NaploSor) -> int:
        kiertekelt = self._api_param(ertek, sor)
        if not egesz_e(kiertekelt) or kiertekelt < 0:
            raise FutasiHiba(HibaKod.E_BAD_ARG)
        return kiertekelt

    def _is_there(self, ertek: Ertek, sor: NaploSor) -> bool:
        sor.hozzaad("isThere")
        kod = self._api_param(ertek, sor)
        if not egesz_e(kod) or kod not in ISTHERE_KODOK:
            raise FutasiHiba(HibaKod.E_BAD_ARG)
        eredmeny = self.vilag.megnez(kod)
        sor.hozzaad(ertek_szoveg(eredmeny))
        return eredmeny

    # ---------- Kifejezések ----------

    def _olvas(self, ertek: Ertek) -> ErtekTipus:
        """Egy V token értéke; nem inicializált változónál E_UNINITIALIZED."""
        fajta = ertek.fajta
        if fajta is ErtekFajta.SZAM:
            return int(ertek.szoveg)
        if fajta is ErtekFajta.LOGIKAI:
            return ertek.szoveg == "true"
        if ertek.szoveg not in self.valtozok:
            raise FutasiHiba(HibaKod.E_UNINITIALIZED)
        return self.valtozok[ertek.szoveg]

    def _kifejezes(self, kif: Kifejezes, sor: NaploSor) -> ErtekTipus:
        if isinstance(kif, ErtekKif):
            return self._olvas(kif.ertek)
        if isinstance(kif, IsThereKif):
            return self._is_there(kif.ertek, sor)
        if isinstance(kif, NotKif):
            ertek = self._olvas(kif.ertek)
            self._megkovetel(logikai_e, ertek)
            return not ertek
        return self._muvelet(kif)

    def _muvelet(self, kif: MuveletKif) -> ErtekTipus:
        """Balról jobbra: minden operandust beolvasás után azonnal ellenőriz."""
        bal = self._olvas(kif.bal)
        if kif.muvelet in EGESZ_OPERANDUSU:
            self._megkovetel(egesz_e, bal)
            jobb = self._olvas(kif.jobb)
            self._megkovetel(egesz_e, jobb)
        elif kif.muvelet in LOGIKAI_OPERANDUSU:
            self._megkovetel(logikai_e, bal)
            jobb = self._olvas(kif.jobb)
            self._megkovetel(logikai_e, jobb)
        else:
            jobb = self._olvas(kif.jobb)
            if type(bal) is not type(jobb):
                raise FutasiHiba(HibaKod.E_BAD_OPERAND)
        return szamol(kif.muvelet, bal, jobb)

    @staticmethod
    def _megkovetel(feltetel: Callable[[ErtekTipus], bool], ertek: ErtekTipus) -> None:
        if not feltetel(ertek):
            raise FutasiHiba(HibaKod.E_BAD_OPERAND)
