"""Example-sentence cards (kind 'sentence') from two-column sentence images.

The book prints its examples as an image with the Spanish sentence on the left and
the English translation on the right, wrapped over several lines. We split the two
columns, join wrapped lines into sentences, pair them by row position and keep only
pairs that pass the quality filters below.
"""

import re
from collections import Counter
from pathlib import Path

from card_types import SENTENCE, Card
from ocr_layout import (
    IGNORED_IMAGES,
    PRONOUN_I_FIXES,
    clean_text,
    clusters_by_x,
    detect_language,
    mixed_language,
    group_wrapped_lines,
    is_conjugation_table,
    is_vocabulary_pair,
    match_rows,
    merge_row_observations,
    split_sentences,
)

NOISE = re.compile(r"[<>•_{}|\[\]=~]|\.\.\.\.|\d{5,}")
ODD_CHARACTER = re.compile(r"[^\w\s.,;:?!¿¡'’\"“”()/%$+\-–]")
BULLETS = {"•", "-", "–", "·", "*"}
OPENING = re.compile(r"^[¿¡A-ZÁÉÍÓÚÑ\"“(0-9]")
ENGLISH_OPENING = re.compile(r"^[A-Z\"“(0-9]")


def is_header_label(text: str) -> bool:
    """ALL-CAPS labels printed beside examples ('REGULAR IN THE PRESENT', 'MODIFIED')."""
    text = text.strip()
    return len(re.findall(r"[A-Za-z]", text)) >= 2 and text.upper() == text and not re.search(r"[¿¡?!]", text)


def without_foreign_lines(lines: list[dict]) -> list[dict]:
    """Drop headings and notes in the other language ("Health" above Spanish examples): lines whose
    language clearly differs from the column's majority language."""
    languages = [detect_language(line["text"], count_accents=True) for line in lines]
    counts = Counter(language for language in languages if language)
    if not counts:
        return lines
    majority = counts.most_common(1)[0][0]
    return [line for line, language in zip(lines, languages) if language in (None, majority)]


def column_pairs(image: dict, report: Counter) -> list[tuple[str, str]]:
    """Raw (spanish, english) sentence pairs of a two-column image, before the quality filters."""
    if Path(image["path"]).name in IGNORED_IMAGES:
        return []
    observations = [
        item for item in image["observations"]
        if item["text"].strip() not in BULLETS and clean_text(item["text"]) and not is_header_label(item["text"])
    ]
    if len(observations) < 2 or is_conjugation_table(observations):
        return []
    clusters = clusters_by_x(observations)
    if len(clusters) != 2:
        report["sentences.skipped_layout"] += 1
        return []
    left_lines = group_wrapped_lines(without_foreign_lines(merge_row_observations(clusters[0])))
    right_lines = group_wrapped_lines(without_foreign_lines(merge_row_observations(clusters[1])))
    pairs, unmatched = match_rows(left_lines, right_lines)
    report["sentences.unmatched_rows"] += unmatched
    result = []
    for left, right in pairs:
        spanish, english = left["text"], right["text"]
        # Some rows print the English on the left (exercise answers); swap when clearly reversed.
        if detect_language(spanish) == "en" and detect_language(english) == "es":
            spanish, english = english, spanish
        result.extend(split_pair(spanish, english, report))
    return result


def split_pair(spanish: str, english: str, report: Counter) -> list[tuple[str, str]]:
    """A row can hold several short sentences ("Cantemos. Bailemos."). Pair them up one by one
    when both sides split into the same number of sentences."""
    spanish_parts, english_parts = split_sentences(spanish), split_sentences(english)
    if len(spanish_parts) == len(english_parts) and len(spanish_parts) > 1:
        report["sentences.split_rows"] += 1
        return list(zip(spanish_parts, english_parts))
    if len(spanish_parts) > 1 or len(english_parts) > 1:
        report["sentences.rejected.sentence_count_mismatch"] += 1
        return []
    return [(spanish, english)]


def fix_english(english: str, spanish: str) -> str:
    for pattern, replacement in PRONOUN_I_FIXES:
        english = pattern.sub(replacement, english)
    english = re.sub(r"\b(dont|doesnt|cant|isnt|arent|wont|didnt)\b", lambda match: {
        "dont": "don't", "doesnt": "doesn't", "cant": "can't", "isnt": "isn't", "arent": "aren't",
        "wont": "won't", "didnt": "didn't",
    }[match.group(0).lower()], english, flags=re.IGNORECASE)
    english = english.strip().rstrip(",;:")
    final = spanish[-1:] if spanish[-1:] in ".?!" else ""
    if final == "?" and not english.endswith("?"):
        english = re.sub(r"[.!]$", "", english) + "?"
    elif final and not re.search(r"[.?!][\"”')]*$", english):
        english += final
    return english


ACCENTLESS_EL = re.compile(
    r"^El (?=(?:está|es|tiene|va|quiere|puede|vive|trabaja|habla|come|sabe|dice|hace|viene|llega|estudia|lee|"
    r"escribe|toca|canta|ve|oye|duerme|piensa|sale|puso|fue|tuvo|estaba|era|iba|estará|sería|ha|no|se|me|te|"
    r"le|lo|la|nos)\b)"
)


def fix_spanish(spanish: str) -> str:
    spanish = ACCENTLESS_EL.sub("Él ", spanish.strip())
    spanish = spanish.rstrip(",;:") + ("." if spanish.endswith((",", ";", ":")) else "")
    if spanish.startswith("¿") and spanish.endswith("."):
        spanish = spanish[:-1] + "?"
    elif spanish.startswith("¿") and spanish.endswith("!"):
        spanish = spanish[:-1] + "?"
    if spanish.endswith("?") and "¿" not in spanish and OPENING.match(spanish):
        spanish = "¿" + spanish
    if spanish.endswith("!") and "¡" not in spanish and OPENING.match(spanish):
        spanish = "¡" + spanish
    spanish = re.sub(r"^([¿¡])\s*['‘’`]+\s*", r"\1", spanish)
    return re.sub(r"¿\s+", "¿", re.sub(r"¡\s+", "¡", spanish))


LABEL = re.compile(
    r"\b(?:Construction|NOTE|EXAMPLES?|Tense|Singular|Plural|Masculine|Feminine|Affirmative|Negative|"
    r"Infinitive|Conjugations?|Exercises?|Vocabulary|Chapter|Lesson|Rule|Summary)\b|\bpg\.?\s*\d"
)
GARBLED_ENGLISH = re.compile(r"['‘’`]\s*\?+$|\?['‘’`]$|\s['‘’`]$|[?!.]{2,}\s*[?!]$")
CUT_OFF_SPANISH = re.compile(
    r"\b(?:si|que|este|esta|ese|esa|el|la|los|las|un|una|unos|unas|de|del|al|y|o|a|en|con|por|para|se|mi|tu|su|"
    r"como|pero|cuando|donde|sin|sobre)$", re.IGNORECASE
)
CUT_OFF_ENGLISH = re.compile(
    r"\b(?:the|a|an|to|of|if|that|this|and|or|in|with|for|at|on|by|from|but|because|when|where|my|your|his|her|"
    r"our|their|is|are|was|were)$", re.IGNORECASE
)


def fix_doubled_punctuation(text: str) -> str:
    """'house..' -> 'house.', 'house.,' -> 'house.' (an ellipsis of three dots is left alone)."""
    text = re.sub(r"(?<!\.)\.\.(?!\.)", ".", text)
    text = re.sub(r"\.,(?=\s+[a-záéíóúñ])", ",", text)  # 'voz., la cantante' -> 'voz, la cantante'
    return re.sub(r"\.,", ".", text)


def has_terminal(text: str) -> bool:
    return bool(re.search(r"[.?!][\"”')]*$", text))


def looks_cut_off(spanish: str, english: str) -> bool:
    """A side with no closing punctuation that ends on a function word was cut off by the page edge."""
    return (not has_terminal(spanish) and bool(CUT_OFF_SPANISH.search(spanish))) or (
        not has_terminal(english) and bool(CUT_OFF_ENGLISH.search(english))
    )


def sentence_problem(spanish: str, english: str) -> str | None:
    """The reason a pair is not a clean example sentence, or None if it is."""
    if NOISE.search(spanish) or NOISE.search(english):
        return "noise"
    if LABEL.search(spanish) or LABEL.search(english):
        return "label"
    if GARBLED_ENGLISH.search(english) or re.search(r"[.,]{2}(?!\.)|\.,", spanish + english):
        return "garbled"
    if re.search(r"\(\s*[mf]\.?\s*\)|\((?:sing|pl)\.?\)", spanish + english, re.IGNORECASE):
        return "gloss"
    if is_vocabulary_pair(spanish, english):
        return "vocabulary_pair"
    if not OPENING.match(spanish) or not ENGLISH_OPENING.match(english):
        return "not_sentence_start"
    if spanish.isupper() or english.isupper():
        return "label"
    terminal = re.search(r"[.?!]$", spanish) or re.search(r"[.?!]$", english)
    if len(spanish.split()) < 2 or len(english.split()) < 2:
        # One-word commands ("Cantemos." / "Let's sing.") are fine when both sides are closed sentences.
        if not (re.search(r"[.?!]$", spanish) and re.search(r"[.?!]$", english)):
            return "too_short"
    if not terminal and (len(spanish.split()) < 4 or len(english.split()) < 4):
        return "no_punctuation"
    spanish_language, english_language = detect_language(spanish), detect_language(english, count_accents=False)
    # Reject mixed-up columns; one side may be unrecognised (a short sentence of rare words)
    # as long as the other side clearly is its language.
    if spanish_language == "en" or english_language == "es":
        return "language"
    if re.search(r"[áéíóúñ]", re.sub(r"\b[A-ZÁÉÍÓÚÑ]\w*", "", english)) or "¿" in english or "¡" in english:
        return "language"
    if mixed_language(spanish, english):
        return "language"
    if len(ODD_CHARACTER.findall(spanish + english)) > 1:
        return "noise"
    if spanish.count("(") != spanish.count(")") or english.count("(") != english.count(")"):
        return "unbalanced"
    if english.startswith("(") or spanish.startswith("("):
        return "note"
    return None


def parse_image(image: dict, report: Counter) -> list[Card]:
    cards = []
    for spanish, english in column_pairs(image, report):
        spanish = fix_doubled_punctuation(clean_text(re.sub(r"^[}>{›»|~]+\s*", "", spanish), "es"))
        english = fix_doubled_punctuation(clean_text(re.sub(r"^[}>{›»|~]+\s*", "", english), "en"))
        # Truncation is judged before punctuation is copied across.
        # (a side that merely lacks its full stop is fine: "I see her" next to "La veo.")
        if not has_terminal(spanish) and not has_terminal(english) and looks_cut_off(spanish, english):
            report["sentences.rejected.cut_off"] += 1
            continue
        # A short Spanish half with no full stop beside a long English sentence was cut by the page edge
        # ("No vayamos" next to "Let's not go to the museum."); a closed short command is fine.
        if (
            not has_terminal(spanish) and has_terminal(english)
            and len(spanish.split()) <= 2 and len(english.split()) >= 2 * len(spanish.split()) + 2
        ):
            report["sentences.rejected.length_mismatch"] += 1
            continue
        spanish = fix_spanish(spanish)
        english = fix_english(english, spanish)
        # When only the English closed the sentence, close the Spanish the same way.
        if not has_terminal(spanish) and has_terminal(english):
            spanish = fix_spanish(spanish + english[-1])
        problem = sentence_problem(spanish, english)
        if problem:
            report[f"sentences.rejected.{problem}"] += 1
            continue
        report["sentences.candidates"] += 1
        cards.append(Card(spanish, english, SENTENCE, needs_second_person_pass=True))
    return cards
