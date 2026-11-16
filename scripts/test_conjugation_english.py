import unittest

from conjugation_english import ENGLISH_SENSES, ENGLISH_SUBJECTS, conjugate_english, english_prompt, first_sense


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
    def forms(self, gloss):
        return {pronoun: conjugate_english(gloss, pronoun) for pronoun in ENGLISH_SUBJECTS}

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
            self.assertEqual(conjugate_english(gloss, "él"), f"he {expected}", gloss)

    def test_be_has_its_own_forms(self):
        self.assertEqual(conjugate_english("to be", "yo"), "I am")
        self.assertEqual(conjugate_english("to be", "vos"), "you are")
        self.assertEqual(conjugate_english("to be", "ella"), "she is")
        self.assertEqual(conjugate_english("to be", "Ud."), "you (formal) are")
        self.assertEqual(conjugate_english("to be", "ellas"), "they (f.) are")
        self.assertEqual(conjugate_english("to be", "Uds."), "you all are")

    def test_be_leads_a_multiword_gloss(self):
        self.assertEqual(conjugate_english("to be able, can", "yo"), "I am able")
        self.assertEqual(conjugate_english("to be able, can", "él"), "he is able")

    def test_have_do_go_are_irregular_in_the_third_person_only(self):
        self.assertEqual(conjugate_english("to have", "él"), "he has")
        self.assertEqual(conjugate_english("to have", "nosotros"), "we have")
        self.assertEqual(conjugate_english("to do", "ella"), "she does")
        self.assertEqual(conjugate_english("to do, to make", "yo"), "I do")
        self.assertEqual(conjugate_english("to go", "él"), "he goes")
        self.assertEqual(conjugate_english("to go", "vos"), "you go")

    def test_multiword_gloss_conjugates_only_the_first_word(self):
        self.assertEqual(conjugate_english("to have zimble", "él"), "he has zimble")
        self.assertEqual(conjugate_english("to have zimble", "ellos"), "they (m.) have zimble")
        self.assertEqual(conjugate_english("to blorp up", "ella"), "she blorps up")
        self.assertEqual(conjugate_english("to listen to", "Ud."), "you (formal) listen to")
        self.assertEqual(conjugate_english("to go down, to descend", "ella"), "she goes down")

    def test_reflexive_glosses_are_plain_verbs(self):
        self.assertEqual(conjugate_english("to get blorped", "yo"), "I get blorped")
        self.assertEqual(conjugate_english("to wake zint", "él"), "he wakes zint")

    def test_oneself_and_ones_follow_the_subject(self):
        self.assertEqual(conjugate_english("to blorp oneself", "yo"), "I blorp myself")
        self.assertEqual(conjugate_english("to blorp oneself", "ella"), "she blorps herself")
        self.assertEqual(conjugate_english("to blorp oneself", "ellos"), "they (m.) blorp themselves")
        self.assertEqual(conjugate_english("to blorp oneself", "Uds."), "you all blorp yourselves")
        self.assertEqual(conjugate_english("to blorp oneself", "vos"), "you blorp yourself")
        self.assertEqual(conjugate_english("to blorp one's wibble", "nosotros"), "we blorp our wibble")
        self.assertEqual(conjugate_english("to blorp one's wibble", "él"), "he blorps his wibble")

    def test_modals_do_not_take_an_s(self):
        self.assertEqual(conjugate_english("can", "él"), "he can")
        self.assertEqual(conjugate_english("must", "ella"), "she must")

    def test_a_gloss_that_cannot_be_trusted_gives_none(self):
        self.assertIsNone(conjugate_english("", "yo"))
        self.assertIsNone(conjugate_english("to 4zint", "yo"))
        self.assertIsNone(conjugate_english("to blorp", "tú"))


class EnglishPromptTests(unittest.TestCase):
    def test_a_verb_without_curated_senses_uses_the_gloss(self):
        self.assertEqual(english_prompt("folmar", "to blorp, to zint", "ella"), "she blorps")
        self.assertIsNone(english_prompt("folmar", "to 4blorp", "ella"))
        self.assertIsNone(english_prompt("folmar", "", "ella"))

    def test_curated_senses_replace_an_unnatural_book_gloss(self):
        self.assertEqual(english_prompt("almorzar", "to lunch", "yo"), "I have lunch")
        self.assertEqual(english_prompt("almorzar", "to lunch", "ella"), "she has lunch")
        self.assertEqual(english_prompt("despertarse", "to wake oneself", "nosotros"), "we wake up")
        self.assertEqual(english_prompt("despertarse", "to wake oneself", "él"), "he wakes up")
        self.assertEqual(english_prompt("divertirse", "to amuse oneself", "ellas"),
                         "they (f.) have a good time / they (f.) amuse themselves")

    def test_poder_offers_be_able_and_can_and_can_is_a_modal(self):
        self.assertEqual(english_prompt("poder", "to be able", "yo"), "I am able / I can")
        self.assertEqual(english_prompt("poder", "to be able", "él"), "he is able / he can")
        self.assertEqual(english_prompt("poder", "to be able", "Ud."), "you (formal) are able / you (formal) can")
        self.assertEqual(english_prompt("poder", "to be able", "ellos"), "they (m.) are able / they (m.) can")
        for pronoun in ENGLISH_SUBJECTS:
            text = english_prompt("poder", "to be able", pronoun)
            self.assertNotIn("cans", text)
            self.assertNotIn("does can", text)

    def test_deber_and_hacer_offer_both_senses(self):
        self.assertEqual(english_prompt("deber", "should", "ella"), "she should / she must")
        self.assertEqual(english_prompt("hacer", "to do, to make", "ella"), "she does / she makes")
        self.assertEqual(english_prompt("hacer", "to do, to make", "Uds."), "you all do / you all make")

    def test_every_curated_verb_conjugates_for_every_pronoun(self):
        for infinitive, senses in ENGLISH_SENSES.items():
            for pronoun in ENGLISH_SUBJECTS:
                text = english_prompt(infinitive, "", pronoun)
                self.assertIsNotNone(text, (infinitive, pronoun))
                self.assertEqual(text.count(" / "), len(senses) - 1)


if __name__ == "__main__":
    unittest.main()
