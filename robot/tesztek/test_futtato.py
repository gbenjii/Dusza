"""A futtató és a napló tesztjei: szemantika, hibák, naplózási határesetek."""

import unittest

from futtato import UTASITAS_LIMIT, Vegallapot
from hibak import LIMIT_TULLEPES, HibaKod
from tesztek.segedlet import futtat, naplo, sorok
from terkep import Irany


class FeladatPeldaTeszt(unittest.TestCase):
    def test_feladat_peldaja(self):
        program = sorok(
            "set arany to isThere 2", "set count to 0", "turn by 0", "print arany",
            "if false", "  print 1", "else", "  set x to isThere 3", "print 9",
        )
        self.assertEqual(
            naplo(program),
            ["1 isThere 2 false", "2", "3 turn by 0", "4 print false", "5", "7",
             "8 isThere 3 E_BAD_ARG", "EOR"],
        )

    def test_ures_program_csak_eor(self):
        self.assertEqual(naplo(""), ["EOR"])

    def test_nincs_szokoz_a_sor_vegen(self):
        for sor in naplo(sorok("set a to 1", "print a", "mine here")):
            self.assertEqual(sor, sor.strip())
            self.assertNotIn("  ", sor)


class BemutatoTeszt(unittest.TestCase):
    TERKEP = ("5 10\n.#..@..#.@\n.#.##.##..\n>.@.@@.@.#\n##.#..#.#.\n.@..#..@..\n")
    PROGRAM = sorok(
        "set count to 0", "set megy to true", "while megy",
        "  set arany to isThere 2", "  if arany", "    step forward 1",
        "    mine here", "    set count to count + 1", "  else",
        "    step forward 1", "  set fal to isThere 1", "  set megy to not fal",
        "print count",
    )

    def test_bemutato_program(self):
        futtato = futtat(self.PROGRAM, self.TERKEP)
        self.assertEqual(futtato.allapot, Vegallapot.RENDBEN)
        self.assertEqual(futtato.kimenet, ["4"])
        self.assertEqual(futtato.vilag.arany_db, 4)
        self.assertEqual((futtato.vilag.robot.sor, futtato.vilag.robot.oszlop), (2, 8))
        napl = futtato.naplo.sorok
        self.assertEqual(napl[:8], ["1", "2", "3", "4 isThere 2 false", "5", "9",
                                    "10 step forward 1", "11 isThere 1 false"])
        self.assertEqual(napl[-4:], ["12", "3", "13 print 4", "EOR"])


class RobotApiTeszt(unittest.TestCase):
    def test_lepes_falnal_megall(self):
        futtato = futtat(sorok("step forward 5"), "1 4\n>.#.\n")
        self.assertEqual(futtato.naplo.sorok, ["1 step forward 5 E_BEDROCK_HIT", "EOR"])
        self.assertEqual(futtato.vilag.robot.oszlop, 1)

    def test_lepes_terkep_szelen(self):
        futtato = futtat(sorok("step forward 3"))
        self.assertEqual(futtato.naplo.sorok, ["1 step forward 3 E_BEDROCK_HIT", "EOR"])
        self.assertEqual(futtato.vilag.robot.oszlop, 2)

    def test_lepes_nulla_es_pontos(self):
        futtato = futtat(sorok("step forward 0", "step forward 2"))
        self.assertEqual(futtato.naplo.sorok, ["1 step forward 0", "2 step forward 2", "EOR"])
        self.assertEqual(futtato.vilag.robot.oszlop, 2)

    def test_atlepett_aranyat_nem_veszi_fel(self):
        futtato = futtat(sorok("step forward 2", "turn by 2", "step forward 1", "mine here"),
                         "1 3\n>@.\n")
        self.assertEqual(futtato.vilag.arany_db, 1)
        self.assertEqual(futtato.naplo.sorok[-2:], ["4 mine here", "EOR"])

    def test_fordulas_balra(self):
        varhato = {0: Irany.KELET, 1: Irany.ESZAK, 2: Irany.NYUGAT, 3: Irany.DEL, 4: Irany.KELET,
                   5: Irany.ESZAK, 100: Irany.KELET}
        for n, irany in varhato.items():
            with self.subTest(n=n):
                self.assertEqual(futtat(sorok(f"turn by {n}")).vilag.robot.irany, irany)

    def test_fordulas_hibas_parameter(self):
        self.assertEqual(naplo(sorok("turn by true")), ["1 turn by true E_BAD_ARG", "EOR"])
        self.assertEqual(naplo(sorok("set n to 0 - 1", "turn by n")),
                         ["1", "2 turn by -1 E_BAD_ARG", "EOR"])

    def test_lepes_hibas_parameter(self):
        self.assertEqual(naplo(sorok("step forward false")), ["1 step forward false E_BAD_ARG", "EOR"])
        self.assertEqual(naplo(sorok("set n to 2 - 5", "step forward n")),
                         ["1", "2 step forward -3 E_BAD_ARG", "EOR"])
        self.assertEqual(naplo(sorok("step forward n")), ["1 step forward E_UNINITIALIZED", "EOR"])

    def test_banyaszas(self):
        futtato = futtat(sorok("step forward 1", "mine here", "mine here"), "1 3\n>@.\n")
        self.assertEqual(futtato.naplo.sorok,
                         ["1 step forward 1", "2 mine here", "3 mine here E_NO_GOLD", "EOR"])
        self.assertEqual(futtato.vilag.arany_db, 1)

    def test_bányászás_ures_mezon(self):
        self.assertEqual(naplo(sorok("mine here")), ["1 mine here E_NO_GOLD", "EOR"])

    def test_isthere_ertekek(self):
        program = sorok("set a to isThere 0", "set b to isThere 1", "set c to isThere 2",
                        "turn by 2", "set d to isThere 1", "set e to isThere 0")
        self.assertEqual(naplo(program, "1 3\n.>@\n"),
                         ["1 isThere 0 false", "2 isThere 1 false", "3 isThere 2 true", "4 turn by 2",
                          "5 isThere 1 false", "6 isThere 0 true", "EOR"])

    def test_isthere_terkepen_kivul_fal(self):
        self.assertEqual(naplo(sorok("turn by 1", "set f to isThere 1")),
                         ["1 turn by 1", "2 isThere 1 true", "EOR"])

    def test_isthere_hibas_parameter(self):
        self.assertEqual(naplo(sorok("set a to isThere 3")), ["1 isThere 3 E_BAD_ARG", "EOR"])
        self.assertEqual(naplo(sorok("set a to isThere true")), ["1 isThere true E_BAD_ARG", "EOR"])
        self.assertEqual(naplo(sorok("set a to isThere w")), ["1 isThere E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set w to 0 - 1", "set a to isThere w")),
                         ["1", "2 isThere -1 E_BAD_ARG", "EOR"])

    def test_isthere_tipushiba_ertekadasnal(self):
        self.assertEqual(naplo(sorok("set x to 1", "set x to isThere 2")),
                         ["1", "2 isThere 2 false E_TYPE_MISMATCH", "EOR"])

    def test_kiiras(self):
        futtato = futtat(sorok("print 5", "print true", "set a to 7", "print a", "print b"))
        self.assertEqual(futtato.naplo.sorok,
                         ["1 print 5", "2 print true", "3", "4 print 7", "5 print E_UNINITIALIZED", "EOR"])
        self.assertEqual(futtato.kimenet, ["5", "true", "7"])


class FelfedezesTeszt(unittest.TestCase):
    def test_felfedezett_mezok(self):
        futtato = futtat(sorok("step forward 1", "turn by 3", "set a to isThere 0"), "2 3\n>..\n...\n")
        self.assertEqual(futtato.vilag.felfedezett, {(0, 0), (0, 1), (1, 1)})

    def test_szenzor_nem_fedez_fel(self):
        futtato = futtat("", "1 3\n>..\n")
        futtato.vilag.szenzor()
        self.assertEqual(futtato.vilag.felfedezett, {(0, 0)})

    def test_terkepen_kivuli_isthere_nem_kerul_be(self):
        futtato = futtat(sorok("turn by 1", "set a to isThere 1"))
        self.assertEqual(futtato.vilag.felfedezett, {(0, 0)})


class TipusTeszt(unittest.TestCase):
    def test_tipus_rogzul(self):
        self.assertEqual(naplo(sorok("set x to 1", "set x to true")), ["1", "2 E_TYPE_MISMATCH", "EOR"])
        self.assertEqual(naplo(sorok("set x to true", "set x to 3")), ["1", "2 E_TYPE_MISMATCH", "EOR"])

    def test_azonos_tipus_felulirhato(self):
        futtato = futtat(sorok("set x to 1", "set x to x + 4", "print x"))
        self.assertEqual(futtato.kimenet, ["5"])

    def test_hibas_ertekadas_nem_hoz_letre_valtozot(self):
        futtato = futtat(sorok("set x to y"))
        self.assertNotIn("x", futtato.valtozok)

    def test_kis_nagybetu_erzekeny(self):
        futtato = futtat(sorok("set a to 1", "set A to true", "print a", "print A"))
        self.assertEqual(futtato.kimenet, ["1", "true"])

    def test_nem_inicializalt(self):
        self.assertEqual(naplo(sorok("set x to y + 1")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to y")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to not y")), ["1 E_UNINITIALIZED", "EOR"])


class MuveletTeszt(unittest.TestCase):
    def ertek(self, kif: str) -> str:
        futtato = futtat(sorok(f"set r to {kif}", "print r"))
        self.assertEqual(futtato.allapot, Vegallapot.RENDBEN, kif)
        return futtato.kimenet[0]

    def test_aritmetika(self):
        self.assertEqual(self.ertek("7 + 5"), "12")
        self.assertEqual(self.ertek("7 - 9"), "-2")
        self.assertEqual(self.ertek("100 * 100"), "10000")

    def test_osszehasonlitas(self):
        esetek = {"1 < 2": "true", "2 < 2": "false", "2 <= 2": "true", "3 > 2": "true",
                  "2 >= 3": "false", "4 = 4": "true", "4 <> 4": "false", "true = false": "false",
                  "true <> false": "true"}
        for kif, varhato in esetek.items():
            with self.subTest(kif=kif):
                self.assertEqual(self.ertek(kif), varhato)

    def test_logikai(self):
        esetek = {"true and false": "false", "true and true": "true", "false or true": "true",
                  "false or false": "false", "not true": "false", "not false": "true"}
        for kif, varhato in esetek.items():
            with self.subTest(kif=kif):
                self.assertEqual(self.ertek(kif), varhato)

    def test_ertek_kifejezes(self):
        self.assertEqual(self.ertek("42"), "42")
        self.assertEqual(self.ertek("false"), "false")

    def test_rossz_operandus(self):
        for kif in ("true + 1", "1 + true", "1 and true", "true or 0", "not 5",
                    "1 = true", "false <> 0", "true < 1", "3 >= false"):
            with self.subTest(kif=kif):
                self.assertEqual(naplo(sorok(f"set x to {kif}")), ["1 E_BAD_OPERAND", "EOR"])


class KiertekelesiSorrendTeszt(unittest.TestCase):
    """Balról jobbra, azonnali ellenőrzés, nincs rövidzár."""

    def test_bal_operandus_tipushibaja_elobb(self):
        self.assertEqual(naplo(sorok("set x to true + y")), ["1 E_BAD_OPERAND", "EOR"])
        self.assertEqual(naplo(sorok("set x to 5 and y")), ["1 E_BAD_OPERAND", "EOR"])

    def test_jobb_nem_inicializalt(self):
        self.assertEqual(naplo(sorok("set x to 1 + y")), ["1 E_UNINITIALIZED", "EOR"])

    def test_nincs_rovidzar(self):
        self.assertEqual(naplo(sorok("set x to true or c")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to false and c")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to true or 3")), ["1 E_BAD_OPERAND", "EOR"])

    def test_egyenloseg_masodik_utan_ellenoriz(self):
        self.assertEqual(naplo(sorok("set x to 1 = y")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to y = true")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("set x to true <> y")), ["1 E_UNINITIALIZED", "EOR"])


class VezerlesTeszt(unittest.TestCase):
    def test_if_igaz_else_nem_naplozodik(self):
        self.assertEqual(naplo(sorok("if true", "  print 1", "else", "  print 2", "print 3")),
                         ["1", "2 print 1", "5 print 3", "EOR"])

    def test_if_hamis_else_nelkul(self):
        self.assertEqual(naplo(sorok("if false", "  print 1", "print 3")), ["1", "3 print 3", "EOR"])

    def test_nem_logikai_feltetel(self):
        self.assertEqual(naplo(sorok("if 1", "  print 1")), ["1 E_NON_BOOL_CONDITION", "EOR"])
        self.assertEqual(naplo(sorok("set a to 0", "while a", "  print 1")),
                         ["1", "2 E_NON_BOOL_CONDITION", "EOR"])

    def test_nem_inicializalt_feltetel(self):
        self.assertEqual(naplo(sorok("if q", "  print 1")), ["1 E_UNINITIALIZED", "EOR"])
        self.assertEqual(naplo(sorok("while q", "  print 1")), ["1 E_UNINITIALIZED", "EOR"])

    def test_while_minden_kiertekeles_naplozodik(self):
        program = sorok("set i to 0", "set c to true", "while c", "  set i to i + 1",
                        "  set c to i < 2", "print i")
        self.assertEqual(naplo(program),
                         ["1", "2", "3", "4", "5", "3", "4", "5", "3", "6 print 2", "EOR"])

    def test_while_hamis_azonnal(self):
        self.assertEqual(naplo(sorok("while false", "  print 1", "print 2")), ["1", "3 print 2", "EOR"])

    def test_hiba_blokk_belsejeben_leallit(self):
        program = sorok("while true", "  if true", "    mine here", "  print 1", "print 2")
        self.assertEqual(naplo(program), ["1", "2", "3 mine here E_NO_GOLD", "EOR"])

    def test_harom_szint_kulonbozo_behuzassal(self):
        program = sorok("set c to true", "while c", "    if true", "     if c",
                        "      print 7", "     else", "         print 8", "    set c to false",
                        "print c")
        futtato = futtat(program)
        self.assertEqual(futtato.kimenet, ["7", "false"])
        self.assertEqual(futtato.naplo.sorok,
                         ["1", "2", "3", "4", "5 print 7", "8", "2", "9 print false", "EOR"])

    def test_valtozo_blokkon_kivul_is_el(self):
        futtato = futtat(sorok("if true", "  set z to 3", "print z"))
        self.assertEqual(futtato.kimenet, ["3"])


class LimitTeszt(unittest.TestCase):
    def test_vegtelen_ciklus(self):
        futtato = futtat(sorok("while true", "  print 1"))
        self.assertEqual(len(futtato.naplo.sorok), UTASITAS_LIMIT + 1)
        self.assertEqual(futtato.naplo.sorok[-1], LIMIT_TULLEPES)
        self.assertNotIn("EOR", futtato.naplo.sorok)
        self.assertEqual(futtato.allapot, Vegallapot.LIMIT)

    @staticmethod
    def szamlalo(n: int, *utana: str) -> str:
        """3n + 4 feldolgozott sort adó ciklus, utána további sorok."""
        return sorok("set d to 0", "set i to 0", "set c to true", "while c",
                     "  set i to i + 1", f"  set c to i < {n}", *utana)

    def test_pontosan_1000_sor_meg_belefer(self):
        futtato = futtat(self.szamlalo(332))
        self.assertEqual(len(futtato.naplo.sorok), UTASITAS_LIMIT + 1)
        self.assertEqual(futtato.naplo.sorok[-1], "EOR")

    def test_1001_sor_mar_limit(self):
        futtato = futtat(self.szamlalo(333))
        self.assertEqual(len(futtato.naplo.sorok), UTASITAS_LIMIT + 1)
        self.assertEqual(futtato.naplo.sorok[-1], LIMIT_TULLEPES)

    def test_hiba_az_1000_soron_eor(self):
        # 997 + 2 sor rendben, az 1000. hibás → EOR, nem limit
        futtato = futtat(self.szamlalo(331, "print 0", "print 0", "mine here"))
        self.assertEqual(futtato.naplo.sorok[-2:], ["9 mine here E_NO_GOLD", "EOR"])
        self.assertEqual(len(futtato.naplo.sorok), UTASITAS_LIMIT + 1)


class HibaAllapotTeszt(unittest.TestCase):
    def test_hiba_adatai(self):
        futtato = futtat(sorok("print 1", "mine here", "print 2"))
        self.assertEqual(futtato.allapot, Vegallapot.HIBA)
        self.assertEqual(futtato.hiba, HibaKod.E_NO_GOLD)
        self.assertEqual(futtato.hiba_sorszam, 2)

    def test_lepesek_generator(self):
        from beolvaso import beolvas_szoveg
        from futtato import Futtato
        from nyelv.elemzo import elemez
        bemenet = beolvas_szoveg("1 3\n>..\n" + sorok("step forward 1", "print 2"))
        futtato = Futtato(elemez(bemenet.program_sorok), bemenet.vilag)
        lepesek = futtato.lepesek()
        self.assertEqual(next(lepesek).szoveg(), "1 step forward 1")
        self.assertEqual(futtato.vilag.robot.oszlop, 1)
        self.assertEqual(next(lepesek).szoveg(), "2 print 2")
        self.assertEqual(list(lepesek), [])
        self.assertEqual(futtato.naplo.sorok[-1], "EOR")


if __name__ == "__main__":
    unittest.main()
