import unittest

from second_person import Lexicon, convert_sentence

LEXICON = Lexicon()
for infinitive, gloss in {
    "hablar": "to speak", "escribir": "to write", "sentar": "to sit (down)", "lavar": "to wash",
    "comer": "to eat", "pensar": "to think", "mirar": "to look at", "cerrar": "to close", "beber": "to drink",
    "divertir": "to amuse", "bailar": "to dance",
}.items():
    LEXICON.add(infinitive, gloss)
for infinitive, gloss in {"ser": "to be", "estar": "to be", "ir": "to go", "tener": "to have", "hacer": "to do", "venir": "to come", "poder": "can"}.items():
    LEXICON.add(infinitive, gloss)


def run(spanish, english):
    return convert_sentence(spanish, english, LEXICON)


class TuToVosTests(unittest.TestCase):
    def test_pronoun_and_verb(self):
        outcome = run("¿Hablas tú español?", "Do you speak Spanish?")
        self.assertEqual((outcome.status, outcome.spanish), ("converted", "¿Hablás vos español?"))

    def test_irregular_and_stem_changing_verbs(self):
        self.assertEqual(run("Tú eres alto.", "You are tall.").spanish, "Vos sos alto.")
        self.assertEqual(run("¿Piensas en mí?", "Do you think of me?").spanish, "¿Pensás en mí?")
        self.assertEqual(run("¿Puedes venir?", "Can you come?").spanish, "¿Podés venir?")

    def test_tu_forms_that_equal_vos_are_kept(self):
        outcome = run("¿Estás cansado?", "Are you tired?")
        self.assertEqual((outcome.status, outcome.spanish), ("unchanged", "¿Estás cansado?"))
        self.assertEqual(run("¿Qué comiste?", "What did you eat?").status, "unchanged")

    def test_contigo_becomes_con_vos(self):
        self.assertEqual(run("Quiero ir contigo.", "I want to go with you.").spanish, "Quiero ir con vos.")

    def test_present_of_iar_verbs_is_not_mistaken_for_imperfect(self):
        lexicon = Lexicon()
        lexicon.add("enviar", "to send")
        outcome = convert_sentence("¿Tú envías la carta?", "Do you send the letter?", lexicon)
        self.assertEqual(outcome.status, "dropped")

    def test_unknown_verb_is_dropped_not_guessed(self):
        outcome = run("¿Cuánto cobras?", "How much do you charge?")
        self.assertEqual((outcome.status, outcome.reason), ("dropped", "unverified_second_person"))

    def test_formal_sentences_are_untouched(self):
        self.assertEqual(run("¿Habla Ud. español?", "Do you speak Spanish?").status, "unchanged")

    def test_nouns_that_look_like_tu_verbs_are_not_converted(self):
        outcome = run("Las cuentas son altas.", "The bills are high.")
        self.assertEqual(outcome.status, "unchanged")

    def test_sentences_without_you_are_unchanged(self):
        self.assertEqual(run("Te veo mañana.", "I see you tomorrow.").status, "unchanged")


class ImperativeTests(unittest.TestCase):
    def test_tu_commands_become_vos_commands(self):
        self.assertEqual(run("Escribe la carta.", "Write the letter.").spanish, "Escribí la carta.")
        self.assertEqual(run("Ven acá.", "Come here.").spanish, "Vení acá.")
        self.assertEqual(run("Haz tu tarea.", "Do your homework.").spanish, "Hacé tu tarea.")

    def test_attached_pronouns(self):
        self.assertEqual(run("Escríbeme la carta.", "Write the letter to me.").spanish, "Escribime la carta.")
        self.assertEqual(run("Lávate las manos.", "Wash your hands.").spanish, "Lavate las manos.")
        self.assertEqual(run("Siéntate aquí.", "Sit down here.").spanish, "Sentate aquí.")

    def test_statements_that_look_like_commands_are_kept(self):
        self.assertEqual(run("Come mucho.", "He eats a lot.").status, "unchanged")
        self.assertEqual(run("Se lo doy.", "I give it to him.").status, "unchanged")

    def test_command_with_unknown_verb_and_pronoun_is_dropped(self):
        self.assertEqual(run("Cuéntame la historia.", "Tell me the story.").status, "dropped")

    def test_nosotros_commands_are_not_mistaken_for_tu_commands(self):
        self.assertEqual(run("Comprémoselo.", "Let's buy it for her.").status, "unchanged")

    def test_formal_commands_are_untouched(self):
        self.assertEqual(run("Escriba la carta.", "Write the letter.").status, "unchanged")


class VosotrosTests(unittest.TestCase):
    def test_regular_present_becomes_ustedes(self):
        outcome = run("Vosotros habláis español.", "You all speak Spanish.")
        self.assertEqual((outcome.status, outcome.spanish), ("converted", "Ustedes hablan español."))

    def test_commands_and_possessives(self):
        self.assertEqual(run("Mirad.", "Look.").spanish, "Miren.")
        self.assertEqual(run("No bailéis aquí.", "Don't dance here.").spanish, "No bailen aquí.")
        self.assertEqual(run("Vuestro amigo es alto.", "Your friend is tall.").spanish, "Su amigo es alto.")

    def test_uncertain_vosotros_is_dropped(self):
        for spanish, english in [
            ("Cerrad la puerta.", "Close the door."),
            ("Os veo mañana.", "I see you tomorrow."),
            ("Los amigos vuestros viven aquí.", "Your friends live here."),
            ("Divertíos mucho.", "Have a good time."),
            ("Leedlo.", "Read it."),
            ("Vosotros sois estudiantes.", "You all are students."),
            ("Vosotros vivís en Madrid.", "You all live in Madrid."),
        ]:
            self.assertEqual(run(spanish, english).status, "dropped", spanish)


class WordCardTests(unittest.TestCase):
    def test_pronouns_after_prepositions_and_alone(self):
        from second_person import convert_word_card as convert
        self.assertEqual(convert("tú"), "vos")
        self.assertEqual(convert("según tú"), "según vos")
        self.assertEqual(convert("para ti"), "para vos")
        self.assertEqual(convert("vosotros"), "ustedes")
        self.assertEqual(convert("entre vosotras y yo"), "entre ustedes y yo")

    def test_contigo_and_unsafe_cards_stay(self):
        from second_person import convert_word_card as convert
        self.assertEqual(convert("contigo"), "contigo")
        self.assertEqual(convert("tú eres"), "tú eres")
        self.assertEqual(convert("el vuestro"), "el vuestro")

    def test_possessive_and_os(self):
        from second_person import convert_word_card as convert
        self.assertEqual(convert("vuestro amigo"), "su amigo")
        self.assertEqual(convert("os"), "se")
        self.assertEqual(convert("os lo, os la"), "se lo, se la")
        self.assertEqual(convert("os los, os las"), "se los, se las")


if __name__ == "__main__":
    unittest.main()
