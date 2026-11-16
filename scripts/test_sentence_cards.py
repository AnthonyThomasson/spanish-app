import unittest
from collections import Counter

from ocr_fixtures import image, obs, two_columns
from ocr_layout import clean_text, detect_language, group_wrapped_lines, match_rows, merge_row_observations, split_sentences
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


class OcrCorrectionTests(unittest.TestCase):
    def test_a_tempo_is_a_spanish_side_slip_for_a_tiempo(self):
        self.assertEqual(clean_text("Ana llegó a tempo.", "es"), "Ana llegó a tiempo.")
        self.assertEqual(clean_text("Llegaron a tempo a la fiesta.", "es"), "Llegaron a tiempo a la fiesta.")

    def test_a_tempo_in_english_is_left_alone(self):
        self.assertEqual(clean_text("Play the next bar a tempo.", "en"), "Play the next bar a tempo.")


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
        cards, _ = parse(two_columns([("Dónde duerme el loro?", "Where does the parrot sleep?")]))
        self.assertEqual(cards[0].spanish, "¿Dónde duerme el loro?")

    def test_headings_and_bullets_are_ignored(self):
        img = image("p050_00.png", [
            obs("•", 0.0, 0.95, 0.02),
            obs("Health", 0.03, 0.95, 0.15),
            obs("Zorba pinta la cerca.", 0.05, 0.8),
            obs("Zorba paints the fence.", 0.6, 0.8),
        ])
        cards, _ = parse(img)
        self.assertEqual([(c.spanish, c.english) for c in cards], [("Zorba pinta la cerca.", "Zorba paints the fence.")])

    def test_rows_with_several_sentences_are_split_when_counts_match(self):
        cards, _ = parse(two_columns([("Saltemos. Riamos.", "Let's jump. Let's laugh.")]))
        self.assertEqual([(c.spanish, c.english) for c in cards], [("Saltemos.", "Let's jump."), ("Riamos.", "Let's laugh.")])

    def test_conjugation_tables_are_skipped(self):
        img = image("p120_00.png", [
            obs("nosotros", 0.0, 0.9), obs("hablamos", 0.3, 0.9), obs("Uds.", 0.0, 0.8), obs("hablan", 0.3, 0.8),
        ])
        self.assertEqual(parse(img)[0], [])

    def test_names_with_accents_in_english_are_fine(self):
        cards, _ = parse(two_columns([("Zulema llega temprano.", "Zulema arrives early.")]))
        self.assertEqual(len(cards), 1)

    def test_english_function_word_in_spanish_side_is_rejected(self):
        cards, _ = parse(two_columns([("Nosotros íbamos a pintar in cerca.", "We were going to paint a fence.")]))
        self.assertEqual(cards, [])

    def test_headings_and_labels_are_rejected_explicitly(self):
        for spanish, english in [
            ("El zorro come uvas.", "English Construction"),
            ("El zorro come uvas.", "NOTE: the fox eats grapes."),
            ("El zorro come uvas.", "Present Tense"),
            ("El zorro come uvas.", "EXAMPLE The fox eats grapes."),
        ]:
            cards, report = parse(two_columns([(spanish, english)]))
            self.assertEqual(cards, [], english)

    def test_side_specific_ocr_corrections(self):
        cards, _ = parse(two_columns([
            ("Es imposible dormir aquí.", "It is imposible to sleep here."),
            ("Yo vi el cohete ayer.", "I sau the rocket yesterday."),
            ("Ellos tienen su propio perro.", "They have their oun dog."),
        ]))
        self.assertEqual([(c.spanish, c.english) for c in cards], [
            ("Es imposible dormir aquí.", "It is impossible to sleep here."),
            ("Yo vi el cohete ayer.", "I saw the rocket yesterday."),
            ("Ellos tienen su propio perro.", "They have their own dog."),
        ])

    def test_spanish_side_slips_and_stray_marks(self):
        cards, _ = parse(two_columns([
            ("Cada apartmento tiene un balcón®.", "Each flat has a balcony."),
            ("La luna sale.., y brilla.", "The moon rises, and shines."),
        ]))
        self.assertEqual(cards[0].spanish, "Cada apartamento tiene un balcón.")
        self.assertNotIn("..", cards[1].spanish)

    def test_doubled_punctuation_is_collapsed(self):
        cards, _ = parse(two_columns([("Apagá la vela..", "Blow out the candle.")]))
        self.assertEqual(cards[0].spanish, "Apagá la vela.")

    def test_terminal_punctuation_is_copied_to_the_other_side(self):
        cards, _ = parse(two_columns([("El loro habla mucho", "The parrot talks a lot.")]))
        self.assertEqual((cards[0].spanish, cards[0].english), ("El loro habla mucho.", "The parrot talks a lot."))

    def test_cut_off_pairs_are_dropped(self):
        for spanish, english in [
            ("No sé si el loro come si", "I don't know if the parrot eats if"),
            ("El pez nada en este", "The fish swims in this"),
            ("Quiero que", "I want that"),
        ]:
            cards, _ = parse(two_columns([(spanish, english)]))
            self.assertEqual(cards, [], spanish)

    def test_english_without_a_full_stop_is_not_cut_off(self):
        cards, _ = parse(two_columns([("Zorba la mira.", "Zorba looks at her"), ("Zorba lo pinta.", "Zorba paints it")]))
        self.assertEqual([c.english for c in cards], ["Zorba looks at her.", "Zorba paints it."])

    def test_short_spanish_next_to_long_english_is_dropped(self):
        cards, _ = parse(two_columns([("No saltemos", "Let's not jump over the old garden wall.")]))
        self.assertEqual(cards, [])

    def test_closed_short_commands_are_kept(self):
        cards, _ = parse(two_columns([("Pintalo.", "Paint it for me."), ("Saltemos.", "Let's jump.")]))
        self.assertEqual(len(cards), 2)

    def test_statements_ending_in_a_dangling_word_are_dropped(self):
        for spanish, english in [
            ("Zorba dice que le gusta pintar.", "Zorba says he likes to."),
            ("El loro viene de la cueva.", "The parrot is coming from."),
            ("Vivo en Lima por tres años.", "I have lived in Lima for."),
        ]:
            cards, _ = parse(two_columns([(spanish, english)]))
            self.assertEqual(cards, [], english)

    def test_questions_ending_in_a_preposition_are_kept(self):
        cards, _ = parse(two_columns([("¿De dónde viene el loro?", "Where is the parrot from?")]))
        self.assertEqual(len(cards), 1)

    def test_unclosed_statements_get_a_full_stop_on_both_sides(self):
        cards, _ = parse(two_columns([("Zorba pinta la cerca verde", "Zorba paints the green fence")]))
        self.assertEqual((cards[0].spanish, cards[0].english), ("Zorba pinta la cerca verde.", "Zorba paints the green fence."))

    def test_garbled_english_is_dropped(self):
        cards, _ = parse(two_columns([("¿Dónde duerme el loro?", "Where does the parrot sleep'?")]))
        self.assertEqual(cards, [])


if __name__ == "__main__":
    unittest.main()
