import unittest
from collections import Counter

from card_types import CONJUGATION, WORD, Card, ConjugationSource
from conjugation_cards import (
    PRESENT_CHAPTERS,
    check_slot,
    gloss_index,
    parse_cells,
    parse_image,
    resolve,
    resolve_all,
)
from ocr_fixtures import image, obs
from vocab_parser import build_vocabulary

SG = ("yo", "tú", "él", "ella", "Ud.")
PL = ("nosotros", "vosotros", "ellos", "ellas", "Uds.")


def block(header, forms, x=0.0, top=0.95, step=0.12):
    """Synthetic OCR of one verb: a header, then pronoun cells in a singular and a plural column.

    `forms` is (yo, tú, él, nosotros, vosotros, ellos); él/ella/Ud. share one form, ellos/ellas/Uds. another.
    """
    yo, tu, el, nos, vos, ellos = forms
    sg = [f"yo {yo}", f"tú {tu}", f"él {el}", f"ella {el}", f"Ud. {el}"]
    pl = [f"nosotros {nos}", f"vosotros {vos}", f"ellos {ellos}", f"ellas {ellos}", f"Uds. {ellos}"]
    items = [obs(header, x, top)]
    for row, (left, right) in enumerate(zip(sg, pl)):
        y = top - 0.15 - row * step
        items.append(obs(left, x, y))
        items.append(obs(right, x + 0.2, y))
    return items


FOLMAR = ("folmo", "folmas", "folma", "folmamos", "folmáis", "folman")
TUMER = ("tumo", "tumes", "tume", "tumemos", "tuméis", "tumen")
RISTIR = ("risto", "ristes", "riste", "ristimos", "ristís", "risten")


def cards_of(img, chapter=5):
    report = Counter()
    return parse_image({**img, "chapter": chapter}, report), report


def spanish_by_pronoun(cards):
    return {card.conjugation.pronoun: card.spanish for card in cards}


class ParseCellsTests(unittest.TestCase):
    def test_pronoun_and_form(self):
        cell = parse_cells("ella folma")[0]
        self.assertEqual((cell["slot"], cell["clitic"], cell["form"]), ("3sg", None, "folma"))

    def test_two_cells_in_one_observation(self):
        cells = parse_cells("Ud. folma Uds. folman")
        self.assertEqual([(c["slot"], c["form"]) for c in cells], [("3sg", "folma"), ("3pl", "folman")])
        self.assertGreater(cells[1]["start"], cells[0]["start"])

    def test_ud_without_a_dot(self):
        self.assertEqual(parse_cells("Uds folman")[0]["slot"], "3pl")

    def test_reflexive_cells_with_and_without_a_pronoun(self):
        self.assertEqual([(c["slot"], c["clitic"]) for c in parse_cells("me folmo")], [("1sg", "me")])
        self.assertEqual([(c["slot"], c["clitic"]) for c in parse_cells("nos folmamos")], [("1pl", "nos")])
        self.assertEqual([(c["slot"], c["clitic"]) for c in parse_cells("él se folma")], [("3sg", "se")])
        self.assertEqual([(c["slot"], c["clitic"]) for c in parse_cells("Uds. se folman")], [("3pl", "se")])

    def test_tu_and_vosotros_cells_have_no_slot(self):
        self.assertIsNone(parse_cells("tú folmas")[0]["slot"])
        self.assertIsNone(parse_cells("vosotros folmáis")[0]["slot"])
        self.assertIsNone(parse_cells("te folmas")[0]["slot"])

    def test_english_beside_a_cell_is_ignored(self):
        cells = parse_cells("yo folmo I blorp, 1 blorp")
        self.assertEqual([(c["slot"], c["form"]) for c in cells], [("1sg", "folmo")])
        self.assertEqual(parse_cells("Ud. se folma you blorp yourself")[0]["clitic"], "se")

    def test_ocr_slips_in_a_pronoun_or_a_trailing_full_stop(self):
        self.assertEqual(parse_cells("é folma")[0]["slot"], "3sg")
        self.assertEqual(parse_cells("ella se folma.")[0]["form"], "folma")

    def test_a_noun_phrase_is_not_a_cell(self):
        self.assertIsNone(parse_cells("el patio"))
        self.assertIsNone(parse_cells("la mesa"))

    def test_not_a_cell(self):
        for text in ("folmar to blorp", "I blorp", "yo", "yo folmo mucho", "to blorp"):
            self.assertIsNone(parse_cells(text), text)


class CheckSlotTests(unittest.TestCase):
    def test_regular_forms(self):
        self.assertEqual(check_slot("folmar", "1sg", "folmo"), "exact")
        self.assertEqual(check_slot("folmar", "3sg", "folma"), "exact")
        self.assertEqual(check_slot("tumer", "3sg", "tume"), "exact")
        self.assertEqual(check_slot("ristir", "1pl", "ristimos"), "exact")
        self.assertEqual(check_slot("folmar", "3pl", "folman"), "exact")

    def test_an_ocr_slip_is_not_accepted(self):
        for slot, form in (("1sg", "folmu"), ("3sg", "folme"), ("1pl", "folmamas"), ("3pl", "folmen"), ("3sg", "fojma")):
            self.assertIsNone(check_slot("folmar", slot, form), form)

    def test_stem_change_in_yo_and_third_person_but_not_nosotros(self):
        self.assertEqual(check_slot("pensar", "3sg", "piensa"), "exact")
        self.assertEqual(check_slot("pensar", "1pl", "pensamos"), "exact")
        self.assertIsNone(check_slot("pensar", "1pl", "pienamos"))
        self.assertEqual(check_slot("fermar", "3sg", "fierma"), "guess")  # not in the stem-change list

    def test_g_and_zc_yo_forms_are_guessed_but_endings_are_checked(self):
        self.assertEqual(check_slot("tumer", "1sg", "tumgo"), "guess")
        self.assertIsNone(check_slot("tumer", "1sg", "xumgo"))

    def test_a_yo_slip_that_keeps_the_first_letters_is_not_accepted(self):
        for form in ("folbro", "folcho", "folmu", "folmaro"):
            self.assertIsNone(check_slot("folmar", "1sg", form), form)
        self.assertEqual(check_slot("hacer", "1sg", "hago"), "guess")
        self.assertEqual(check_slot("conocer", "1sg", "conozco"), "guess")
        self.assertEqual(check_slot("caer", "1sg", "caigo"), "guess")
        self.assertEqual(check_slot("seguir", "1sg", "sigo"), "guess")

    def test_irregular_verbs(self):
        self.assertEqual(check_slot("ser", "1sg", "soy"), "exact")
        self.assertEqual(check_slot("ser", "3pl", "son"), "exact")
        self.assertEqual(check_slot("ser", "1pl", "somos"), "exact")
        self.assertEqual(check_slot("ir", "1pl", "vamos"), "exact")
        self.assertEqual(check_slot("estar", "3sg", "está"), "exact")
        self.assertEqual(check_slot("estar", "3pl", "están"), "exact")
        self.assertIsNone(check_slot("ser", "1sg", "estoy"))


class ParseImageTests(unittest.TestCase):
    def test_one_verb_makes_nine_cards_in_order(self):
        cards, report = cards_of(image("p100_00.png", block("folmar to blorp", FOLMAR)))
        self.assertEqual([card.conjugation.pronoun for card in cards],
                         ["yo", "vos", "él", "ella", "Ud.", "nosotros", "ellos", "ellas", "Uds."])
        self.assertEqual(spanish_by_pronoun(cards), {
            "yo": "yo folmo", "vos": "vos folmás", "él": "él folma", "ella": "ella folma", "Ud.": "Ud. folma",
            "nosotros": "nosotros folmamos", "ellos": "ellos folman", "ellas": "ellas folman", "Uds.": "Uds. folman",
        })
        self.assertTrue(all(card.kind == CONJUGATION and card.tense == "present" and card.english == "" for card in cards))
        self.assertEqual(cards[0].conjugation, ConjugationSource("folmar", "yo", "to blorp"))
        self.assertEqual(report["conjugations.verbs"], 1)

    def test_no_tu_or_vosotros_card(self):
        cards, _ = cards_of(image("p100_00.png", block("folmar to blorp", FOLMAR)))
        text = " ".join(card.spanish for card in cards)
        self.assertNotIn("tú", text)
        self.assertNotIn("vosotros", text)
        self.assertNotIn("folmáis", text)
        self.assertNotIn("folmas", text.replace("folmás", ""))

    def test_vos_follows_the_infinitive_class_without_a_stem_change(self):
        for header, forms, vos in (("tumer to zint", TUMER, "vos tumés"), ("ristir to wibble", RISTIR, "vos ristís")):
            cards, _ = cards_of(image("p100_00.png", block(header, forms)))
            self.assertEqual(spanish_by_pronoun(cards)["vos"], vos)
        stem = ("fierma", "fiermas", "fierma", "fermamos", "fermáis", "fiermen")
        cards, _ = cards_of(image("p100_00.png", block("fermar to zint", stem)))
        self.assertEqual(spanish_by_pronoun(cards)["vos"], "vos fermás")
        self.assertEqual(spanish_by_pronoun(cards)["nosotros"], "nosotros fermamos")

    def test_two_verbs_side_by_side_are_split_by_header_x(self):
        left = block("folmar to blorp", FOLMAR, x=0.0)
        right = block("tumer to zint", TUMER, x=0.5)
        cards, report = cards_of(image("p100_01.png", left + right))
        self.assertEqual(report["conjugations.verbs"], 2)
        self.assertEqual(spanish_by_pronoun(cards[:9])["nosotros"], "nosotros folmamos")
        self.assertEqual(spanish_by_pronoun(cards[9:])["nosotros"], "nosotros tumemos")
        self.assertEqual({card.conjugation.infinitive for card in cards[:9]}, {"folmar"})
        self.assertEqual({card.conjugation.infinitive for card in cards[9:]}, {"tumer"})

    def test_stacked_verbs_with_their_own_headers(self):
        top = block("folmar to blorp", FOLMAR, top=0.95, step=0.07)
        bottom = block("ristir to wibble", RISTIR, top=0.45, step=0.07)
        cards, report = cards_of(image("p100_01.png", top + bottom))
        self.assertEqual([card.conjugation.infinitive for card in cards], ["folmar"] * 9 + ["ristir"] * 9)

    def test_merged_cells_in_one_observation(self):
        items = [
            obs("folmar to blorp", 0.0, 0.95),
            obs("yo folmo", 0.0, 0.8), obs("nosotros folmamos", 0.2, 0.8),
            obs("Ud. folma Uds. folman", 0.0, 0.65, width=0.5),
        ]
        cards, _ = cards_of(image("p100_00.png", items))
        self.assertEqual(spanish_by_pronoun(cards)["Uds."], "Uds. folman")
        self.assertEqual(spanish_by_pronoun(cards)["Ud."], "Ud. folma")

    def test_missing_cells_give_only_the_certain_cards(self):
        items = [
            obs("folmar to blorp", 0.0, 0.95), obs("yo folmo", 0.0, 0.8), obs("nosotros folmamos", 0.2, 0.8),
            obs("vosotros folmáis", 0.2, 0.7),
        ]
        cards, report = cards_of(image("p100_00.png", items))
        self.assertEqual([card.conjugation.pronoun for card in cards], ["yo", "vos", "nosotros"])
        self.assertEqual(report["conjugations.verbs_partial"], 1)

    def test_a_broken_form_is_skipped_and_counted(self):
        broken = ("folmo", "folmas", "folme", "folmamos", "folmáis", "folman")
        cards, report = cards_of(image("p100_00.png", block("folmar to blorp", broken)))
        pronouns = {card.conjugation.pronoun for card in cards}
        self.assertTrue({"él", "ella", "Ud."}.isdisjoint(pronouns))
        self.assertIn("yo", pronouns)
        self.assertEqual(report["conjugations.forms_unverified"], 1)

    def test_conflicting_cells_for_a_slot_are_dropped(self):
        items = block("folmar to blorp", FOLMAR)
        items = [obs("ella folmo", 0.0, 0.47) if item["text"] == "ella folma" else item for item in items]
        cards, report = cards_of(image("p100_00.png", items))
        self.assertTrue({"él", "ella", "Ud."}.isdisjoint({card.conjugation.pronoun for card in cards}))
        self.assertEqual(report["conjugations.slots_conflicting"], 1)

    def test_a_verb_whose_forms_do_not_fit_the_infinitive_is_skipped(self):
        wrong = ("tumo", "tumes", "tume", "tumemos", "tuméis", "tumen")
        cards, report = cards_of(image("p100_00.png", block("folmar to blorp", wrong)))
        self.assertEqual(cards, [])
        self.assertEqual(report["conjugations.verbs_skipped_unconfirmed"], 1)

    def test_reflexive_verb(self):
        items = [
            obs("folmarse to blorp oneself", 0.0, 0.95),
            obs("me folmo", 0.0, 0.8), obs("nos folmamos", 0.25, 0.8),
            obs("te folmas", 0.0, 0.7), obs("os folmáis", 0.25, 0.7),
            obs("él se folma", 0.0, 0.6), obs("ellos se folman", 0.25, 0.6),
            obs("Ud. se folma", 0.0, 0.5), obs("Uds. se folman", 0.25, 0.5),
        ]
        cards, _ = cards_of(image("p277_00.png", items), chapter=12)
        self.assertEqual(spanish_by_pronoun(cards), {
            "yo": "yo me folmo", "vos": "vos te folmás", "él": "él se folma", "ella": "ella se folma",
            "Ud.": "Ud. se folma", "nosotros": "nosotros nos folmamos", "ellos": "ellos se folman",
            "ellas": "ellas se folman", "Uds.": "Uds. se folman",
        })

    def test_reflexive_cells_without_the_clitic_are_dropped(self):
        items = [
            obs("folmarse to blorp oneself", 0.0, 0.95),
            obs("nos folmamos", 0.25, 0.8), obs("él folma", 0.0, 0.6), obs("os folmáis", 0.25, 0.7),
        ]
        cards, report = cards_of(image("p277_00.png", items), chapter=12)
        self.assertEqual([card.conjugation.pronoun for card in cards], ["vos", "nosotros"])
        self.assertEqual(report["conjugations.cells_wrong_reflexive"], 1)

    def test_headerless_irregular_table_is_recognised_by_its_yo_form(self):
        items = [
            obs("yo soy", 0.0, 0.9), obs("nosotros somos", 0.5, 0.9), obs("I am", 0.2, 0.9),
            obs("tú eres", 0.0, 0.7), obs("vosotros sois", 0.5, 0.7),
            obs("él es", 0.0, 0.5), obs("ellos son", 0.5, 0.5),
            obs("ella es", 0.0, 0.3), obs("ellas son", 0.5, 0.3),
            obs("Ud. es", 0.0, 0.1), obs("Uds. son", 0.5, 0.1),
        ]
        cards, _ = cards_of(image("p051_01.png", items), chapter=2)
        spanish = spanish_by_pronoun(cards)
        self.assertEqual(spanish["yo"], "yo soy")
        self.assertEqual(spanish["vos"], "vos sos")
        self.assertEqual(spanish["ellas"], "ellas son")
        self.assertEqual(cards[0].conjugation.infinitive, "ser")

    def test_a_table_without_header_or_known_yo_form_gives_nothing(self):
        items = [obs("yo folmo", 0.0, 0.9), obs("nosotros folmamos", 0.5, 0.9), obs("Uds. folman", 0.5, 0.5)]
        cards, report = cards_of(image("p100_00.png", items))
        self.assertEqual(cards, [])
        self.assertEqual(report["conjugations.tables_without_verb"], 1)

    def test_gloss_from_the_header_only_when_complete(self):
        cards, _ = cards_of(image("p100_00.png", block("folmar to blorp (a wibble)", FOLMAR)))
        self.assertEqual(cards[0].conjugation.gloss, "to blorp (a wibble)")
        cards, _ = cards_of(image("p100_00.png", block("folmar to blorp,", FOLMAR)))
        self.assertEqual(cards[0].conjugation.gloss, "")

    def test_a_gloss_wrapped_onto_the_next_line_is_left_to_the_word_card(self):
        items = block("folmar to blorp", FOLMAR) + [obs("up and down", 0.0, 0.89)]
        cards, _ = cards_of(image("p100_00.png", items))
        self.assertEqual(cards[0].conjugation.gloss, "")

    def test_gloss_on_its_own_line_under_the_infinitive(self):
        items = block("folmarse (los wibbles)", FOLMAR, top=0.95) + [obs("to blorp (one's wibbles)", 0.0, 0.9)]
        cards, _ = cards_of(image("p277_00.png", items), chapter=12)
        # a reflexive verb needs reflexive cells, so nothing is made, but the header must not break the parse
        self.assertEqual(cards, [])

    def test_other_chapters_and_command_or_example_tables_are_ignored(self):
        img = image("p400_00.png", block("folmar to blorp", FOLMAR))
        self.assertEqual(parse_image({**img, "chapter": 15}, Counter()), [])
        sentences = image("p139_00.png", [
            obs("tratar de + infinitive to try to", 0.0, 0.95),
            obs("yo trato de leer", 0.05, 0.8), obs("nosotros tratamos de escribir", 0.05, 0.6),
        ])
        self.assertEqual(cards_of(sentences)[0], [])

    def test_an_infinitive_printed_twice_uses_the_header_with_the_gloss(self):
        items = block("folmar to blorp", FOLMAR) + [obs("folmar", 0.0, 0.88)]
        cards, report = cards_of(image("p100_03.png", items))
        self.assertEqual(len(cards), 9)
        self.assertEqual(cards[0].conjugation.gloss, "to blorp")
        self.assertEqual(report["conjugations.verbs_skipped_no_forms"], 0)

    def test_a_lone_noun_that_ends_like_an_infinitive_is_not_a_header(self):
        items = block("folmar to blorp", FOLMAR) + [obs("lugar", 0.0, 0.88), obs("mujer", 0.2, 0.5)]
        cards, report = cards_of(image("p100_00.png", items))
        self.assertEqual({card.conjugation.infinitive for card in cards}, {"folmar"})
        self.assertEqual(len(cards), 9)

    def test_an_infinitive_that_lost_its_accent_is_restored(self):
        forms = ("oigo", "oyes", "oye", "oímos", "oís", "oyen")
        cards, _ = cards_of(image("p124_01.png", block("oir to hear", forms)), chapter=6)
        self.assertEqual(cards[0].conjugation.infinitive, "oír")
        self.assertEqual(spanish_by_pronoun(cards)["vos"], "vos oís")
        self.assertEqual(spanish_by_pronoun(cards)["nosotros"], "nosotros oímos")

    def test_e_to_i_verbs_may_have_their_own_yo_form(self):
        forms = ("pigo", "piles", "pile", "pelimos", "pelís", "pilen")
        cards, report = cards_of(image("p123_01.png", block("pelir to blorp", forms)), chapter=6)
        self.assertIn("yo", spanish_by_pronoun(cards))
        self.assertEqual(report["conjugations.forms_guessed"], 3)

    def test_english_printed_beside_the_cells_does_not_stop_the_parse(self):
        items = [
            obs("folmarse to blorp oneself", 0.0, 0.95),
            obs("yo me folmo I blorp myself", 0.0, 0.8, width=0.5), obs("nosotros", 0.5, 0.8), obs("nos folmamos", 0.5, 0.7),
            obs("Ud. se folma you blorp yourself", 0.0, 0.5, width=0.5), obs("Uds. se folman", 0.5, 0.5),
        ]
        cards, _ = cards_of(image("p272_00.png", items), chapter=12)
        self.assertEqual(spanish_by_pronoun(cards)["yo"], "yo me folmo")
        self.assertEqual(spanish_by_pronoun(cards)["nosotros"], "nosotros nos folmamos")
        self.assertEqual(spanish_by_pronoun(cards)["Uds."], "Uds. se folman")

    def test_the_present_chapters(self):
        self.assertEqual(PRESENT_CHAPTERS, {2, 5, 6, 7, 12})

    def test_no_chapter_means_no_gating(self):
        cards = parse_image(image("p100_00.png", block("folmar to blorp", FOLMAR)), Counter())
        self.assertEqual(len(cards), 9)


class ResolveTests(unittest.TestCase):
    def conj(self, infinitive="folmar", pronoun="ella", gloss="to have blorp", spanish="ella folma"):
        return Card(spanish, "", CONJUGATION, tense="present", conjugation=ConjugationSource(infinitive, pronoun, gloss))

    def test_english_from_the_header_gloss(self):
        card = resolve(self.conj(), {}, Counter())
        self.assertEqual((card.spanish, card.english, card.kind, card.tense), ("ella folma", "she has blorp", CONJUGATION, "present"))

    def test_missing_gloss_comes_from_the_word_card(self):
        glosses = gloss_index([Card("folmar", "to blorp, to zint", WORD)])
        card = resolve(self.conj(gloss=""), glosses, Counter())
        self.assertEqual(card.english, "she blorps")

    def test_unknown_gloss_is_skipped_and_counted(self):
        report = Counter()
        self.assertIsNone(resolve(self.conj(gloss=""), {}, report))
        self.assertEqual(report["conjugations.cards_skipped_no_gloss"], 1)

    def test_unusable_gloss_is_skipped_and_counted(self):
        report = Counter()
        self.assertIsNone(resolve(self.conj(gloss="to 4blorp"), {}, report))
        self.assertEqual(report["conjugations.cards_skipped_bad_gloss"], 1)

    def test_verbs_with_the_same_english_in_a_chapter_get_the_infinitive_added(self):
        entries = [
            (2, 47, self.conj("ser", "yo", "to be", "yo soy")),
            (2, 47, self.conj("estar", "yo", "to be", "yo estoy")),
            (2, 47, self.conj("estar", "Uds.", "to be", "Uds. están")),
            (2, 51, self.conj("ser", "Uds.", "to be", "Uds. son")),
        ]
        result = [(chapter, card.spanish, card.english) for chapter, _, card in resolve_all(entries, {}, Counter())]
        self.assertEqual(result, [
            (2, "yo soy", "I am (ser)"), (2, "yo estoy", "I am (estar)"),
            (2, "Uds. están", "you all are (estar)"), (2, "Uds. son", "you all are (ser)"),
        ])

    def test_the_same_english_in_another_chapter_or_for_one_verb_is_left_alone(self):
        entries = [
            (5, 100, self.conj("folmar", "yo", "to blorp", "yo folmo")),
            (6, 120, self.conj("tumer", "yo", "to blorp", "yo tumo")),
            (6, 121, self.conj("tumer", "yo", "to blorp", "yo tumo")),  # the same verb printed twice
        ]
        report = Counter()
        english = [card.english for _, _, card in resolve_all(entries, {}, report)]
        self.assertEqual(english, ["I blorp"] * 3)
        self.assertEqual(report["conjugations.prompts_disambiguated"], 0)

    def test_resolved_cards_no_longer_carry_a_conjugation_source(self):
        entries = [(5, 100, self.conj())]
        self.assertIsNone(resolve_all(entries, {}, Counter())[0][2].conjugation)

    def test_cards_that_cannot_be_resolved_are_dropped_and_other_cards_pass_through(self):
        word = Card("la mesa", "the table", WORD)
        entries = [(5, 100, word), (5, 100, self.conj(gloss=""))]
        report = Counter()
        self.assertEqual(resolve_all(entries, {}, report), [(5, 100, word)])
        self.assertEqual(report["conjugations.cards_skipped_no_gloss"], 1)

    def test_reflexive_infinitive_is_found_in_the_index(self):
        glosses = gloss_index([Card("folmarse (el wibble)", "to blorp up", WORD)])
        self.assertEqual(glosses, {"folmarse": "to blorp up"})
        card = resolve(self.conj("folmarse", "él", "", "él se folma"), glosses, Counter())
        self.assertEqual(card.english, "he blorps up")

    def test_gloss_index_ignores_sentences_and_non_verbs(self):
        cards = [Card("la casa", "the house", WORD), Card("folmar", "to blorp", "sentence"), Card("folmar", "blorp", WORD)]
        self.assertEqual(gloss_index(cards), {})


class PipelineTests(unittest.TestCase):
    """build_vocabulary wires the parser in: chapter gating, gloss recovery, dedupe and counts."""

    def run_pipeline(self, images, starts=None):
        import json
        import tempfile
        from pathlib import Path

        starts = starts or {1: 1, 2: 40, 3: 60, 4: 80, 5: 100}
        titles = [f"Chapter {number}" for number in range(1, 6)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ocr.json"
            path.write_text(json.dumps(images))
            return build_vocabulary(path, starts, titles)

    def test_cards_land_in_the_chapter_of_the_table_with_english(self):
        images = [image("p105_00.png", block("folmar to blorp", FOLMAR))]
        vocabulary, stats = self.run_pipeline(images)
        words = vocabulary["chapters"][4]["words"]
        conjugations = [word for word in words if word.get("kind") == "conjugation"]
        self.assertEqual(len(conjugations), 9)
        self.assertEqual(
            {word["spanish"]: word["english"] for word in conjugations},
            {
                "yo folmo": "I blorp", "vos folmás": "you blorp", "él folma": "he blorps", "ella folma": "she blorps",
                "Ud. folma": "you (formal) blorp", "nosotros folmamos": "we blorp",
                "ellos folman": "they (m.) blorp", "ellas folman": "they (f.) blorp", "Uds. folman": "you all blorp",
            },
        )
        self.assertTrue(all(word["tense"] == "present" and word["sourcePage"] == 105 for word in conjugations))
        self.assertEqual(stats["cardsByChapter"]["5"]["conjugation"], 9)

    def test_gloss_recovered_from_an_infinitive_word_card(self):
        header_only = [obs("folmar to blorp,", 0.0, 0.95)] + block("folmar", FOLMAR)[1:]
        words = [two_column_words()]
        vocabulary, stats = self.run_pipeline(words + [image("p105_00.png", header_only)])
        conjugations = [w for w in vocabulary["chapters"][4]["words"] if w.get("kind") == "conjugation"]
        self.assertEqual(len(conjugations), 9)
        self.assertEqual(conjugations[0]["english"], "I blorp")

    def test_unknown_gloss_skips_the_verb_and_counts_it(self):
        header_only = [obs("folmar (los wibbles)", 0.0, 0.95)] + block("folmar", FOLMAR)[1:]
        vocabulary, stats = self.run_pipeline([image("p105_00.png", header_only)])
        self.assertEqual([w for w in vocabulary["chapters"][4]["words"] if w.get("kind") == "conjugation"], [])
        self.assertEqual(stats["report"]["conjugations.cards_skipped_no_gloss"], 9)

    def test_other_tense_chapters_make_no_conjugation_cards(self):
        images = [image("p105_00.png", block("folmar to blorp", FOLMAR))]
        vocabulary, _ = self.run_pipeline(images, starts={1: 1, 2: 40, 3: 60, 4: 80, 5: 200})
        self.assertEqual([w for c in vocabulary["chapters"] for w in c["words"] if w.get("kind") == "conjugation"], [])

    def test_the_argentine_word_map_applies_to_the_forms(self):
        forms = ("conduzco", "conduces", "conduce", "conducimos", "conducís", "conducen")
        vocabulary, _ = self.run_pipeline([image("p105_00.png", block("conducir to drive", forms))])
        spanish = {w["english"]: w["spanish"] for w in vocabulary["chapters"][4]["words"] if w.get("kind") == "conjugation"}
        self.assertEqual(spanish["I drive"], "yo manejo")
        self.assertEqual(spanish["you drive"], "vos manejás")
        self.assertEqual(spanish["we drive"], "nosotros manejamos")

    def test_a_verb_repeated_in_a_chapter_is_deduplicated(self):
        images = [
            image("p105_00.png", block("folmar to blorp", FOLMAR)),
            image("p106_00.png", block("folmar to blorp", FOLMAR)),
        ]
        vocabulary, stats = self.run_pipeline(images)
        self.assertEqual(stats["cardsByChapter"]["5"]["conjugation"], 9)
        self.assertEqual(stats["report"]["duplicates.conjugation"], 9)


def two_column_words():
    from ocr_fixtures import two_columns

    return two_columns([("folmar", "to blorp"), ("la mesa", "the table")], name="p104_00.png")


if __name__ == "__main__":
    unittest.main()
