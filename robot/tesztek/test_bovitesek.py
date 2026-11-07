"""Az élő napló, az előjelzés, a tömeges mód, a példák és a térképszerkesztés tesztjei."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from beolvaso import beolvas_szoveg
from futtato import Futtato, SorElott, Vegallapot
from main import kimenet_neve, main, mappa_futtatas
from naplo import Naplo, NaploSor
from nyelv.elemzo import elemez
from peldaprogramok import PELDAK, TERKEP_VIDEO
from tesztek.segedlet import sorok
from terkep import Irany, Mezo


def futtato_keszit(szoveg: str, naplo: Naplo | None = None) -> Futtato:
    bemenet = beolvas_szoveg(szoveg)
    return Futtato(elemez(bemenet.program_sorok), bemenet.vilag, naplo=naplo)


class EloNaploTeszt(unittest.TestCase):
    def test_soronkent_kerul_a_fajlba(self):
        with tempfile.TemporaryDirectory() as mappa:
            ut = os.path.join(mappa, "naplo.txt")
            futtato = futtato_keszit("1 3\n>..\n" + sorok("step forward 1", "print 1", "turn by 1"),
                                     Naplo(elo_fajl=ut))
            lepesek = futtato.lepesek()
            next(lepesek)
            with open(ut, encoding="utf-8") as fajl:
                self.assertEqual(fajl.read(), "1 step forward 1\n")
            next(lepesek)
            with open(ut, encoding="utf-8") as fajl:
                self.assertEqual(fajl.read(), "1 step forward 1\n2 print 1\n")
            list(lepesek)
            with open(ut, encoding="utf-8") as fajl:
                self.assertEqual(fajl.read(), "1 step forward 1\n2 print 1\n3 turn by 1\nEOR\n")

    def test_felulirja_a_regit(self):
        with tempfile.TemporaryDirectory() as mappa:
            ut = os.path.join(mappa, "naplo.txt")
            Path(ut).write_text("régi\n" * 10, encoding="utf-8")
            naplo = Naplo(elo_fajl=ut)
            self.assertEqual(Path(ut).read_text(encoding="utf-8"), "")
            naplo.hozzaad(NaploSor(1))
            naplo.bezar()
            self.assertEqual(Path(ut).read_text(encoding="utf-8"), "1\n")

    def test_megszakitott_futas_reszleges_naplo(self):
        with tempfile.TemporaryDirectory() as mappa:
            ut = os.path.join(mappa, "naplo.txt")
            naplo = Naplo(elo_fajl=ut)
            futtato = futtato_keszit("1 1\n>\n" + sorok("while true", "  print 1"), naplo)
            lepesek = futtato.lepesek()
            for _ in range(3):
                next(lepesek)
            lepesek.close()
            naplo.bezar()
            self.assertEqual(Path(ut).read_text(encoding="utf-8"), "1\n2 print 1\n1\n")


class ElojelzesTeszt(unittest.TestCase):
    def test_sor_elott_esemenyek(self):
        futtato = futtato_keszit("1 3\n>..\n" + sorok("if true", "  print 1", "else", "  print 2"))
        esemenyek = list(futtato.lepesek(elore_jelez=True))
        tipusok = [(type(e).__name__, e.sorszam) for e in esemenyek]
        self.assertEqual(tipusok, [("SorElott", 1), ("NaploSor", 1), ("SorElott", 2), ("NaploSor", 2)])
        self.assertEqual(futtato.naplo.sorok, ["1", "2 print 1", "EOR"])

    def test_elojelzes_nelkul_nincs_sor_elott(self):
        futtato = futtato_keszit("1 3\n>..\n" + sorok("print 1"))
        self.assertFalse(any(isinstance(e, SorElott) for e in futtato.lepesek()))

    def test_limitnel_nincs_1001_elojelzes(self):
        futtato = futtato_keszit("1 1\n>\n" + sorok("while true", "  print 1"))
        esemenyek = list(futtato.lepesek(elore_jelez=True))
        self.assertEqual(sum(isinstance(e, SorElott) for e in esemenyek), 1000)
        self.assertEqual(futtato.allapot, Vegallapot.LIMIT)


class TomegesModTeszt(unittest.TestCase):
    def test_mappa_minden_fajl(self):
        with tempfile.TemporaryDirectory() as mappa:
            for szam, program in (("001", "print 1\n"), ("002", "mine here\n"), ("010", "")):
                Path(mappa, f"input_{szam}.txt").write_text("1 2\n>.\n" + program, encoding="utf-8")
            self.assertEqual(mappa_futtatas(mappa), (3, 0))
            self.assertEqual(Path(mappa, "output_001.txt").read_text(encoding="utf-8"), "1 print 1\nEOR\n")
            self.assertEqual(Path(mappa, "output_002.txt").read_text(encoding="utf-8"),
                             "1 mine here E_NO_GOLD\nEOR\n")
            self.assertEqual(Path(mappa, "output_010.txt").read_text(encoding="utf-8"), "EOR\n")

    def test_kimenet_neve(self):
        self.assertEqual(kimenet_neve(Path("a/input_042.txt")), Path("a/output_042.txt"))

    def test_main_m_kapcsolo(self):
        with tempfile.TemporaryDirectory() as mappa:
            Path(mappa, "input_001.txt").write_text("1 1\n>\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["-m", mappa]), 0)
            self.assertTrue(Path(mappa, "output_001.txt").exists())


class PeldaTeszt(unittest.TestCase):
    def futtat(self, nev_resz: str) -> Futtato:
        pelda = next(p for p in PELDAK if nev_resz in p.nev)
        futtato = futtato_keszit(pelda.szoveg)
        futtato.futtat_vegig()
        return futtato

    def test_minden_pelda_betoltheto(self):
        for pelda in PELDAK:
            with self.subTest(pelda=pelda.nev):
                futtato_keszit(pelda.szoveg).futtat_vegig()

    def test_aranygyujtes(self):
        self.assertEqual(self.futtat("egyenesen").kimenet, ["4"])

    def test_bemutato_palya_minden_arany(self):
        futtato = self.futtat("mind a 8 arany")
        self.assertEqual(futtato.allapot, Vegallapot.RENDBEN)
        self.assertEqual(futtato.vilag.arany_db, 8)
        self.assertEqual(futtato.naplo.sorok[-1], "EOR")

    def test_bemutato_terkep_egyezik_az_input_video_fajllal(self):
        fajl = Path(__file__).resolve().parent.parent / "input_video.txt"
        terkep = fajl.read_text(encoding="utf-8").splitlines()[:6]
        self.assertEqual(TERKEP_VIDEO, "".join(sor + "\n" for sor in terkep))

    def test_korbejaras(self):
        futtato = self.futtat("Körbejárás")
        self.assertEqual(futtato.allapot, Vegallapot.RENDBEN)
        self.assertEqual(futtato.kimenet, ["5"])

    def test_limit_es_hiba(self):
        self.assertEqual(self.futtat("korlát").allapot, Vegallapot.LIMIT)
        hibas = self.futtat("Futási hiba")
        self.assertEqual(hibas.naplo.sorok[-2:], ["6 step forward 3 E_BEDROCK_HIT", "EOR"])

    def test_feladat_naplopelda(self):
        self.assertEqual(self.futtat("naplópéldája").naplo.sorok,
                         ["1 isThere 2 false", "2", "3 turn by 0", "4 print false", "5", "7",
                          "8 isThere 3 E_BAD_ARG", "EOR"])


class VilagBovitesTeszt(unittest.TestCase):
    def test_utvonal_es_statisztika(self):
        futtato = futtato_keszit("1 4\n>.@.\n" + sorok("step forward 2", "mine here", "turn by 2"))
        futtato.futtat_vegig()
        vilag = futtato.vilag
        self.assertEqual(vilag.utvonal, [(0, 1), (0, 2)])
        self.assertEqual(vilag.nyomvonal, [(0, 0), (0, 1), (0, 2)])
        self.assertEqual((vilag.lepesszam, vilag.fordulasszam), (2, 1))
        self.assertEqual(vilag.kibanyaszott, {(0, 2)})
        self.assertEqual(vilag.osszes_arany(), 1)

    def test_iranyvaltas_nelkuli_fordulas_nem_szamit(self):
        futtato = futtato_keszit("1 2\n>.\n" + sorok("turn by 0", "turn by 4", "turn by 1", "turn by 3"))
        futtato.futtat_vegig()
        self.assertEqual(futtato.vilag.fordulasszam, 2)

    def test_reszleges_lepes_utvonala(self):
        futtato = futtato_keszit("1 3\n>..\n" + sorok("step forward 5"))
        futtato.futtat_vegig()
        self.assertEqual(futtato.vilag.utvonal, [(0, 1), (0, 2)])

    def test_mezo_szerkesztes(self):
        vilag = beolvas_szoveg("2 2\n>.\n..\n").vilag
        self.assertTrue(vilag.mezo_szerkeszt(1, 1, Mezo.FAL))
        self.assertFalse(vilag.mezo_szerkeszt(0, 0, Mezo.ARANY))  # a robot mezője
        self.assertFalse(vilag.mezo_szerkeszt(5, 5, Mezo.FAL))
        self.assertEqual(vilag.terkep_sorai(), [">.", ".#"])

    def test_robot_athelyez_es_forgat(self):
        vilag = beolvas_szoveg("2 2\n>@\n..\n").vilag
        self.assertTrue(vilag.robot_athelyez(0, 1))
        self.assertEqual(vilag.terkep_sorai(), [".>", ".."])
        vilag.robot_athelyez(0, 1)
        self.assertEqual(vilag.robot.irany, Irany.ESZAK)

    def test_atmeretezes(self):
        vilag = beolvas_szoveg("2 3\n.#>\n@..\n").vilag
        kisebb = vilag.atmeretezve(1, 2)
        self.assertEqual(kisebb.terkep_sorai(), [".>"])
        nagyobb = vilag.atmeretezve(3, 4)
        self.assertEqual(nagyobb.terkep_sorai(), [".#>.", "@...", "...."])
        self.assertEqual(vilag.atmeretezve(99, 0).terkep.oszlopok, 1)


if __name__ == "__main__":
    unittest.main()
