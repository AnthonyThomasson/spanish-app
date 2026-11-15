import unittest
from collections import Counter

from ocr_fixtures import image, obs, two_columns
from ocr_layout import detect_language, group_wrapped_lines, match_rows, merge_row_observations, split_sentences
from sentence_cards import parse_image


def parse(img):
    report = Counter()
    return parse_image(img, report), report


class LayoutHelperTests(unittest.TestCase):
    def test_split_sentences_keeps_abbreviations_together(self):
        self.assertEqual(
            split_sentences("Hola, Sr. Pérez. ¿Cómo está Ud.? Bien."),
            ["Hola, Sr. Pérez.", "¿Cómo está Ud.?", "Bien."],
        )

    def test_detect_language(self):
        self.assertEqual(detect_language("¿Dónde está la casa?"), "es")
        self.assertEqual(detect_language("Where is the house?"), "en")
        # Accents in English text are names, not Spanish.
        self.assertEqual(detect_language("María and José are here.", count_accents=False), "en")

    def test_wrapped_lines_join_on_indent_or_lowercase(self):
        lines = merge_row_observations([
            obs("El gato negro come el", 0.0, 0.9),
            obs("pescado.", 0.04, 0.8),
            obs("Ana bebe agua.", 0.0, 0.7),
        ])
        self.assertEqual([group["text"] for group in group_wrapped_lines(lines)], ["El gato negro come el pescado.", "Ana bebe agua."])

    def test_wrapped_line_with_capitalised_name_is_joined_by_indent(self):
        lines = merge_row_observations([obs("Vamos a ver si", 0.0, 0.9), obs("Lucía llega.", 0.04, 0.8)])
        self.assertEqual([group["text"] for group in group_wrapped_lines(lines)], ["Vamos a ver si Lucía llega."])

    def test_match_rows_pairs_by_position_and_counts_leftovers(self):
        left = group_wrapped_lines(merge_row_observations([obs("Uno aquí.", 0.0, 0.9), obs("Dos aquí.", 0.0, 0.5)]))
        right = group_wrapped_lines(merge_row_observations([obs("One here.", 0.6, 0.9), obs("(a note)", 0.6, 0.7)]))
        pairs, unmatched = match_rows(left, right)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(unmatched, 2)


class SentenceImageTests(unittest.TestCase):
    def test_pairs_each_row(self):
        cards, _ = parse(two_columns([
            ("El gato duerme en la cama.", "The cat sleeps in the bed."),
            ("¿Dónde está mi libro?", "Where is my book?"),
        ]))
        self.assertEqual([(card.spanish, card.english) for card in cards], [
            ("El gato duerme en la cama.", "The cat sleeps in the bed."),
            ("¿Dónde está mi libro?", "Where is my book?"),
        ])
        self.assertTrue(all(card.kind == "sentence" for card in cards))

    def test_wrapped_english_is_joined(self):
        img = image("p050_00.png", [
            obs("Mi hermana vive en una casa", 0.0, 0.9),
            obs("grande.", 0.04, 0.8),
            obs("My sister lives in a big", 0.55, 0.9),
            obs("house.", 0.58, 0.8),
        ])
        cards, _ = parse(img)
        self.assertEqual([(c.spanish, c.english) for c in cards], [("Mi hermana vive en una casa grande.", "My sister lives in a big house.")])

    def test_word_lists_are_not_sentences(self):
        cards, report = parse(two_columns([("el gato el perro la casa", "the cat the dog the house")]))
        self.assertEqual(cards, [])
        self.assertGreater(sum(count for key, count in report.items() if key.startswith("sentences.rejected")), 0)

    def test_single_word_pairs_are_left_to_the_word_parser(self):
        cards, _ = parse(two_columns([("el gato", "the cat"), ("la mesa", "the table")]))
        self.assertEqual(cards, [])

    def test_ocr_slips_are_repaired(self):
        cards, _ = parse(two_columns([
            ("Yo estoy bien.", "1 am fine."),
            ("¿Cómo estás tú?", "How are you!"),
            ("La mesa es grande.", "The table is big"),
        ]))
        self.assertEqual([c.english for c in cards], ["I am fine.", "How are you?", "The table is big."])

    def test_missing_inverted_question_mark_is_restored(self):
        cards, _ = parse(two_columns([("Dónde vives?", "Where do you live?")]))
        self.assertEqual(cards[0].spanish, "¿Dónde vives?")

    def test_headings_and_bullets_are_ignored(self):
        img = image("p050_00.png", [
            obs("•", 0.0, 0.95, 0.02),
            obs("Health", 0.03, 0.95, 0.15),
            obs("Ella está enferma.", 0.05, 0.8),
            obs("She is sick.", 0.6, 0.8),
        ])
        cards, _ = parse(img)
        self.assertEqual([(c.spanish, c.english) for c in cards], [("Ella está enferma.", "She is sick.")])

    def test_rows_with_several_sentences_are_split_when_counts_match(self):
        cards, _ = parse(two_columns([("Cantemos. Bailemos.", "Let's sing. Let's dance.")]))
        self.assertEqual([(c.spanish, c.english) for c in cards], [("Cantemos.", "Let's sing."), ("Bailemos.", "Let's dance.")])

    def test_conjugation_tables_are_skipped(self):
        img = image("p120_00.png", [
            obs("nosotros", 0.0, 0.9), obs("hablamos", 0.3, 0.9), obs("Uds.", 0.0, 0.8), obs("hablan", 0.3, 0.8),
        ])
        self.assertEqual(parse(img)[0], [])

    def test_names_with_accents_in_english_are_fine(self):
        cards, _ = parse(two_columns([("María llega temprano.", "María arrives early.")]))
        self.assertEqual(len(cards), 1)

    def test_english_function_word_in_spanish_side_is_rejected(self):
        cards, _ = parse(two_columns([("Nosotros íbamos a comprar in carro.", "We were going to buy a car.")]))
        self.assertEqual(cards, [])


if __name__ == "__main__":
    unittest.main()
