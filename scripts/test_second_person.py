import unittest

from second_person import Lexicon, convert_sentence

LEXICON = Lexicon()
for infinitive, gloss in {
    "hablar": "to speak", "escribir": "to write", "sentar": "to sit (down)", "lavar": "to wash",
    "comer": "to eat", "pensar": "to think", "mirar": "to look at", "cerrar": "to close", "beber": "to drink",
    "divertir": "to amuse", "bailar": "to dance", "cantar": "to sing", "pintar": "to paint", "dormir": "to sleep",
}.items():
    LEXICON.add(infinitive, gloss)
for infinitive, gloss in {"ser": "to be", "estar": "to be", "ir": "to go", "tener": "to have", "hacer": "to do", "venir": "to come", "poder": "can"}.items():
    LEXICON.add(infinitive, gloss)


def run(spanish, english):
    return convert_sentence(spanish, english, LEXICON)


class TuToVosTests(unittest.TestCase):
    def test_pronoun_and_verb(self):
        outcome = run("¿Cantas tú bien?", "Do you sing well?")
        self.assertEqual((outcome.status, outcome.spanish), ("converted", "¿Cantás vos bien?"))

    def test_irregular_and_stem_changing_verbs(self):
        self.assertEqual(run("Tú eres un dragón.", "You are a dragon.").spanish, "Vos sos un dragón.")
        self.assertEqual(run("¿Pensás en mí?", "Do you think of me?").spanish, "¿Pensás en mí?")
        self.assertEqual(run("¿Puedes volar?", "Can you fly?").spanish, "¿Podés volar?")

    def test_tu_forms_that_equal_vos_are_kept(self):
        outcome = run("¿Estás mojado?", "Are you wet?")
        self.assertEqual((outcome.status, outcome.spanish), ("unchanged", "¿Estás mojado?"))
        self.assertEqual(run("¿Qué pintaste?", "What did you paint?").status, "unchanged")

    def test_contigo_becomes_con_vos(self):
        self.assertEqual(run("Quiero bailar contigo.", "I want to dance with you.").spanish, "Quiero bailar con vos.")

    def test_present_of_iar_verbs_is_not_mistaken_for_imperfect(self):
        lexicon = Lexicon()
        lexicon.add("enviar", "to send")
        outcome = convert_sentence("¿Tú envías la carta?", "Do you send the letter?", lexicon)
        self.assertEqual(outcome.status, "dropped")

    def test_unknown_verb_is_dropped_not_guessed(self):
        outcome = run("¿Cuánto pesas?", "How much do you weigh?")
        self.assertEqual((outcome.status, outcome.reason), ("dropped", "unverified_second_person"))

    def test_formal_sentences_are_untouched(self):
        self.assertEqual(run("¿Canta Ud. bien?", "Do you sing well?").status, "unchanged")

    def test_nouns_that_look_like_tu_verbs_are_not_converted(self):
        outcome = run("Las cuerdas son largas.", "The ropes are long.")
        self.assertEqual(outcome.status, "unchanged")

    def test_sentences_without_you_are_unchanged(self):
        self.assertEqual(run("Te pinto mañana.", "I paint you tomorrow.").status, "unchanged")


class ImperativeTests(unittest.TestCase):
    def test_tu_commands_become_vos_commands(self):
        self.assertEqual(run("Pinta la cerca.", "Paint the fence.").spanish, "Pintá la cerca.")
        self.assertEqual(run("Ven acá.", "Come here.").spanish, "Vení acá.")
        self.assertEqual(run("Haz tu dibujo.", "Do your drawing.").spanish, "Hacé tu dibujo.")

    def test_attached_pronouns(self):
        self.assertEqual(run("Píntame la cerca.", "Paint the fence for me.").spanish, "Pintame la cerca.")
        self.assertEqual(run("Lávate las botas.", "Wash your boots.").spanish, "Lavate las botas.")
        self.assertEqual(run("Siéntate allá.", "Sit down there.").spanish, "Sentate allá.")

    def test_statements_that_look_like_commands_are_kept(self):
        self.assertEqual(run("Zorba come mucho.", "Zorba eats a lot.").status, "unchanged")
        self.assertEqual(run("Se lo pinto.", "I paint it for him.").status, "unchanged")

    def test_command_with_unknown_verb_and_pronoun_is_dropped(self):
        self.assertEqual(run("Ordénamelo ya.", "Sort it for me now.").status, "dropped")

    def test_nosotros_commands_are_not_mistaken_for_tu_commands(self):
        self.assertEqual(run("Pintémoselo.", "Let's paint it for her.").status, "unchanged")

    def test_formal_commands_are_untouched(self):
        self.assertEqual(run("Pinte la cerca.", "Paint the fence.").status, "unchanged")


class VosotrosTests(unittest.TestCase):
    def test_regular_present_becomes_ustedes(self):
        outcome = run("Vosotros cantáis bien.", "You all sing well.")
        self.assertEqual((outcome.status, outcome.spanish), ("converted", "Ustedes cantan bien."))

    def test_commands_and_possessives(self):
        self.assertEqual(run("Cantad.", "Sing.").spanish, "Canten.")
        self.assertEqual(run("No bailéis aquí.", "Don't dance here.").spanish, "No bailen aquí.")
        self.assertEqual(run("Vuestro loro es verde.", "Your parrot is green.").spanish, "Su loro es verde.")

    def test_uncertain_vosotros_is_dropped(self):
        for spanish, english in [
            ("Cerrad la jaula.", "Close the cage."),
            ("Os pinto mañana.", "I paint you tomorrow."),
            ("Los loros vuestros viven aquí.", "Your parrots live here."),
            ("Divertíos mucho.", "Have a good time."),
            ("Pintadlo.", "Paint it."),
            ("Vosotros sois dragones.", "You all are dragons."),
            ("Vosotros dormís en la cueva.", "You all sleep in the cave."),
        ]:
            self.assertEqual(run(spanish, english).status, "dropped", spanish)


class VosotrosLeakTests(unittest.TestCase):
    def test_os_attached_to_infinitives_and_commands(self):
        for spanish, english in [
            ("Quiero pintaros una cerca.", "I want to paint you a fence."),
            ("Mandároslos es fácil.", "Sending them to you is easy."),
            ("Bañaos ahora.", "Take a bath now."),
            ("Ponéosla ya.", "Put it on now."),
        ]:
            self.assertEqual(run(spanish, english).status, "dropped", spanish)

    def test_nouns_ending_in_os_are_not_mistaken(self):
        self.assertEqual(run("Los museos están cerrados.", "The museums are closed.").status, "unchanged")
        self.assertEqual(run("Mis tíos duermen.", "My uncles sleep.").status, "unchanged")

    def test_other_vosotros_endings_are_dropped(self):
        for spanish, english in [
            ("Vosotros cantabais mucho.", "You all sang a lot."),
            ("Vosotros teníais un loro.", "You all had a parrot."),
            ("Vosotros cantasteis ayer.", "You all sang yesterday."),
            ("Vosotros dormisteis bien.", "You all slept well."),
            ("Si vosotros cantarais, bailaría.", "If you all sang, I would dance."),
            ("Si vosotros durmierais, soñaría.", "If you all slept, I would dream."),
        ]:
            self.assertEqual(run(spanish, english).status, "dropped", spanish)

    def test_vuestro_after_es_becomes_de_ustedes(self):
        outcome = run("El loro es vuestro.", "The parrot is yours.")
        self.assertEqual((outcome.status, outcome.spanish), ("converted", "El loro es de ustedes."))
        self.assertEqual(run("Es vuestro porque sí y más.", "It is yours, period.").status, "dropped")


class TuLeakTests(unittest.TestCase):
    def test_dont_you_and_do_you_trigger_conversion(self):
        self.assertEqual(run("¿Por qué no vienes acá?", "Why don't you come here?").spanish, "¿Por qué no venís acá?")
        self.assertEqual(run("¿Duermes en la cueva?", "Do you sleep in the cave?").spanish, "¿Dormís en la cueva?")

    def test_ti_after_a_preposition_is_converted(self):
        self.assertEqual(run("Pinto la cerca por ti.", "I paint the fence for you.").spanish, "Pinto la cerca por vos.")
        self.assertEqual(run("A ti te gusta el queso.", "The cheese pleases you.").spanish, "A vos te gusta el queso.")

    def test_tu_reflexive_verbs_without_you_in_english(self):
        self.assertEqual(run("Te llamas Zorba.", "Your name is Zorba.").status, "dropped")
        self.assertEqual(run("¿Cómo te sientes?", "How are you feeling?").status, "dropped")

    def test_negative_commands_with_te_are_kept(self):
        for spanish, english in [("No te vayas.", "Don't leave."), ("No te quejes del frío.", "Don't complain about the cold.")]:
            self.assertNotEqual(run(spanish, english).status, "dropped", spanish)

    def test_ocr_slipped_imperative_is_dropped(self):
        self.assertEqual(run("Enséñanosa.", "Show us.").status, "dropped")

    def test_ojala_is_not_an_imperative(self):
        self.assertEqual(run("Ojalá que llueva.", "I hope it rains.").status, "unchanged")
        self.assertEqual(run("Además llueve.", "Besides, it rains.").status, "unchanged")


class WordCardTests(unittest.TestCase):
    def test_pronouns_after_prepositions_and_alone(self):
        from second_person import convert_word_card
        convert = lambda spanish, english="": convert_word_card(spanish, english)[0]
        self.assertEqual(convert("tú"), "vos")
        self.assertEqual(convert("excepto tú"), "excepto vos")
        self.assertEqual(convert("sin ti"), "sin vos")
        self.assertEqual(convert("vosotros"), "ustedes")
        self.assertEqual(convert("entre vosotras y yo"), "entre ustedes y yo")

    def test_contigo_and_unsafe_cards_stay(self):
        from second_person import convert_word_card
        convert = lambda spanish, english="": convert_word_card(spanish, english)[0]
        self.assertEqual(convert("contigo"), "contigo")
        self.assertEqual(convert("tú eres"), "tú eres")
        self.assertEqual(convert("el vuestro"), "el vuestro")

    def test_possessive_and_os(self):
        from second_person import convert_word_card
        convert = lambda spanish, english="": convert_word_card(spanish, english)[0]
        self.assertEqual(convert("vuestro loro"), "su loro")
        self.assertEqual(convert("os", "oneself, themselves"), "se")
        self.assertEqual(convert("os lo, os la", "it to you"), "se lo, se la")
        self.assertEqual(convert("os los, os las", "them to you"), "se los, se las")
        self.assertEqual(convert_word_card("os lo, os la", "it to you")[1], "it to you (all)")
        self.assertEqual(convert_word_card("os los, os las", "them to you")[1], "them to you (all)")

    def test_os_depends_on_the_gloss(self):
        from second_person import convert_word_card
        self.assertEqual(convert_word_card("os", "to you")[0], "les")
        self.assertEqual(convert_word_card("os", "you (direct object)")[0], "los, las")
        self.assertEqual(convert_word_card("os", "yourselves")[0], "se")

    def test_bare_vuestro_card_becomes_de_ustedes(self):
        from second_person import convert_word_card
        self.assertEqual(convert_word_card("vuestro/a", "your (pl.)")[0], "de ustedes")


if __name__ == "__main__":
    unittest.main()
