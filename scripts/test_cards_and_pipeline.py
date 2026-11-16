import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import command_cards
import extra_vocab
from ocr_fixtures import image, obs, two_columns
from vocab_parser import build_vocabulary


class CommandTableTests(unittest.TestCase):
    def test_vos_commands_from_the_infinitive_column(self):
        img = image("p509_02.png", [
            obs("Infinitive", 0.0, 0.95, 0.2), obs("tú Command", 0.35, 0.95, 0.3), obs("English", 0.8, 0.95, 0.2),
            obs("sentarse", 0.0, 0.8), obs("Siéntate.", 0.35, 0.8), obs("Sit down.", 0.8, 0.8),
            obs("venir", 0.0, 0.6), obs("ven", 0.35, 0.6), obs("come", 0.8, 0.6),
        ])
        cards = command_cards.parse_image(img, Counter())
        self.assertEqual([(c.spanish, c.english, c.kind) for c in cards], [
            ("Sentate.", "Sit down.", "sentence"), ("Vení.", "Come.", "sentence"),
        ])


class ExtraVocabTests(unittest.TestCase):
    def test_number_words_and_english(self):
        self.assertEqual(extra_vocab.spanish_number_value("treinta y uno"), 31)
        self.assertEqual(extra_vocab.spanish_number_value("dos mil"), 2000)
        self.assertEqual(extra_vocab.spanish_number_value("gato"), None)
        self.assertEqual(extra_vocab.english_number(31), "thirty-one")
        self.assertEqual(extra_vocab.english_number(199), "one hundred ninety-nine")
        self.assertEqual(extra_vocab.english_number(2_000_000), "two million")

    def test_number_table_checks_digits_against_words(self):
        img = image("p079_00.png", [
            obs("1", 0.0, 0.9, 0.02), obs("uno", 0.1, 0.9),
            obs("2", 0.0, 0.8, 0.02), obs("dos", 0.1, 0.8),
            obs("3", 0.0, 0.7, 0.02), obs("tres", 0.1, 0.7),
            obs("4", 0.0, 0.6, 0.02), obs("cinco", 0.1, 0.6),  # slip: digit and word disagree
            obs("cero", 0.1, 0.5),  # no digit: still a number word
        ])
        cards = extra_vocab.parse_number_table(img, Counter())
        self.assertEqual([(c.spanish, c.english) for c in cards], [("uno", "one"), ("dos", "two"), ("tres", "three"), ("cero", "zero")])

    def test_interrogative_list_and_headings(self):
        img = image("p393_03.png", [
            obs("¿ cómo?", 0.0, 0.9), obs("how?", 0.5, 0.9),
            obs("¿cuál?, ¿cuáles?", 0.0, 0.7), obs("which one?, which ones?", 0.5, 0.7),
            obs("¿Que?", 0.0, 0.5), obs("what?", 0.5, 0.5),
            obs("¿Cómo estás?", 0.0, 0.3), obs("How are you?", 0.5, 0.3),  # a sentence, not an interrogative word
        ])
        cards = extra_vocab.parse_interrogatives(img, Counter())
        self.assertEqual([(c.spanish, c.english) for c in cards], [
            ("¿cómo?", "how?"), ("¿cuál?, ¿cuáles?", "which one?, which ones?"), ("¿qué?", "what?"),
        ])
        heading = image("p064_00.png", [obs("¿Dónde? Where?", 0.0, 0.9, 0.3)])
        self.assertEqual([(c.spanish, c.english) for c in extra_vocab.parse_interrogatives(heading, Counter())], [("¿dónde?", "where?")])

    def test_a_missing_cien_is_added_next_to_the_hundreds(self):
        img = image("p079_00.png", [
            obs("200", 0.0, 0.9, 0.04), obs("doscientos", 0.1, 0.9),
            obs("300", 0.0, 0.8, 0.04), obs("trescientos", 0.1, 0.8),
            obs("400", 0.0, 0.7, 0.04), obs("cuatrocientos", 0.1, 0.7),
        ])
        spanish = [c.spanish for c in extra_vocab.parse_number_table(img, Counter())]
        self.assertIn("cien", spanish)

    def test_sections_split_by_spanish_headers(self):
        img = image("p287_00.png", [
            obs("Verbos", 0.0, 0.95, 0.1),
            obs("charlar", 0.04, 0.85), obs("to chat", 0.3, 0.85),
            obs("Nombres", 0.0, 0.6, 0.1),
            obs("la nata", 0.04, 0.5), obs("the cream", 0.3, 0.5),
        ])
        cards = extra_vocab.parse_sections(img, Counter())
        self.assertEqual([(c.spanish, c.english) for c in cards], [("charlar", "to chat"), ("la nata", "the cream")])


def build(images, starts=None):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ocr.json"
        path.write_text(json.dumps(images))
        return build_vocabulary(path, starts or {1: 1, 2: 100}, ["One", "Two"])


class PipelineTests(unittest.TestCase):
    def test_words_have_no_kind_and_sentences_do(self):
        vocabulary, stats = build([
            two_columns([("el gato", "the cat"), ("la mesa", "the table")], "p010_00.png"),
            two_columns([("El gato duerme.", "The cat sleeps.")], "p011_00.png"),
        ])
        words = vocabulary["chapters"][0]["words"]
        self.assertTrue(all("kind" not in word for word in words if word["spanish"] in ("el gato", "la mesa")))
        sentence = next(word for word in words if word.get("kind") == "sentence")
        self.assertEqual(sentence["spanish"], "El gato duerme.")
        self.assertEqual(stats["cards"], {"word": 2, "sentence": 1})

    def test_sentences_are_deduplicated_per_chapter_only(self):
        vocabulary, _ = build([
            two_columns([("El gato duerme.", "The cat sleeps.")], "p010_00.png"),
            two_columns([("El gato duerme.", "The cat sleeps.")], "p020_00.png"),
            two_columns([("El gato duerme.", "The cat sleeps.")], "p110_00.png"),
        ])
        self.assertEqual([len(chapter["words"]) for chapter in vocabulary["chapters"]], [1, 1])

    def test_tu_sentence_is_converted_and_unknown_one_dropped(self):
        vocabulary, stats = build([
            two_columns([("cantar", "to sing")], "p010_00.png"),
            two_columns([("¿Cantas bien?", "Do you sing well?"), ("¿Cuánto cobras?", "How much do you charge?")], "p011_00.png"),
        ])
        texts = [word["spanish"] for word in vocabulary["chapters"][0]["words"]]
        self.assertIn("¿Cantás bien?", texts)
        self.assertNotIn("¿Cuánto cobras?", texts)
        self.assertEqual(stats["report"]["second_person.dropped"], 1)

    def test_pronoun_word_cards_become_argentine(self):
        vocabulary, stats = build([
            two_columns([("sin ti", "without you"), ("excepto tú", "except you"), ("contigo", "with you"), ("os lo, os la", "it to you")], "p010_00.png"),
        ])
        words = vocabulary["chapters"][0]["words"]
        self.assertEqual([word["spanish"] for word in words], ["sin vos", "excepto vos", "contigo", "se lo, se la"])
        self.assertEqual(words[3]["english"], "it to you (all)")
        self.assertEqual(stats["report"]["second_person.word_cards_converted"], 3)

    def test_interrogatives_are_kept_once_in_the_first_chapter(self):
        vocabulary, _ = build([
            two_columns([("¿cómo?", "how?"), ("¿dónde?", "where?")], "p010_00.png"),
            two_columns([("¿cómo?", "how?")], "p110_00.png"),
        ])
        self.assertEqual([len(chapter["words"]) for chapter in vocabulary["chapters"]], [2, 0])

    def test_os_card_repeating_the_chapters_se_card_is_dropped(self):
        vocabulary, _ = build([
            two_columns([("se", "himself, herself"), ("os", "yourselves"), ("pintar", "to paint")], "p010_00.png"),
        ])
        pairs = [(w["spanish"], w["english"]) for w in vocabulary["chapters"][0]["words"]]
        self.assertEqual(pairs, [("se", "himself, herself"), ("pintar", "to paint")])

    def test_argentine_map_applies_to_words_and_sentences(self):
        vocabulary, _ = build([
            two_columns([("el coche", "the car"), ("la patata", "the potato"), ("el carro de compras", "the shopping cart")], "p010_00.png"),
            two_columns([("Yo tengo un coche rojo.", "I have a red car.")], "p011_00.png"),
        ])
        texts = [word["spanish"] for word in vocabulary["chapters"][0]["words"]]
        self.assertEqual(texts, ["el auto", "la papa", "el carro de compras", "Yo tengo un auto rojo."])


if __name__ == "__main__":
    unittest.main()
