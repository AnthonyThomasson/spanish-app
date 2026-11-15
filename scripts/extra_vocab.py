"""Vocabulary the original two-column word parser missed (kind 'word').

* number tables: digits next to Spanish number words, with the English number words generated;
* interrogative words: list images (¿cómo? / how?) and the bold headings above the ch.3 examples;
* section lists: images split by Spanish headers (Verbos / Nombres / Adjetivos / Expresiones).
"""

import re
from collections import Counter
from pathlib import Path

from card_types import WORD, Card
from ocr_layout import (
    IGNORED_IMAGES,
    center_y,
    clean_text,
    clusters_by_x,
    match_rows,
    merge_row_observations,
)
from spanish_verbs import strip_accents

# ---- numbers ------------------------------------------------------------------------

SPANISH_UNITS = {
    "cero": 0, "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
    "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21,
    "veintiún": 21, "veintiuna": 21, "veintidós": 22, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
SPANISH_TENS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}
SPANISH_HUNDREDS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500, "seiscientos": 600,
    "seiscientas": 600, "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}
ENGLISH_UNITS = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
]
ENGLISH_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"}


def spanish_number_value(text: str) -> int | None:
    """Value of a Spanish number phrase ('treinta y uno' -> 31, 'dos mil' -> 2000), None if not a number."""
    text = re.sub(r"\(.*?\)", " ", text.lower())
    tokens = [token for token in re.findall(r"[a-záéíóúñü]+", text) if token != "y"]
    if not tokens:
        return None
    total, current = 0, 0
    for token in tokens:
        if token in SPANISH_UNITS:
            current += SPANISH_UNITS[token]
        elif token in SPANISH_TENS:
            current += SPANISH_TENS[token]
        elif token in SPANISH_HUNDREDS:
            current += SPANISH_HUNDREDS[token]
        elif token == "mil":
            total += (current or 1) * 1000
            current = 0
        elif token in ("millón", "millones"):
            total += (current or 1) * 1_000_000
            current = 0
        else:
            return None
    return total + current


def english_number(value: int) -> str:
    """English number words: 31 -> 'thirty-one', 1200 -> 'one thousand two hundred'."""
    if value < 20:
        return ENGLISH_UNITS[value]
    if value < 100:
        tens, unit = divmod(value, 10)
        return ENGLISH_TENS[tens * 10] + (f"-{ENGLISH_UNITS[unit]}" if unit else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        return f"{ENGLISH_UNITS[hundreds]} hundred" + (f" {english_number(rest)}" if rest else "")
    for size, name in ((1_000_000_000, "billion"), (1_000_000, "million"), (1000, "thousand")):
        if value >= size:
            head, rest = divmod(value, size)
            return f"{english_number(head)} {name}" + (f" {english_number(rest)}" if rest else "")
    raise ValueError(value)


def digits_value(text: str) -> int | None:
    text = text.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", text):
        return int(re.sub(r"[.,]", "", text))
    if re.fullmatch(r"\d{1,9}", text):
        return int(text)
    return None


def parse_number_table(image: dict, report: Counter) -> list[Card]:
    """Rows of 'digits  spanish words'. The Spanish must spell the digits (checked), so OCR slips are dropped."""
    lines = merge_row_observations([item for item in image["observations"] if clean_text(item["text"])])
    digit_items = [item for item in image["observations"] if digits_value(clean_text(item["text"])) is not None]
    spanish_items = [
        item for item in image["observations"]
        if spanish_number_value(clean_text(item["text"])) is not None
    ]
    if len(digit_items) < 3 or len(spanish_items) < 3 or not lines:
        return []
    cards = []
    checked_columns: list[float] = []
    unchecked = []
    for item in spanish_items:
        text = clean_text(item["text"])
        if text.lower() in {"un", "una", "y"}:
            continue
        value = spanish_number_value(text)
        row_digits = [
            digit for digit in digit_items
            if abs(center_y(item) - center_y(digit)) <= 0.5 * max(item["height"], digit["height"]) + 0.01
            and digit["x"] < item["x"] + 0.02
        ]
        if not row_digits:
            unchecked.append((item, value))
            continue
        # A digit on the same row must agree with the Spanish words; a mismatch is an OCR slip.
        if all(digits_value(clean_text(digit["text"])) != value for digit in row_digits):
            report["extra.numbers_unmatched"] += 1
            continue
        checked_columns.append(item["x"])
        cards.append(number_card(text, value, report))
    # A word without a digit (a missed "0") is kept only when it sits in the same column as checked rows.
    for item, value in unchecked:
        if any(abs(item["x"] - column) <= 0.03 for column in checked_columns):
            cards.append(number_card(clean_text(item["text"]), value, report))
    return cards


def number_card(text: str, value: int, report: Counter) -> Card:
    report["extra.numbers"] += 1
    return Card(re.sub(r"\s*\(.*?\)", "", text).strip(), english_number(value), WORD)


# ---- interrogatives -----------------------------------------------------------------

INTERROGATIVES = {
    "qué", "quién", "quiénes", "cuál", "cuáles", "cuándo", "dónde", "cómo", "cuánto", "cuánta", "cuántos",
    "cuántas", "por qué", "adónde", "de dónde", "para qué", "con quién", "a quién", "de quién", "de qué",
    "a dónde", "en qué",
}
_ACCENT_LOOKUP = {strip_accents(word): word for word in INTERROGATIVES}


def canonical_interrogative(part: str) -> str | None:
    """'¿ cómo?' / '¿Que?' -> '¿cómo?' / '¿qué?'; None if it is not exactly an interrogative word."""
    if "¿" not in part:
        return None
    word = re.sub(r"[¿?\s]+", " ", part).strip().lower()
    canonical = _ACCENT_LOOKUP.get(strip_accents(word))
    return f"¿{canonical}?" if canonical else None


def interrogative_card(spanish: str, english: str) -> Card | None:
    spanish = re.sub(r"\s*\([^)]*\)", "", spanish)
    parts = [part for part in re.split(r"\?\s*,?\s*", spanish) if part.strip()]
    spanish_forms = [canonical_interrogative(part) for part in parts]
    english = clean_text(english).rstrip("?!,. ").strip()
    if not spanish_forms or None in spanish_forms or not english or len(english.split()) > 5:
        return None
    english = english[:1].lower() + english[1:] if not english.startswith("I ") else english
    return Card(", ".join(spanish_forms), f"{english}?", WORD)


HEADING = re.compile(
    r"^(?P<es>¿[^?]*\?(?:\s*\([^)]*\))?(?:,?\s*¿[^?]*\?(?:\s*\([^)]*\))?)*)\s+(?P<en>[A-Z][A-Za-z' ,]*\?)$"
)


def parse_interrogatives(image: dict, report: Counter) -> list[Card]:
    cards = []
    # Headings above the examples: '¿Cómo? How?'
    for item in image["observations"]:
        match = HEADING.match(clean_text(item["text"]))
        if match:
            card = interrogative_card(match.group("es"), match.group("en"))
            if card:
                cards.append(card)
                report["extra.interrogatives"] += 1
    # A list image: '¿cómo?' on the left, 'how?' on the right.
    observations = [item for item in image["observations"] if clean_text(item["text"])]
    clusters = clusters_by_x(observations)
    if len(clusters) == 2 and len(observations) >= 4:
        pairs, _ = match_rows(merge_row_observations(clusters[0]), merge_row_observations(clusters[1]))
        for left, right in pairs:
            card = interrogative_card(left["text"], right["text"])
            if card:
                cards.append(card)
                report["extra.interrogatives"] += 1
    return cards


# ---- Spanish-headed section lists -----------------------------------------------------

SECTION_HEADERS = {
    "verbos", "nombres", "adjetivos", "expresiones", "adverbios", "preposiciones", "pronombres", "sustantivos",
    "conjunciones", "palabras",
}


def parse_sections(image: dict, report: Counter) -> list[Card]:
    """Images such as 'Verbos / Nombres / Adjetivos / Expresiones' lists: each section has its own columns."""
    from vocab_parser import cleaned_vocabulary, pair_columns

    observations = image["observations"]
    headers = sorted(
        (item for item in observations if clean_text(item["text"]).lower() in SECTION_HEADERS),
        key=lambda item: -center_y(item),
    )
    if not headers:
        return []
    rest = [item for item in observations if item not in headers]
    boundaries = [center_y(item) for item in headers]
    cards = []
    for index, top in enumerate(boundaries):
        bottom = boundaries[index + 1] if index + 1 < len(boundaries) else -1.0
        section = [item for item in rest if bottom < center_y(item) < top]
        clusters = clusters_by_x(section)
        if len(clusters) not in (2, 4):
            report["extra.section_skipped_layout"] += 1
            continue
        pairs = []
        for start in range(0, len(clusters), 2):
            pairs.extend(pair_columns(clusters[start], clusters[start + 1]))
        for spanish, english in cleaned_vocabulary(pairs):
            cards.append(Card(spanish, english, WORD))
            report["extra.section_words"] += 1
    return cards


def parse_image(image: dict, report: Counter) -> list[Card]:
    if Path(image["path"]).name in IGNORED_IMAGES:
        return []
    return parse_number_table(image, report) + parse_interrogatives(image, report) + parse_sections(image, report)
