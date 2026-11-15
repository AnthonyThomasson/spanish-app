"""Present-tense conjugation cards from the book's conjugation tables (kind 'conjugation').

A table image has a header per verb ("infinitive + to-gloss") with a singular and a plural column of
"pronoun + form" cells; two to four verbs often sit side by side. The parser splits an image into
verbs by header position, reads the pronoun cells, and checks every form against the infinitive
(an OCR slip, or a form the rules cannot explain, is skipped and counted, never guessed).

Cards: yo, vos, él, ella, Ud., nosotros, ellos, ellas, Uds. The book's tú and vosotros cells are not
used. The Argentine vos form is generated (`spanish_verbs.vos_present`); él/ella/Ud. share the table's
third-person singular form and ellos/ellas/Uds. its plural. The English is generated from the verb's
gloss (`conjugation_english`). The gloss comes from the table header when it is clean, otherwise from the
infinitive's word card, which only exists in the second pass: `parse_image` therefore returns cards with
no English and a `ConjugationSource`, and `resolve` finishes them.
"""

import re
from collections import Counter
from pathlib import Path

from card_types import CONJUGATION, WORD, Card, ConjugationSource
from conjugation_english import conjugate_english
from ocr_layout import IGNORED_IMAGES, clean_text, center_y
from spanish_verbs import split_reflexive, strip_accents, tu_present_forms, verb_class, vos_present

TENSE = "present"
# Chapters that teach the present tense in tables: ser/estar, regular, stem-changing and irregular verbs,
# ir, and reflexive verbs. Other chapters' tables are other tenses and are left alone.
PRESENT_CHAPTERS = {2, 5, 6, 7, 12}

LETTERS = r"[a-záéíóúñü]+"
INFINITIVE = re.compile(rf"(?:{LETTERS}(?:ar|er|ir|ír)|ir)(?:se)?")
HEADER = re.compile(
    rf"^(?P<infinitive>{INFINITIVE.pattern})\s*(?P<paren>\([^)]*\))?\s*(?P<gloss>(?:to|can|must|may|should)\b.*)?$",
    re.IGNORECASE,
)
FORM = re.compile(LETTERS, re.IGNORECASE)
# Some tables print the English beside a cell ("yo voy I go"): everything from the English subject on is dropped.
ENGLISH_TAIL_START = {"i", "1", "l", "you", "he", "she", "we", "they"}

# Pronoun word in a table cell -> person slot (None for tú / vosotros, which are not used).
PRONOUN_SLOTS = {
    "yo": "1sg", "él": "3sg", "é": "3sg", "ella": "3sg", "ud": "3sg", "usted": "3sg",
    "nosotros": "1pl", "nosotras": "1pl",
    "ellos": "3pl", "ellas": "3pl", "uds": "3pl", "ustedes": "3pl",
    "tú": None, "tu": None, "vosotros": None, "vosotras": None,
}
CLITIC_SLOTS = {"me": "1sg", "nos": "1pl", "te": None, "os": None}
SLOT_CLITIC = {"1sg": "me", "1pl": "nos", "3sg": "se", "3pl": "se"}
PRONOUN_CLITICS = {"yo": "me", "nosotros": "nos", "nosotras": "nos", "tú": "te", "tu": "te", "vosotros": "os", "vosotras": "os"}
SLOT_PRONOUNS = {
    "1sg": ["yo"],
    "3sg": ["él", "ella", "Ud."],
    "1pl": ["nosotros"],
    "3pl": ["ellos", "ellas", "Uds."],
}
CARD_ORDER = ["yo", "vos", "él", "ella", "Ud.", "nosotros", "ellos", "ellas", "Uds."]

# Irregular present forms the endings rule cannot predict (accents ignored when compared).
IRREGULAR_FORMS = {
    "ser": {"1sg": {"soy"}, "3sg": {"es"}, "1pl": {"somos"}, "3pl": {"son"}},
    "ir": {"1sg": {"voy"}, "3sg": {"va"}, "1pl": {"vamos"}, "3pl": {"van"}},
    "estar": {"1sg": {"estoy"}},
    "dar": {"1sg": {"doy"}},
    "ver": {"1sg": {"veo"}},
    "saber": {"1sg": {"se"}},
    "oír": {"1sg": {"oigo"}},
    "haber": {"1sg": {"he"}, "3sg": {"ha"}, "1pl": {"hemos"}, "3pl": {"han"}},
}
# A table without a header (the ser / estar / ir tables) is recognised by its yo form.
HEADERLESS_YO = {"soy": ("ser", "to be"), "estoy": ("estar", "to be"), "voy": ("ir", "to go")}
# Headers whose accent the OCR dropped or whose letters it misread; only forms no Spanish word shares.
HEADER_FIXES = {"oir": "oír", "reir": "reír", "reirse": "reírse", "sonreir": "sonreír", "lamarse": "llamarse"}
STEM_CHANGES = (("e", "ie"), ("e", "i"), ("o", "ue"), ("u", "ue"))

MIN_CELLS = 3  # fewer pronoun cells than this is not a conjugation table
COLUMN_TOLERANCE = 0.06
CELL_X_SLACK = 0.04
GLOSS_LINE_GAP = 0.075


def fold(text: str) -> str:
    return strip_accents(text.lower())


# ---- cells and headers ---------------------------------------------------------

def parse_cells(text: str) -> list[dict] | None:
    """'Ud. piensa Uds. piensan' -> two cells. None when the text is not made only of pronoun cells.

    A cell is `pronoun [clitic] form` or `clitic form` (reflexive tables leave out yo / nosotros / tú / vosotros).
    Each cell records `start`, its character offset, so a merged observation can be placed in its column.
    """
    tokens = [(match.group(0), match.start()) for match in re.finditer(r"\S+", text)]
    cells = []
    index = 0
    while index < len(tokens):
        word, start = tokens[index]
        key = word.lower().rstrip(".")
        clitic = None
        if key in PRONOUN_SLOTS:
            slot, expected_clitic = PRONOUN_SLOTS[key], PRONOUN_CLITICS.get(key, "se")
            index += 1
            if index < len(tokens) and tokens[index][0].lower() == expected_clitic:
                clitic = expected_clitic
                index += 1
        elif key in CLITIC_SLOTS:
            slot, clitic = CLITIC_SLOTS[key], key
            index += 1
        else:
            return None
        form = tokens[index][0].rstrip(".,;") if index < len(tokens) else ""
        if not FORM.fullmatch(form):
            return None
        cells.append({"slot": slot, "clitic": clitic, "form": form.lower(), "start": start})
        index += 1
        if index < len(tokens) and tokens[index][0].lower() in ENGLISH_TAIL_START:
            break
    return cells or None


def parse_header(text: str) -> dict | None:
    match = HEADER.match(text.strip())
    if not match:
        return None
    gloss = (match.group("gloss") or "").strip()
    return {"infinitive": match.group("infinitive").lower(), "gloss": gloss, "has_paren": bool(match.group("paren"))}


def clean_gloss(gloss: str) -> str:
    """The header's gloss when it is complete on one line, else '' (the word card's gloss is used instead)."""
    gloss = gloss.strip()
    if not gloss or gloss.endswith((",", ";", "-")) or gloss.count("(") != gloss.count(")"):
        return ""
    return gloss


def column_anchors(headers: list[dict]) -> list[float]:
    anchors: list[float] = []
    for x in sorted(header["x"] for header in headers):
        if not anchors or x - anchors[-1] > COLUMN_TOLERANCE:
            anchors.append(x)
    return anchors


def assign_blocks(headers: list[dict], cells: list[dict]) -> dict[int, list[dict]]:
    """Cells per header index: the cell's column is the right-most header column at or left of its x,
    and its block is the nearest header above it in that column."""
    anchors = column_anchors(headers)
    blocks: dict[int, list[dict]] = {index: [] for index in range(len(headers))}
    for cell in cells:
        columns = [anchor for anchor in anchors if anchor <= cell["x"] + CELL_X_SLACK]
        if not columns:
            continue
        anchor = columns[-1]
        above = [
            index for index, header in enumerate(headers)
            if abs(header["x"] - anchor) <= COLUMN_TOLERANCE and header["y"] >= cell["y"] - 0.02
        ]
        if above:
            blocks[min(above, key=lambda index: headers[index]["y"] - cell["y"])].append(cell)
    return blocks


def one_header_per_verb(headers: list[dict]) -> list[dict]:
    """An infinitive can be printed twice (a header, then the word again in a stem / ending diagram):
    keep the header with a gloss, or the top one."""
    kept: dict[str, dict] = {}
    for header in sorted(headers, key=lambda item: -item["y"]):
        current = kept.get(header["infinitive"])
        if current is None or (not current["gloss"] and header["gloss"]):
            kept[header["infinitive"]] = header
    return [header for header in headers if kept[header["infinitive"]] is header]


def read_image(observations: list[dict], report: Counter) -> tuple[list[dict], list[dict]]:
    """(headers, cells) of one image, each with the x / y of their text."""
    headers, cells, others = [], [], []
    for observation in observations:
        text = clean_text(observation["text"], "es")
        y = center_y(observation)
        parsed = parse_cells(text)
        if parsed:
            for cell in parsed:
                offset = observation["width"] * cell["start"] / max(len(text), 1)
                cells.append({**cell, "x": observation["x"] + offset, "y": y})
            continue
        mixed = clean_text(observation["text"])  # a header holds Spanish and English
        header = parse_header(mixed)
        if header:
            header["infinitive"] = HEADER_FIXES.get(header["infinitive"], header["infinitive"])
            headers.append({**header, "x": observation["x"], "y": y})
        else:
            others.append({"text": mixed, "x": observation["x"], "y": y})
    headers = one_header_per_verb(headers)
    for header in headers:
        below = [
            item for item in others
            if abs(item["x"] - header["x"]) <= 0.04 and 0 < header["y"] - item["y"] <= GLOSS_LINE_GAP
            and not re.match(r"^(?:I|you|he|she|we|they)\b", item["text"])
        ]
        header["inline_gloss"] = bool(header["gloss"])
        header["gloss"] = clean_gloss(header["gloss"])
        if below and header["gloss"]:
            header["gloss"] = ""  # the gloss wraps onto another line: the word card has the whole thing
        elif not header["gloss"] and len(below) == 1:
            header["gloss"] = clean_gloss(below[0]["text"]) if below[0]["text"].lower().startswith("to ") else ""
        header["has_gloss_line"] = bool(below) and any(item["text"].lower().startswith("to ") for item in below)
    # A lone infinitive-looking word ("lugar", a label) is a header only with a gloss, a parenthetical
    # ("cepillarse (los dientes)") or a "to ..." line under it.
    headers = [
        header for header in headers
        if header["gloss"] or header["has_paren"] or header["has_gloss_line"] or header["inline_gloss"]
    ]
    return headers, cells


# ---- checking the forms ----------------------------------------------------------

def predicted_stems(base: str) -> set[str]:
    """Stems the present endings attach to for yo / 3rd person, from the tú forms the verb rules produce."""
    folded = (fold(form) for form in tu_present_forms(base))
    return {form[:-2] for form in folded if form.endswith(("as", "es"))}


def stem_change_matches(stem: str, observed: str) -> bool:
    """True when `observed` is `stem` with one vowel turned into a stem-change diphthong (pens -> piens)."""
    for old, new in STEM_CHANGES:
        for index, letter in enumerate(stem):
            if letter == old and stem[:index] + new + stem[index + 1:] == observed:
                return True
    return False


YO_IRREGULAR_SUFFIXES = ("zc", "ig", "g", "j")


def has_irregular_yo_ending(plain_stem: str, stem: str) -> bool:
    """True for a yo stem that is the verb's stem (or its stem-change variant) plus g / zc / ig / j,
    allowing the stem's last letters to give way (hac- -> hag-, conoc- -> conozc-, segu- -> sig-)."""
    variants = {plain_stem} | {
        plain_stem[:index] + new + plain_stem[index + 1:]
        for old, new in STEM_CHANGES for index, letter in enumerate(plain_stem) if letter == old
    }
    for suffix in YO_IRREGULAR_SUFFIXES:
        if stem.endswith(suffix) and len(stem) > len(suffix):
            rest = stem[: -len(suffix)]
            if any(variant.startswith(rest) and len(variant) - len(rest) <= 2 for variant in variants):
                return True
    return False


def check_slot(base: str, slot: str, form: str) -> str | None:
    """'exact' when the rules (or the irregular table) give this form, 'guess' when it fits a pattern
    the rules do not list (a stem change, a g/zc yo form), None when it cannot be explained."""
    folded = fold(form)
    if folded in IRREGULAR_FORMS.get(base, {}).get(slot, set()):
        return "exact"
    if slot in IRREGULAR_FORMS.get(base, {}):
        return None
    kind = verb_class(base)
    if kind is None:
        return None
    plain_stem = fold(base[:-2])
    if slot == "1pl":
        return "exact" if folded == plain_stem + {"ar": "amos", "er": "emos", "ir": "imos"}[kind] else None
    ending = {"1sg": "o", "3sg": "a" if kind == "ar" else "e", "3pl": "an" if kind == "ar" else "en"}[slot]
    if not folded.endswith(ending):
        return None
    stem = folded[: -len(ending)]
    if stem in predicted_stems(base):
        return "exact"
    if stem_change_matches(plain_stem, stem):
        return "guess"
    if slot == "1sg" and has_irregular_yo_ending(plain_stem, stem):
        return "guess"  # tengo, hago, salgo, conozco, sigo: the yo form has its own irregularity
    return None


def verify(base: str, forms: dict[str, str], report: Counter) -> tuple[dict[str, str], bool]:
    """(the forms that check out, whether the infinitive is confirmed by an exact 1pl / 3sg form)."""
    verified: dict[str, str] = {}
    exact: set[str] = set()
    for slot, form in forms.items():
        outcome = check_slot(base, slot, form)
        if outcome is None:
            report["conjugations.forms_unverified"] += 1
            continue
        if outcome == "guess":
            report["conjugations.forms_guessed"] += 1
        else:
            exact.add(slot)
        verified[slot] = form
    return verified, bool(exact & {"1pl", "3sg"})


# ---- the parser ----------------------------------------------------------------------

def block_forms(infinitive: str, cells: list[dict], report: Counter) -> dict[str, tuple[str, str | None]]:
    """slot -> form from a block's cells. A clitic must be there exactly when the verb is reflexive;
    cells that disagree about a slot's form are dropped."""
    _, reflexive = split_reflexive(infinitive)
    found: dict[str, set[str]] = {}
    for cell in cells:
        slot = cell["slot"]
        if slot is None:
            continue
        expected = SLOT_CLITIC[slot] if reflexive else None
        if cell["clitic"] != expected:
            report["conjugations.cells_wrong_reflexive"] += 1
            continue
        found.setdefault(slot, set()).add(cell["form"])
    forms = {}
    for slot, options in found.items():
        if len(options) > 1:
            report["conjugations.slots_conflicting"] += 1
            continue
        forms[slot] = next(iter(options))
    return forms


def verb_cards(infinitive: str, gloss: str, forms: dict[str, str], report: Counter) -> list[Card]:
    base, reflexive = split_reflexive(infinitive)
    verified, confirmed = verify(base, forms, report)
    vos = vos_present(infinitive)
    if not confirmed or not vos:
        report["conjugations.verbs_skipped_unconfirmed"] += 1
        return []
    texts = {"vos": f"vos {vos}"}
    for slot, form in verified.items():
        for pronoun in SLOT_PRONOUNS[slot]:
            clitic = f"{SLOT_CLITIC[slot]} " if reflexive else ""
            texts[pronoun] = f"{pronoun} {clitic}{form}"
    cards = [
        Card(texts[pronoun], "", CONJUGATION, tense=TENSE, conjugation=ConjugationSource(infinitive, pronoun, gloss))
        for pronoun in CARD_ORDER if pronoun in texts
    ]
    report["conjugations.verbs"] += 1
    if len(cards) < len(CARD_ORDER):
        report["conjugations.verbs_partial"] += 1
    return cards


def parse_image(image: dict, report: Counter) -> list[Card]:
    observations = image["observations"]
    chapter = image.get("chapter")
    if (chapter is not None and chapter not in PRESENT_CHAPTERS) or Path(image["path"]).name in IGNORED_IMAGES:
        return []
    headers, cells = read_image(observations, report)
    if len(cells) < MIN_CELLS:
        return []
    if not headers:
        yo = [cell["form"] for cell in cells if cell["slot"] == "1sg" and cell["form"] in HEADERLESS_YO]
        if len(yo) != 1:
            report["conjugations.tables_without_verb"] += 1
            return []
        infinitive, gloss = HEADERLESS_YO[yo[0]]
        headers = [{"infinitive": infinitive, "gloss": gloss, "x": min(cell["x"] for cell in cells), "y": 2.0}]
    report["conjugations.tables"] += 1
    blocks = assign_blocks(headers, cells)
    cards: list[Card] = []
    for index in sorted(blocks, key=lambda i: (-headers[i]["y"], headers[i]["x"])):
        header = headers[index]
        forms = block_forms(header["infinitive"], blocks[index], report)
        if not forms:
            report["conjugations.verbs_skipped_no_forms"] += 1
            continue
        cards.extend(verb_cards(header["infinitive"], header["gloss"], forms, report))
    return cards


# ---- second pass: English -----------------------------------------------------------------

def gloss_index(cards) -> dict[str, str]:
    """infinitive -> its word card's gloss ('to have lunch'), first card wins."""
    index: dict[str, str] = {}
    for card in cards:
        if card.kind == WORD and re.match(r"^to\b", card.english, re.IGNORECASE):
            infinitive = re.sub(r"\s*\(.*?\)", "", card.spanish).strip().lower()
            if INFINITIVE.fullmatch(infinitive):
                index.setdefault(infinitive, card.english)
    return index


def resolve(card: Card, glosses: dict[str, str], report: Counter) -> Card | None:
    """Give a conjugation card its English, or None (counted) when the gloss is unknown or unusable."""
    source = card.conjugation
    gloss = source.gloss or glosses.get(source.infinitive, "")
    if not gloss:
        report["conjugations.cards_skipped_no_gloss"] += 1
        return None
    english = conjugate_english(gloss, source.pronoun, split_reflexive(source.infinitive)[1])
    if english is None:
        report["conjugations.cards_skipped_bad_gloss"] += 1
        return None
    report["conjugations.cards"] += 1
    return Card(card.spanish, english, CONJUGATION, tense=card.tense, conjugation=source)


def resolve_all(entries: list[tuple[int, int, Card]], glosses: dict[str, str], report: Counter) -> list[tuple[int, int, Card]]:
    """Resolve every conjugation card of `entries` (chapter, page, card). Where two verbs in a chapter get
    the same English ('I return' for volver and devolver; 'I am' for ser and estar) the infinitive is added
    in parentheses, so each English prompt has one answer. The app treats a parenthetical as optional."""
    resolved: list[tuple[int, int, Card]] = []
    for chapter, page, card in entries:
        if card.conjugation:
            card = resolve(card, glosses, report)
            if card is None:
                continue
        resolved.append((chapter, page, card))
    verbs_by_prompt: dict[tuple[int, str], set[str]] = {}
    for chapter, _, card in resolved:
        if card.conjugation:
            verbs_by_prompt.setdefault((chapter, card.english), set()).add(card.conjugation.infinitive)
    result = []
    for chapter, page, card in resolved:
        if card.conjugation and len(verbs_by_prompt[(chapter, card.english)]) > 1:
            report["conjugations.prompts_disambiguated"] += 1
            card = Card(card.spanish, f"{card.english} ({card.conjugation.infinitive})", CONJUGATION, tense=card.tense)
        elif card.conjugation:
            card = Card(card.spanish, card.english, CONJUGATION, tense=card.tense)
        result.append((chapter, page, card))
    return result
