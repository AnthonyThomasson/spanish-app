import unittest

from conjugation_english import ENGLISH_SUBJECTS, conjugate_english, first_sense


class FirstSenseTests(unittest.TestCase):
    def test_takes_the_first_comma_separated_sense(self):
        self.assertEqual(first_sense("to blorp, to zint"), "blorp")

    def test_commas_inside_parentheses_do_not_split(self):
        self.assertEqual(first_sense("to blorp (a thing, a place), to zint"), "blorp")

    def test_drops_parentheses_and_keeps_a_multiword_sense(self):
        self.assertEqual(first_sense("to have zimble (at noon)"), "have zimble")
        self.assertEqual(first_sense("to blorp (one's wibbles) up"), "blorp up")

    def test_semicolon_and_slash_also_separate_senses(self):
        self.assertEqual(first_sense("to blorp; to zint"), "blorp")
        self.assertEqual(first_sense("to blorp/zint"), "blorp")

    def test_a_modal_sense_is_kept(self):
        self.assertEqual(first_sense("can, to be able"), "can")

    def test_unusable_glosses_are_rejected(self):
        for gloss in ("", "to", "the blorp", "to 4blorp", "to blorp @ zint", "to (blorp)", "to blorp (a thing"):
            self.assertIsNone(first_sense(gloss), gloss)

    def test_requires_to_or_a_modal(self):
        self.assertIsNone(first_sense("blorp"))


class ConjugateEnglishTests(unittest.TestCase):
    def forms(self, gloss, reflexive=False):
        return {pronoun: conjugate_english(gloss, pronoun, reflexive) for pronoun in ENGLISH_SUBJECTS}

    def test_regular_verb_uses_the_distinguishable_subjects(self):
        self.assertEqual(self.forms("to blorp"), {
            "yo": "I blorp",
            "vos": "you blorp",
            "él": "he blorps",
            "ella": "she blorps",
            "Ud.": "you (formal) blorp",
            "nosotros": "we blorp",
            "ellos": "they (m.) blorp",
            "ellas": "they (f.) blorp",
            "Uds.": "you all blorp",
        })

    def test_third_person_spelling(self):
        cases = {
            "to blorch": "blorches",
            "to zint": "zints",
            "to wibbox": "wibboxes",
            "to frizz": "frizzes",
            "to flush": "flushes",
            "to blurry": "blurries",
            "to display": "displays",
            "to zimbo": "zimboes",
        }
        for gloss, expected in cases.items():
            self.assertEqual(conjugate_english(gloss, "él", False), f"he {expected}", gloss)

    def test_be_has_its_own_forms(self):
        self.assertEqual(conjugate_english("to be", "yo", False), "I am")
        self.assertEqual(conjugate_english("to be", "vos", False), "you are")
        self.assertEqual(conjugate_english("to be", "ella", False), "she is")
        self.assertEqual(conjugate_english("to be", "Ud.", False), "you (formal) are")
        self.assertEqual(conjugate_english("to be", "ellas", False), "they (f.) are")
        self.assertEqual(conjugate_english("to be", "Uds.", False), "you all are")

    def test_be_leads_a_multiword_gloss(self):
        self.assertEqual(conjugate_english("to be able, can", "yo", False), "I am able")
        self.assertEqual(conjugate_english("to be able, can", "él", False), "he is able")

    def test_have_do_go_are_irregular_in_the_third_person_only(self):
        self.assertEqual(conjugate_english("to have", "él", False), "he has")
        self.assertEqual(conjugate_english("to have", "nosotros", False), "we have")
        self.assertEqual(conjugate_english("to do", "ella", False), "she does")
        self.assertEqual(conjugate_english("to do, to make", "yo", False), "I do")
        self.assertEqual(conjugate_english("to go", "él", False), "he goes")
        self.assertEqual(conjugate_english("to go", "vos", False), "you go")

    def test_multiword_gloss_conjugates_only_the_first_word(self):
        self.assertEqual(conjugate_english("to have zimble", "él", False), "he has zimble")
        self.assertEqual(conjugate_english("to have zimble", "ellos", False), "they (m.) have zimble")
        self.assertEqual(conjugate_english("to blorp up", "ella", False), "she blorps up")
        self.assertEqual(conjugate_english("to listen to", "Ud.", False), "you (formal) listen to")
        self.assertEqual(conjugate_english("to go down, to descend", "ella", False), "she goes down")

    def test_reflexive_glosses_are_plain_verbs(self):
        self.assertEqual(conjugate_english("to get blorped", "yo", True), "I get blorped")
        self.assertEqual(conjugate_english("to wake zint", "él", True), "he wakes zint")

    def test_oneself_and_ones_follow_the_subject(self):
        self.assertEqual(conjugate_english("to blorp oneself", "yo", True), "I blorp myself")
        self.assertEqual(conjugate_english("to blorp oneself", "ella", True), "she blorps herself")
        self.assertEqual(conjugate_english("to blorp oneself", "ellos", True), "they (m.) blorp themselves")
        self.assertEqual(conjugate_english("to blorp oneself", "Uds.", True), "you all blorp yourselves")
        self.assertEqual(conjugate_english("to blorp oneself", "vos", True), "you blorp yourself")
        self.assertEqual(conjugate_english("to blorp one's wibble", "nosotros", True), "we blorp our wibble")
        self.assertEqual(conjugate_english("to blorp one's wibble", "él", True), "he blorps his wibble")

    def test_modals_do_not_take_an_s(self):
        self.assertEqual(conjugate_english("can", "él", False), "he can")
        self.assertEqual(conjugate_english("must", "ella", False), "she must")

    def test_a_gloss_that_cannot_be_trusted_gives_none(self):
        self.assertIsNone(conjugate_english("", "yo", False))
        self.assertIsNone(conjugate_english("to 4zint", "yo", False))
        self.assertIsNone(conjugate_english("to blorp", "tú", False))


if __name__ == "__main__":
    unittest.main()
