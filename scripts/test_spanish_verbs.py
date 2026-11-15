import unittest

from spanish_verbs import (
    english_base_forms,
    peel_clitics,
    tu_imperative_form,
    tu_present_forms,
    vos_imperative,
    vos_present,
)


class VosPresentTests(unittest.TestCase):
    def test_regular_verbs_take_stressed_endings(self):
        self.assertEqual(vos_present("hablar"), "hablás")
        self.assertEqual(vos_present("comer"), "comés")
        self.assertEqual(vos_present("vivir"), "vivís")

    def test_stem_changing_verbs_keep_the_infinitive_stem(self):
        self.assertEqual(vos_present("pensar"), "pensás")
        self.assertEqual(vos_present("poder"), "podés")
        self.assertEqual(vos_present("dormir"), "dormís")
        self.assertEqual(vos_present("pedir"), "pedís")

    def test_irregular_verbs(self):
        self.assertEqual(vos_present("ser"), "sos")
        self.assertEqual(vos_present("ir"), "vas")
        self.assertEqual(vos_present("estar"), "estás")
        self.assertEqual(vos_present("haber"), "has")

    def test_reflexive_verbs_keep_te(self):
        self.assertEqual(vos_present("sentarse"), "te sentás")
        self.assertEqual(vos_present("dormirse"), "te dormís")

    def test_accented_ir_verbs(self):
        self.assertEqual(vos_present("reír"), "reís")
        self.assertEqual(vos_present("oír"), "oís")


class VosImperativeTests(unittest.TestCase):
    def test_regular_commands_drop_r_and_stress_the_vowel(self):
        self.assertEqual(vos_imperative("hablar"), "hablá")
        self.assertEqual(vos_imperative("comer"), "comé")
        self.assertEqual(vos_imperative("escribir"), "escribí")

    def test_irregular_commands(self):
        self.assertEqual(vos_imperative("venir"), "vení")
        self.assertEqual(vos_imperative("decir"), "decí")
        self.assertEqual(vos_imperative("hacer"), "hacé")
        self.assertEqual(vos_imperative("ir"), "andá")
        self.assertEqual(vos_imperative("ser"), "sé")

    def test_reflexive_commands_attach_te_without_an_accent(self):
        self.assertEqual(vos_imperative("sentarse"), "sentate")
        self.assertEqual(vos_imperative("irse"), "andate")
        self.assertEqual(vos_imperative("levantarse"), "levantate")

    def test_attached_pronouns(self):
        self.assertEqual(vos_imperative("decir", ["me"]), "decime")
        self.assertEqual(vos_imperative("decir", ["me", "lo"]), "decímelo")


class TuFormTests(unittest.TestCase):
    def test_present_forms_including_stem_changes(self):
        self.assertEqual(tu_present_forms("hablar"), {"hablas"})
        self.assertEqual(tu_present_forms("pensar"), {"piensas"})
        self.assertEqual(tu_present_forms("dormir"), {"duermes"})
        self.assertEqual(tu_present_forms("pedir"), {"pides"})
        self.assertEqual(tu_present_forms("ser"), {"eres"})
        self.assertEqual(tu_present_forms("construir"), {"construyes"})

    def test_imperatives(self):
        self.assertEqual(tu_imperative_form("hablar"), "habla")
        self.assertEqual(tu_imperative_form("empezar"), "empieza")
        self.assertEqual(tu_imperative_form("hacer"), "haz")
        self.assertEqual(tu_imperative_form("sentarse"), "sienta")


class HelperTests(unittest.TestCase):
    def test_peel_clitics(self):
        self.assertIn(("escribe", ["me"]), peel_clitics("escribeme"))
        self.assertIn(("di", ["me", "lo"]), peel_clitics("dimelo"))

    def test_english_base_forms(self):
        self.assertEqual(english_base_forms("to take, to have"), {"take", "have"})
        self.assertEqual(english_base_forms("to look at (something)"), {"look"})


if __name__ == "__main__":
    unittest.main()
