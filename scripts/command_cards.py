"""Command cards from the 'Infinitive | tú Command | English' tables (kind 'sentence').

The book teaches the tú command. The deck is Argentine, so the Spanish side is the vos
command built from the infinitive in the first column (sentate, vení, decí, hacé...).
Ud./Uds. commands are not in these tables and are untouched elsewhere.
"""

import re
from collections import Counter
from pathlib import Path

from card_types import SENTENCE, Card
from ocr_layout import IGNORED_IMAGES, clean_text, clusters_by_x, match_rows, merge_row_observations
from spanish_verbs import vos_imperative

INFINITIVE = re.compile(r"^(?:[a-záéíóúñ]+(?:ar|er|ir|ír)(?:se)?|ir|irse)$")
HEADER = re.compile(r"^(?:infinitive|english|affirmative|negative|(?:tú|ud\.?|uds\.?|vosotros)\s+command)$", re.IGNORECASE)


def is_command_table(observations: list[dict]) -> bool:
    texts = [clean_text(item["text"]) for item in observations]
    return any(re.fullmatch(r"infinitive", text, re.IGNORECASE) for text in texts) and any(
        re.search(r"command", text, re.IGNORECASE) for text in texts
    ) and any(re.fullmatch(r"english", text, re.IGNORECASE) for text in texts)


def capitalised_sentence(text: str) -> str:
    text = text.strip().rstrip(".")
    return text[:1].upper() + text[1:] + "."


def parse_image(image: dict, report: Counter) -> list[Card]:
    if Path(image["path"]).name in IGNORED_IMAGES or not is_command_table(image["observations"]):
        return []
    observations = [item for item in image["observations"] if not HEADER.match(clean_text(item["text"]))]
    clusters = clusters_by_x(observations)
    if len(clusters) != 3:
        report["commands.skipped_layout"] += 1
        return []
    columns = [merge_row_observations(cluster) for cluster in clusters]
    infinitive_rows, english_rows = columns[0], columns[2]
    pairs, unmatched = match_rows(infinitive_rows, english_rows)
    report["commands.unmatched_rows"] += unmatched
    cards = []
    for infinitive_row, english_row in pairs:
        infinitive = infinitive_row["text"].lower().strip()
        english = clean_text(english_row["text"])
        if not INFINITIVE.match(infinitive) or not english or re.search(r"[áéíóúñ¿¡]", english):
            report["commands.rejected"] += 1
            continue
        vos = vos_imperative(infinitive)
        if not vos:
            report["commands.rejected"] += 1
            continue
        cards.append(Card(capitalised_sentence(vos), capitalised_sentence(english), SENTENCE))
        report["commands.cards"] += 1
    return cards
