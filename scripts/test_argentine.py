import unittest

from argentine import argentinize


class ArgentineMapTests(unittest.TestCase):
    def test_simple_nouns_and_plurals(self):
        self.assertEqual(argentinize("el coche"), "el auto")
        self.assertEqual(argentinize("los coches rojos"), "los autos rojos")
        self.assertEqual(argentinize("las patatas"), "las papas")
        self.assertEqual(argentinize("el zumo de naranja"), "el jugo de naranja")
        self.assertEqual(argentinize("Mi falda es azul."), "Mi pollera es azul.")
        self.assertEqual(argentinize("el autobús"), "el colectivo")

    def test_gender_change_flips_the_article(self):
        self.assertEqual(argentinize("Compro un ordenador."), "Compro una computadora.")
        self.assertEqual(argentinize("del ordenador"), "de la computadora")
        self.assertEqual(argentinize("Los aguacates"), "Las paltas")

    def test_gender_change_is_skipped_when_an_adjective_would_disagree(self):
        self.assertEqual(argentinize("un ordenador nuevo"), "un ordenador nuevo")
        self.assertEqual(argentinize("mi ordenador es nuevo"), "mi ordenador es nuevo")

    def test_gender_tags_follow_a_gender_change(self):
        self.assertEqual(argentinize("el aguacate (m.)"), "la palta (f.)")

    def test_verbs_follow_the_whole_conjugation(self):
        self.assertEqual(argentinize("Quiero conducir."), "Quiero manejar.")
        self.assertEqual(argentinize("Ella conduce rápido."), "Ella maneja rápido.")
        self.assertEqual(argentinize("Cojo un resfriado."), "Agarro un resfriado.")

    def test_coger_with_transport_becomes_tomar(self):
        self.assertEqual(argentinize("Quiero coger el autobús."), "Quiero tomar el colectivo.")

    def test_unrelated_text_is_untouched(self):
        self.assertEqual(argentinize("Hola, ¿cómo estás?"), "Hola, ¿cómo estás?")


if __name__ == "__main__":
    unittest.main()
