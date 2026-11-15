import json
import re
from collections import Counter
from pathlib import Path

from card_types import WORD, Card

from ocr_layout import (  # noqa: F401  (re-exported for callers of the old module layout)
    CONJUGATION_MARKERS,
    IGNORED_IMAGES,
    ENGLISH_MARKERS,
    HEADER_WORDS,
    INVALID_PAIRS,
    OCR_CORRECTIONS,
    SPANISH_MARKERS,
    center_y,
    clean_text,
    clusters_by_x,
    is_vocabulary_pair,
    language_score,
    normalized_key,
)

PAIR_CORRECTIONS = {
    ("solo", "lane"): ("solo", "alone"),
    ("7 or", "to hear"): ("oír", "to hear"),
    ("ın rato", "a little while"): ("un rato", "a little while"),
    ("desaparecerse", "› disappea"): ("desaparecerse", "to disappear"),
    ("recuperarse", ") recuperat"): ("recuperarse", "to recuperate"),
    ("la lección veintitrés", "(the street eleven) the twenty-third lesson (the lesson twenty-three)"):
        ("la lección veintitrés", "the twenty-third lesson (the lesson twenty-three)"),
    ("hace", "ago (when it is used before a period"): ("hace", "ago (before a period of time)"),
    ("hace (dos días)", "of time in the past) (two days) ago"): ("hace (dos días)", "(two days) ago"),
    ("hace", "ago (when it is used before a period of time"): ("hace", "ago (before a period of time)"),
    ("desde", "since; from (a point of departure in place or time"):
        ("desde", "since; from (a point of departure in place or time)"),
    ("irse", "to go (compared with ir, irse expresses more"): ("irse", "to go"),
    ("llevarse (bien)", "to get along (well"): ("llevarse (bien)", "to get along (well)"),
    ("más allá de (mi ventana)", "outside (my window"): ("más allá de (mi ventana)", "outside (my window)"),
    ("triqui triqui", "trick or treat (from the sound of English trick or treat"):
        ("triqui triqui", "trick or treat"),
    ("cotidiano", "an emphasized i- or hi..) daily"): ("cotidiano", "daily"),
    ("bonita e inteligente", "pretty and intelligent (The word e is used instead of y before words that begin with"):
        ("bonita e inteligente", "pretty and intelligent"),
    ("e indecisa", "and indecisive (When expressing and in Spanish, e replaces y before a word that"):
        ("e indecisa", "and indecisive"),
    ("después de + infinitive", "after (doing something"): ("después de + infinitive", "after (doing something)"),
    ("bajo", "under (more figurative than debajo de"): ("bajo", "under (more figurative than debajo de)"),
    ("dejar", "to leave (something"): ("dejar", "to leave (something)"),
    ("llevarse (bien) (con)", "to get along (well with"): ("llevarse (bien) (con)", "to get along (well with)"),
    ("el arte español", "Spanish arl"): ("el arte español", "Spanish art"),
    ("propio", "oun"): ("propio", "own"),
    ("hace dos días", "in the past) two days ago"): ("hace dos días", "two days ago"),
    ("caber", "to fit (one thing inside"): ("caber", "to fit (one thing inside)"),
    ("maquillarse", "immediacy) to put makeup on"): ("maquillarse", "to put makeup on"),
    ("es impossible (que)", "it is impossible that"): ("es imposible (que)", "it is impossible (that)"),
    ("es preciso (que)", "it is extremely necessary (that"): ("es preciso (que)", "it is extremely necessary (that)"),
    ("echar de menos", "to miss (a person or place"): ("echar de menos", "to miss (a person or place)"),
    ("ser todo oídos", "to he all ears"): ("ser todo oídos", "to be all ears"),
    ("en seguida", "ight awar"): ("en seguida", "right away"),
    ("sobre todo", "ahora all"): ("sobre todo", "above all"),
}


def pair_columns(spanish: list[dict], english: list[dict]) -> list[tuple[str, str]]:
    if not spanish or not english:
        return []
    spanish = sorted(spanish, key=lambda item: -center_y(item))
    english = sorted(english, key=lambda item: -center_y(item))
    rows: list[dict] = [
        {"spanish": [observation], "english": [], "center": center_y(observation)}
        for observation in spanish
    ]
    for observation in english:
        row = min(rows, key=lambda item: abs(item["center"] - center_y(observation)))
        row["english"].append(observation)

    merged: list[dict] = []
    for row in rows:
        if not row["english"] and merged:
            distance_previous = abs(merged[-1]["center"] - row["center"])
            next_rows = [item for item in rows if item["english"] and item["center"] < row["center"]]
            distance_next = abs(next_rows[-1]["center"] - row["center"]) if next_rows else float("inf")
            if distance_previous <= distance_next:
                merged[-1]["spanish"].extend(row["spanish"])
                continue
        merged.append(row)

    pairs = []
    for row in merged:
        if not row["english"]:
            continue
        spanish_text = clean_text(" ".join(item["text"] for item in sorted(row["spanish"], key=lambda item: -center_y(item))))
        english_text = clean_text(" ".join(item["text"] for item in sorted(row["english"], key=lambda item: -center_y(item))))
        if spanish_text.lower() in HEADER_WORDS or english_text.lower() in HEADER_WORDS:
            continue
        pairs.append((spanish_text, english_text))
    return pairs


def clean_pair(pair: tuple[str, str]) -> tuple[str, str]:
    spanish, english = clean_text(pair[0]), clean_text(pair[1])
    spanish = re.sub(r"^\d+(?:\.|\s)\s*", "", spanish)
    spanish = re.sub(r"\s+(?:segundo second|tercero third|quinto fifth|octavo eighth|noveno ninth|décimo tenth)$", "", spanish)
    spanish = re.sub(r"\s+(?:Expresiones con Verbos|Adjetivos|Pronombres)$", "", spanish)
    english = english.rstrip(",")
    return PAIR_CORRECTIONS.get((spanish, english), (spanish, english))


def infinitive_pairs(observations: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for observation in observations:
        text = clean_text(observation["text"])
        match = re.match(r"^([a-záéíóúñ]+(?:\s*\([^)]*\))?)\s+((?:to|should|must|can|may)\b.+)$", text, re.IGNORECASE)
        if match and match.group(1).lower().endswith(("ar", "er", "ir")):
            pairs.append((match.group(1), match.group(2)))
    return pairs


def cleaned_vocabulary(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    cleaned_pairs = [clean_pair(pair) for pair in pairs]
    return [pair for pair in cleaned_pairs if is_vocabulary_pair(*pair)]


def parse_image(image: dict) -> list[tuple[str, str]]:
    if Path(image["path"]).name in IGNORED_IMAGES:
        return []
    observations = [item for item in image["observations"] if clean_text(item["text"]).lower() not in HEADER_WORDS]
    if not observations:
        return []
    headers = infinitive_pairs(observations)
    all_text = " ".join(item["text"] for item in observations)
    if len(CONJUGATION_MARKERS.findall(all_text)) >= 2:
        return cleaned_vocabulary(headers)
    clusters = clusters_by_x(observations)
    if len(clusters) not in (2, 4):
        return cleaned_vocabulary(headers)
    if any(len(cluster) < 1 for cluster in clusters):
        return cleaned_vocabulary(headers)

    pairs = []
    for index in range(0, len(clusters), 2):
        spanish, english = clusters[index], clusters[index + 1]
        spanish_text = " ".join(item["text"] for item in spanish)
        english_text = " ".join(item["text"] for item in english)
        if language_score(english_text, SPANISH_MARKERS) > language_score(english_text, ENGLISH_MARKERS):
            continue
        if language_score(spanish_text, ENGLISH_MARKERS) > language_score(spanish_text, SPANISH_MARKERS) + 1:
            continue
        pairs.extend(pair_columns(spanish, english))
    return cleaned_vocabulary(headers + pairs)


def word_details(spanish: str, english: str, source_page: int) -> dict:
    gender_match = re.search(r"\s+\((m|f)\.\)", spanish, re.IGNORECASE)
    if gender_match:
        gender = "masculine" if gender_match.group(1).lower() == "m" else "feminine"
        spanish = spanish[:gender_match.start()].strip()
    else:
        first = spanish.lower().split(maxsplit=1)[0] if spanish else ""
        gender = {"el": "masculine", "los": "masculine", "la": "feminine", "las": "feminine"}.get(first, "")
    part_of_speech = ""
    if re.match(r"^(?:el|la|los|las|un|una)\b", spanish, re.IGNORECASE):
        part_of_speech = "noun"
    elif re.match(r"^to\s+", english, re.IGNORECASE):
        part_of_speech = "verb"
    word = {"spanish": spanish, "english": english, "sourcePage": source_page}
    if part_of_speech:
        word["partOfSpeech"] = part_of_speech
    if gender:
        word["gender"] = gender
    return word


def page_of(image: dict) -> int:
    return int(re.search(r"p(\d+)_", Path(image["path"]).name).group(1))


def card_entry(card: Card, source_page: int) -> dict:
    """The vocab.json entry for a card. Words keep their original shape (no `kind`) so existing
    progress keys survive; other kinds carry an explicit `kind`."""
    if card.kind == WORD:
        return word_details(card.spanish, card.english, source_page)
    return {"spanish": card.spanish, "english": card.english, "sourcePage": source_page, "kind": card.kind}


def build_vocabulary(ocr_path: Path, chapter_starts: dict[int, int], chapter_titles: list[str]) -> tuple[dict, dict]:
    from argentine import argentinize
    from card_parsers import PARSERS
    from second_person import Lexicon, convert_sentence, convert_word_card

    images = json.loads(ocr_path.read_text())
    starts = sorted(chapter_starts.items())
    chapters = [
        {"number": number, "title": chapter_titles[number - 1], "words": []}
        for number in range(1, len(chapter_titles) + 1)
    ]
    stats = {"images": len(images), "acceptedImages": 0, "rejectedImages": 0, "rejectedPages": {}}
    report: Counter = Counter()

    # Pass 1: every card type, per image, in page order.
    entries: list[tuple[int, int, Card]] = []
    for image in sorted(images, key=page_of):
        page = page_of(image)
        chapter_number = max((number for number, start in starts if start <= page), default=0)
        if not chapter_number:
            continue
        cards = [Card(spanish, english) for spanish, english in parse_image(image)]
        for parser in PARSERS:
            cards.extend(parser(image, report))
        if not cards:
            stats["rejectedImages"] += 1
            stats["rejectedPages"][str(page)] = stats["rejectedPages"].get(str(page), 0) + 1
            continue
        stats["acceptedImages"] += 1
        entries.extend((chapter_number, page, card) for card in cards)

    # Pass 2: tú/vosotros sentences become vos/ustedes (or are dropped), then the Argentine word map.
    lexicon = Lexicon.from_word_cards(card for _, _, card in entries)
    indexes = {"present": lexicon.tu_present_index(), "imperative": lexicon.tu_imperative_index()}
    seen = set()
    for chapter_number, page, card in entries:
        spanish = card.spanish
        if card.needs_second_person_pass:
            outcome = convert_sentence(spanish, card.english, lexicon, indexes)
            report[f"second_person.{outcome.status}"] += 1
            if outcome.status == "dropped":
                report[f"second_person.dropped.{outcome.reason}"] += 1
                continue
            if outcome.status == "converted":
                report[f"second_person.converted.{outcome.reason}"] += 1
            spanish = outcome.spanish
        if card.kind == WORD:
            converted = convert_word_card(spanish)
            if converted != spanish:
                report["second_person.word_cards_converted"] += 1
                spanish = converted
        mapped = argentinize(spanish)
        if mapped != spanish:
            report[f"argentine.changed.{card.kind}"] += 1
        key = (chapter_number, card.kind, normalized_key(mapped), normalized_key(card.english))
        if key in seen:
            report[f"duplicates.{card.kind}"] += 1
            continue
        seen.add(key)
        chapters[chapter_number - 1]["words"].append(card_entry(Card(mapped, card.english, card.kind), page))

    stats["cards"] = dict(Counter(word.get("kind", WORD) for chapter in chapters for word in chapter["words"]))
    stats["cardsByChapter"] = {
        str(chapter["number"]): dict(Counter(word.get("kind", WORD) for word in chapter["words"])) for chapter in chapters
    }
    stats["report"] = dict(sorted(report.items()))
    return {
        "source": "Complete Spanish Step-by-Step by Bárbara Bregstein. Regenerate locally from your own PDF.",
        "chapters": chapters,
    }, stats
