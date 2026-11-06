"""Beolvasó, tokenizáló, elemző, kiíró, ellenőrző és szerkesztő tesztek."""

import contextlib
import io
import os
import tempfile
import unittest

from beolvaso import beolvas_szoveg, bemenet_szoveg
from main import csendes_futtatas, main
from nyelv.elemzo import elemez
from nyelv.ellenorzo import azonosito_hiba, ertek_hiba
from nyelv.kiiro import program_sorai, sorszamoz
from nyelv.szerkesztes import (
    BeszurasHelye, BlokkFajta, SzerkesztesiHiba, beszur, beszuras_hiba, torol,
)
from nyelv.tokenizalo import kulcsszo_e, tokenizal_sor
from nyelv.utasitasok import (
    Ciklus, Elagazas, ErtekFajta, Ertek, Ertekadas, IsThereKif, Muvelet, MuveletKif, NotKif,
)
from tesztek.segedlet import sorok
from terkep import Irany, Mezo


class BeolvasoTeszt(unittest.TestCase):
    def test_terkep_es_robot(self):
        bemenet = beolvas_szoveg("2 3\n.#@\nv..\nprint 1\n")
        terkep = bemenet.vilag.terkep
        self.assertEqual((terkep.sorok, terkep.oszlopok), (2, 3))
        self.assertEqual(terkep.mezo(0, 1), Mezo.FAL)
        self.assertEqual(terkep.mezo(0, 2), Mezo.ARANY)
        self.assertEqual(terkep.mezo(1, 0), Mezo.URES)
        robot = bemenet.vilag.robot
        self.assertEqual((robot.sor, robot.oszlop, robot.irany), (1, 0, Irany.DEL))
        self.assertEqual(bemenet.program_sorok, ["print 1"])

    def test_iranyok(self):
        for jel, irany in ((">", Irany.KELET), ("<", Irany.NYUGAT), ("^", Irany.ESZAK), ("v", Irany.DEL)):
            self.assertEqual(beolvas_szoveg(f"1 1\n{jel}\n").vilag.robot.irany, irany)

    def test_ures_program_es_crlf(self):
        bemenet = beolvas_szoveg("1 2\r\n>.\r\n")
        self.assertEqual(bemenet.program_sorok, [])

    def test_visszairas(self):
        szoveg = "2 3\n.#@\nv..\nif true\n  print 1\n"
        bemenet = beolvas_szoveg(szoveg)
        self.assertEqual(bemenet_szoveg(bemenet.vilag, bemenet.program_sorok), szoveg)

    def test_terkepen_kivul_fal(self):
        terkep = beolvas_szoveg("1 1\n>\n").vilag.terkep
        self.assertEqual(terkep.mezo(-1, 0), Mezo.FAL)
        self.assertEqual(terkep.mezo(0, 1), Mezo.FAL)


class TokenizaloTeszt(unittest.TestCase):
    def test_behuzas_es_tokenek(self):
        sor = tokenizal_sor("   set x to a + 1", 4)
        self.assertEqual((sor.sorszam, sor.behuzas), (4, 3))
        self.assertEqual(sor.tokenek, ["set", "x", "to", "a", "+", "1"])

    def test_kulcsszavak_minden_alakban(self):
        for szo in ("while", "WHILE", "While", "isThere", "isthere", "ISTHERE", "To", "bY"):
            self.assertTrue(kulcsszo_e(szo), szo)
        self.assertFalse(kulcsszo_e("arany"))

    def test_ertek_fajta(self):
        self.assertEqual(Ertek("12").fajta, ErtekFajta.SZAM)
        self.assertEqual(Ertek("true").fajta, ErtekFajta.LOGIKAI)
        self.assertEqual(Ertek("True").fajta, ErtekFajta.AZONOSITO)
        self.assertEqual(Ertek("a1").fajta, ErtekFajta.AZONOSITO)


class ElemzoTeszt(unittest.TestCase):
    def test_kifejezesek(self):
        program = elemez(["set a to isThere 2", "set b to not a", "set c to 1 <= x"])
        self.assertIsInstance(program[0].kif, IsThereKif)
        self.assertIsInstance(program[1].kif, NotKif)
        self.assertEqual(program[2].kif, MuveletKif(Ertek("1"), Muvelet.KISEBB_EGYENLO, Ertek("x")))

    def test_blokkok_es_sorszamok(self):
        program = elemez(sorok("while a", "  if b", "      print 1", "  else", "   print 2",
                               "  print 3", "print 4").splitlines())
        self.assertEqual(len(program), 2)
        ciklus = program[0]
        self.assertIsInstance(ciklus, Ciklus)
        elagazas = ciklus.torzs[0]
        self.assertIsInstance(elagazas, Elagazas)
        self.assertEqual((elagazas.sorszam, elagazas.else_sorszam), (2, 4))
        self.assertEqual(elagazas.hamis_ag[0].sorszam, 5)
        self.assertEqual(ciklus.torzs[1].sorszam, 6)
        self.assertEqual(program[1].sorszam, 7)

    def test_kiiro_visszaalakit(self):
        forras = sorok("set a to 0", "set b to a < 3", "while b", "  if b", "    print a", "  else",
                       "    turn by 1", "  set a to a + 1", "step forward 2", "mine here").splitlines()
        self.assertEqual(program_sorai(elemez(forras)), forras)

    def test_sorszamoz(self):
        program = elemez(["if true", "  print 1", "else", "  print 2", "print 3"])
        program.insert(0, Ertekadas("x", MuveletKif(Ertek("1"), Muvelet.PLUSZ, Ertek("2"))))
        sorszamoz(program)
        self.assertEqual(program[1].sorszam, 2)
        self.assertEqual(program[1].else_sorszam, 4)
        self.assertEqual(program[2].sorszam, 6)


class EllenorzoTeszt(unittest.TestCase):
    def test_ervenyes_azonositok(self):
        for nev in ("a", "arany", "x1", "Count", "megy2b"):
            self.assertIsNone(azonosito_hiba(nev), nev)

    def test_ervenytelen_azonositok(self):
        for nev in ("", "9lives", "while", "While", "ISTHERE", "a_b", "a b", "árvíz", "x-1"):
            self.assertIsNotNone(azonosito_hiba(nev), nev)

    def test_ertekek(self):
        for szoveg in ("0", "100", "true", "false", "abc"):
            self.assertIsNone(ertek_hiba(szoveg), szoveg)
        for szoveg in ("101", "-1", "True", "", "if"):
            self.assertIsNotNone(ertek_hiba(szoveg), szoveg)


class SzerkesztesTeszt(unittest.TestCase):
    def test_beszuras_ele_moge_torzsbe(self):
        program = []
        ciklus = beszur(program, None, BeszurasHelye.MOGE, BlokkFajta.AMIG)
        beszur(program, ciklus, BeszurasHelye.ELE, BlokkFajta.ERTEKADAS)
        beszur(program, ciklus, BeszurasHelye.MOGE, BlokkFajta.KIIRAS)
        beszur(program, ciklus, BeszurasHelye.TORZSBE, BlokkFajta.LEPES)
        self.assertEqual(program_sorai(program),
                         ["set x to 0", "while false", "  step forward 1", "print 0"])

    def test_else_ag(self):
        program = []
        ha = beszur(program, None, BeszurasHelye.MOGE, BlokkFajta.HA_KULONBEN)
        beszur(program, ha, BeszurasHelye.ELSE_AGBA, BlokkFajta.BANYASZAS)
        beszur(program, ha, BeszurasHelye.TORZSBE, BlokkFajta.FORDULAS)
        self.assertEqual(program_sorai(program), ["if true", "  turn by 1", "else", "  mine here"])
        egyszeru = beszur(program, None, BeszurasHelye.MOGE, BlokkFajta.HA)
        with self.assertRaises(SzerkesztesiHiba):
            beszur(program, egyszeru, BeszurasHelye.ELSE_AGBA, BlokkFajta.KIIRAS)

    def test_torzsbe_csak_vezerlobe(self):
        program = []
        kiiras = beszur(program, None, BeszurasHelye.MOGE, BlokkFajta.KIIRAS)
        self.assertIsNotNone(beszuras_hiba(program, kiiras, BeszurasHelye.TORZSBE, BlokkFajta.KIIRAS))

    def test_melysegi_korlat(self):
        program = []
        kulso = beszur(program, None, BeszurasHelye.MOGE, BlokkFajta.AMIG)
        kozep = beszur(program, kulso, BeszurasHelye.TORZSBE, BlokkFajta.HA)
        belso = beszur(program, kozep, BeszurasHelye.TORZSBE, BlokkFajta.HA)
        kiiras = beszur(program, belso, BeszurasHelye.TORZSBE, BlokkFajta.KIIRAS)
        with self.assertRaises(SzerkesztesiHiba):
            beszur(program, belso, BeszurasHelye.TORZSBE, BlokkFajta.AMIG)
        with self.assertRaises(SzerkesztesiHiba):
            beszur(program, kiiras, BeszurasHelye.MOGE, BlokkFajta.HA)
        beszur(program, kiiras, BeszurasHelye.MOGE, BlokkFajta.KIIRAS)
        self.assertIsNone(beszuras_hiba(program, belso, BeszurasHelye.MOGE, BlokkFajta.HA))

    def test_torles_tartalommal(self):
        program = elemez(["while true", "  if true", "    print 1", "print 2"])
        torol(program, program[0])
        self.assertEqual(program_sorai(program), ["print 2"])


class CsendesModTeszt(unittest.TestCase):
    def test_q_mod_fajlt_ir(self):
        with tempfile.TemporaryDirectory() as mappa:
            be = os.path.join(mappa, "input_001.txt")
            ki = os.path.join(mappa, "output_001.txt")
            with open(be, "w", encoding="utf-8") as fajl:
                fajl.write("1 2\n>@\nstep forward 1\nmine here\n")
            self.assertEqual(main(["-q", be, ki]), 0)
            with open(ki, encoding="utf-8") as fajl:
                self.assertEqual(fajl.read(), "1 step forward 1\n2 mine here\nEOR\n")

    def test_napló_felulirodik(self):
        with tempfile.TemporaryDirectory() as mappa:
            be = os.path.join(mappa, "be.txt")
            ki = os.path.join(mappa, "ki.txt")
            with open(ki, "w", encoding="utf-8") as fajl:
                fajl.write("régi tartalom\n" * 50)
            with open(be, "w", encoding="utf-8") as fajl:
                fajl.write("1 1\n>\n")
            csendes_futtatas(be, ki)
            with open(ki, encoding="utf-8") as fajl:
                self.assertEqual(fajl.read(), "EOR\n")

    def test_hibas_parameterszam(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["-q", "csak_egy"]), 2)


if __name__ == "__main__":
    unittest.main()
