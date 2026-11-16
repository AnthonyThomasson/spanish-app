import re
import unittest
from collections import Counter
from pathlib import Path

from sentence_disambiguation import (
    classify_command,
    FIXED_TAGS,
    collision_groups,
    disambiguate_sentences,
    insert_tag,
    tense_of,
)


def sentence(spanish, english):
    return {"spanish": spanish, "english": english, "sourcePage": 1, "kind": "sentence"}


def word(spanish, english):
    return {"spanish": spanish, "english": english, "sourcePage": 1}


def run(*pairs):
    report = Counter()
    cards = disambiguate_sentences([sentence(*pair) for pair in pairs], report)
    return [(card["spanish"], card["english"]) for card in cards], report


class InsertTagTests(unittest.TestCase):
    def test_tag_goes_before_the_closing_punctuation(self):
        self.assertEqual(insert_tag("Drink.", "vos"), "Drink (vos).")
        self.assertEqual(insert_tag("Where are you from?", "Ud."), "Where are you from (Ud.)?")
        self.assertEqual(insert_tag("Come here", "vos"), "Come here (vos)")


class CommandTests(unittest.TestCase):
    def test_commands_are_told_apart_by_their_ending(self):
        self.assertEqual(classify_command("Cantá.", "Sing."), "vos")
        self.assertEqual(classify_command("Cante.", "Sing."), "Ud.")
        self.assertEqual(classify_command("Canten.", "Sing."), "Uds.")
        self.assertEqual(classify_command("No cantes.", "Don't sing."), "vos")
        self.assertEqual(classify_command("No cante.", "Don't sing."), "Ud.")
        self.assertEqual(classify_command("No se vayan.", "Don't go."), "Uds.")
        self.assertEqual(classify_command("No te vayas.", "Don't go."), "vos")

    def test_an_explicit_pronoun_wins(self):
        self.assertEqual(classify_command("Canten Uds.", "Sing."), "Uds.")
        self.assertEqual(classify_command("No cante Ud.", "Don't sing."), "Ud.")

    def test_statements_and_questions_are_not_commands(self):
        self.assertIsNone(classify_command("Fue buena.", "It was good."))
        self.assertIsNone(classify_command("¿Cantan?", "Do they sing?"))
        self.assertIsNone(classify_command("Pedro canta.", "The singer sings."))


class TenseTests(unittest.TestCase):
    def test_only_certain_forms_are_classified(self):
        self.assertEqual(tense_of("quise"), "preterit")
        self.assertEqual(tense_of("cantaron"), "preterit")
        self.assertEqual(tense_of("cantaba"), "imperfect")
        self.assertEqual(tense_of("éramos"), "imperfect")
        self.assertIsNone(tense_of("cantan"))
        self.assertIsNone(tense_of("café"))


class SpokenTextInStepTests(unittest.TestCase):
    """src/spoken-text.ts must strip exactly the tags this module can emit."""

    def tag_pattern(self):
        source = (Path(__file__).resolve().parent.parent / "src" / "spoken-text.ts").read_text()
        match = re.search(r"const DISAMBIGUATION_TAG =\s*/(.+)/g;", source)
        self.assertIsNotNone(match, "DISAMBIGUATION_TAG not found in src/spoken-text.ts")
        return match.group(1)

    def test_the_regex_lists_exactly_the_fixed_tags_and_the_hint(self):
        alternatives = re.search(r"\\\(\(\?:(.*?)\)\\\)", self.tag_pattern()).group(1).split("|")
        hint = [alternative for alternative in alternatives if alternative.startswith("Sp")]
        fixed = {alternative.replace("\\.", ".") for alternative in alternatives if not alternative.startswith("Sp")}
        self.assertEqual(fixed, set(FIXED_TAGS))
        self.assertEqual(len(hint), 1)

    def test_the_regex_strips_every_tag_the_module_emits(self):
        pattern = re.compile(self.tag_pattern())
        for tag in (*FIXED_TAGS, "Sp. fue buena"):
            self.assertEqual(pattern.sub("", insert_tag("It was fine.", tag)), "It was fine.", tag)


class DisambiguationTests(unittest.TestCase):
    def test_commands_get_vos_ud_uds(self):
        cards, report = run(("Cantá.", "Sing."), ("Cante.", "Sing."), ("Canten.", "Sing."))
        self.assertEqual([english for _, english in cards], ["Sing (vos).", "Sing (Ud.).", "Sing (Uds.)."])
        self.assertEqual(report["disambiguation.strategy.command"], 1)

    def test_a_you_sentence_is_told_apart_by_its_pronoun(self):
        cards, _ = run(("¿Dónde vive Ud.?", "Where do you live?"), ("¿Dónde viven Uds.?", "Where do you live?"))
        self.assertEqual([english for _, english in cards], ["Where do you live (Ud.)?", "Where do you live (Uds.)?"])

    def test_clitic_gender(self):
        cards, _ = run(("Quiero verlos.", "I want to see them."), ("Quiero verlas.", "I want to see them."))
        self.assertEqual([english for _, english in cards], ["I want to see them (m.).", "I want to see them (f.)."])

    def test_preterit_against_imperfect(self):
        cards, _ = run(("Yo quise bailar.", "I wanted to dance."), ("Yo quería bailar.", "I wanted to dance."))
        self.assertEqual(
            [english for _, english in cards], ["I wanted to dance (preterit).", "I wanted to dance (imperfect)."]
        )

    def test_two_preterits_fall_back_to_the_distinguishing_word(self):
        cards, report = run(("La torta fue rica.", "The cake was tasty."), ("La torta estuvo rica.", "The cake was tasty."))
        self.assertEqual([english for _, english in cards], ["The cake was tasty (Sp. fue).", "The cake was tasty (Sp. estuvo)."])
        self.assertEqual(report["disambiguation.strategy.hint"], 1)

    def test_a_conditional_is_not_called_imperfect(self):
        cards, _ = run(("Ana habría ido.", "Ana would have gone."), ("Ana hubiera ido.", "Ana would have gone."))
        self.assertEqual([english for _, english in cards], ["Ana would have gone (Sp. habría).", "Ana would have gone (Sp. hubiera)."])

    def test_pronoun_placement(self):
        cards, _ = run(("Voy a darlo ya.", "I am going to give it now."), ("Lo voy a dar ya.", "I am going to give it now."))
        self.assertEqual(
            [english for _, english in cards],
            ["I am going to give it now (pronoun attached).", "I am going to give it now (pronoun before)."],
        )

    def test_word_order_variants_are_told_apart_by_the_moved_word(self):
        cards, _ = run(("¿Canta Ana hoy?", "Is Ana singing today?"), ("¿Canta hoy Ana?", "Is Ana singing today?"))
        self.assertEqual(
            [english for _, english in cards], ["Is Ana singing today (Sp. hoy)?", "Is Ana singing today (Sp. ana)?"]
        )

    def test_a_repeated_word_still_counts_as_distinguishing(self):
        cards, _ = run(
            ("Si Ana hubiera ido, ella habría visto.", "If Ana had gone, she would have seen."),
            ("Si Ana hubiera ido, ella hubiera visto.", "If Ana had gone, she would have seen."),
        )
        self.assertEqual([english.split("(")[1] for _, english in cards], ["Sp. habría).", "Sp. hubiera)."])

    def test_unique_prompts_and_other_kinds_are_left_alone(self):
        report = Counter()
        cards = [
            sentence("Hola, Ana.", "Hello, Ana."),
            word("el artista", "the artist (male)"),
            word("la artista", "the artist (male)"),
            {**word("yo canto", "I sing"), "kind": "conjugation"},
            {**word("vos cantás", "I sing"), "kind": "conjugation"},
        ]
        self.assertEqual(disambiguate_sentences(cards, report), cards)
        self.assertEqual(sum(report.values()), 0)

    def test_the_same_english_in_two_chapters_is_not_a_collision(self):
        report = Counter()
        first = disambiguate_sentences([sentence("Cantá.", "Sing.")], report)
        second = disambiguate_sentences([sentence("Cante.", "Sing.")], report)
        self.assertEqual((first[0]["english"], second[0]["english"]), ("Sing.", "Sing."))

    def test_one_spanish_prompt_with_two_english_answers_is_merged(self):
        cards, report = run(("La torta es rica.", "The cake tastes good."), ("La torta es rica.", "The cake is good."))
        self.assertEqual(cards, [("La torta es rica.", "The cake tastes good. / The cake is good.")])
        self.assertEqual(report["disambiguation.merged_spanish"], 1)

    def test_a_repeated_pronoun_command_is_dropped_as_a_duplicate(self):
        cards, report = run(("Canten Uds.", "Sing."), ("Canten.", "Sing."), ("Cantá.", "Sing."))
        self.assertEqual(cards, [("Canten.", "Sing (Uds.)."), ("Cantá.", "Sing (vos).")])
        self.assertEqual(report["disambiguation.duplicates_dropped"], 1)

    def test_a_merged_card_is_tagged_in_every_alternative(self):
        cards, _ = run(
            ("Cantá.", "Sing."), ("Cantá.", "Have a sing."), ("Cante.", "Sing."),
        )
        self.assertEqual(cards[0][1], "Sing (vos). / Have a sing (vos).")

    def test_ustedes_spelled_out_is_a_duplicate_too(self):
        cards, _ = run(("Canten ustedes.", "Sing."), ("Canten.", "Sing."), ("Cantá.", "Sing."))
        self.assertEqual([spanish for spanish, _ in cards], ["Canten.", "Cantá."])

    def test_accents_keep_prompts_apart_when_merging(self):
        cards, report = run(("Hablo.", "I talk."), ("Habló.", "He talked."))
        self.assertEqual(cards, [("Hablo.", "I talk."), ("Habló.", "He talked.")])
        self.assertEqual(report["disambiguation.merged_spanish"], 0)
        # ...but punctuation and case alone do not make a different prompt.
        cards, _ = run(("¿Hablo?", "Do I talk?"), ("¿hablo?", "Am I talking?"))
        self.assertEqual(cards, [("¿Hablo?", "Do I talk? / Am I talking?")])

    def test_a_truncated_copy_of_an_answer_is_replaced_by_the_full_one(self):
        cards, report = run(
            ("Si Ana cantara, ella ganaría.", "If Ana sang"),
            ("Si Ana cantara, ella ganaría.", "If Ana sang she would win."),
        )
        self.assertEqual(cards, [("Si Ana cantara, ella ganaría.", "If Ana sang she would win.")])
        self.assertEqual(report["disambiguation.truncated_replaced"], 1)
        # The full answer first, the fragment second: the fragment is dropped.
        cards, report = run(
            ("Si Ana cantara, ella ganaría.", "If Ana sang she would win."),
            ("Si Ana cantara, ella ganaría.", "If Ana sang"),
        )
        self.assertEqual(cards[0][1], "If Ana sang she would win.")
        self.assertEqual(report["disambiguation.duplicates_dropped"], 1)

    def test_a_word_that_merely_starts_the_same_is_not_a_truncation(self):
        cards, _ = run(("Ana canta.", "Ana sings."), ("Ana canta.", "Ana singsong."))
        self.assertEqual(cards[0][1], "Ana sings. / Ana singsong.")

    def test_este_is_not_a_preterit(self):
        self.assertIsNone(tense_of("este"))
        self.assertEqual(tense_of("hablaste"), "preterit")

    def test_no_collisions_remain(self):
        cards, _ = run(
            ("Cantá.", "Sing."), ("Cante.", "Sing."),
            ("Fue buena.", "It was good."), ("Estuvo buena.", "It was good."), ("Fue bueno.", "It was good."),
            ("Quiero verlos.", "I want to see them."), ("Quiero verlas.", "I want to see them."),
        )
        self.assertEqual(collision_groups([sentence(*pair) for pair in cards]), [])
        self.assertEqual(len({english for _, english in cards}), len(cards))


if __name__ == "__main__":
    unittest.main()
