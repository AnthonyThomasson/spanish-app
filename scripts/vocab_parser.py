import json
import re
import unicodedata
from pathlib import Path

SPANISH_MARKERS = re.compile(
    r"[áéíóúñü¿¡]|\b(?:el|la|los|las|un|una|yo|tú|usted|ustedes|nosotros|vosotros|él|ella|ellos|ellas|"
    r"qué|quién|cómo|cuándo|dónde|para|con|sin|del|al|y|o|muy|más|menos)\b",
    re.IGNORECASE,
)
ENGLISH_MARKERS = re.compile(
    r"\b(?:the|to|a|an|and|or|i|you|he|she|it|we|they|your|my|his|her|their|our|"
    r"what|where|when|who|how|why|with|without|for|from|in|on|at|of)\b",
    re.IGNORECASE,
)
CONJUGATION_MARKERS = re.compile(r"\b(?:nosotros|vosotros|ustedes|uds\.?|ud\.?)\b", re.IGNORECASE)
HEADER_WORDS = {"adjective", "adverb", "noun", "verbs", "spanish", "english", "examples", "infinitive", "stem", "ending"}
OCR_CORRECTIONS = {
    "to revieu": "to review",
    "to throu": "to throw",
    "the daun": "the dawn",
    "frequenth": "frequently",
    "where!": "where?",
    "sundays!": "sundays?",
    "somerne": "someone",
    "faceloverlook": "face/overlook",
    "cloudt": "cloudy",
    "desparecerse": "desaparecerse",
    "ilevar": "llevar",
    "siath": "sixth",
    "imposible": "impossible",
    "ơ'clock": "o'clock",
    "tomorrou": "tomorrow",
    "litle": "little",
    "vieu": "view",
    "artice": "article",
    "sweatt": "sweaty",
}
IGNORED_IMAGES = {
    "p041_00.png", "p041_01.png", "p042_02.png", "p164_00.png", "p167_01.png",
    "p168_00.png", "p189_01.png", "p194_02.png", "p253_04.png", "p258_00.png",
    "p263_02.png", "p298_00.png", "p300_00.png", "p301_02.png", "p304_00.png",
    "p378_00.png", "p382_01.png", "p444_00.png", "p444_01.png", "p453_00.png",
    "p462_01.png", "p462_02.png", "p464_00.png", "p518_00.png", "p523_00.png",
    "p523_01.png", "p527_02.png", "p528_00.png", "p545_00.png", "p545_02.png",
    "p572_00.png", "p580_02.png", "p593_01.png", "p593_04.png", "p626_01.png",
    "p628_01.png", "p640_00.png", "p644_00.png", "p678_01.png", "p686_00.png",
    "p690_00.png", "p690_02.png", "p717_00.png",
}
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
}
INVALID_PAIRS = {("valer", "to male")}


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^¿\s+", "¿", text)
    text = re.sub(r"\s+([?,!.])", r"\1", text)
    for wrong, right in OCR_CORRECTIONS.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    return text


def language_score(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


def clusters_by_x(observations: list[dict]) -> list[list[dict]]:
    clusters: list[list[dict]] = []
    for observation in sorted(observations, key=lambda item: item["x"]):
        if not clusters or observation["x"] - clusters[-1][-1]["x"] > 0.075:
            clusters.append([observation])
        else:
            clusters[-1].append(observation)
    return clusters


def center_y(observation: dict) -> float:
    return observation["y"] + observation["height"] / 2


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


def is_vocabulary_pair(spanish: str, english: str) -> bool:
    if (spanish, english) in INVALID_PAIRS:
        return False
    spanish = re.sub(r"^\d+\.\s*", "", spanish)
    combined = f"{spanish} {english}"
    if re.search(r"Construction|NOTE:|EXAMPLE|Present Tense|Past Tense|[<>•_{}]", combined, re.IGNORECASE):
        return False
    if not re.search(r"[a-záéíóúñ]", english, re.IGNORECASE):
        return False
    if re.fullmatch(r"(?:\d+\.\s*)?[a-záéíóúñ]+(?:ar|er|ir)", english, re.IGNORECASE):
        return False
    if re.search(r"[.!?]$", spanish) or (english.endswith(".") and not english.lower().endswith("etc.")):
        return False
    if len(spanish.split()) >= 4 and spanish[0].isupper():
        return False
    if len(english.split()) >= 4 and english[0].isupper():
        return False
    if len(spanish.split()) >= 4 and len(english.split()) >= 4:
        return False
    if len(spanish.split()) >= 4 and spanish.endswith(","):
        return False
    return bool(spanish and english)


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


def normalized_key(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(character for character in value if not unicodedata.combining(character))).strip()


def build_vocabulary(ocr_path: Path, chapter_starts: dict[int, int], chapter_titles: list[str]) -> tuple[dict, dict]:
    images = json.loads(ocr_path.read_text())
    starts = sorted(chapter_starts.items())
    chapters = [
        {"number": number, "title": chapter_titles[number - 1], "words": []}
        for number in range(1, len(chapter_titles) + 1)
    ]
    stats = {"images": len(images), "acceptedImages": 0, "rejectedImages": 0, "rejectedPages": {}}
    seen = set()
    for image in sorted(images, key=lambda item: int(re.search(r"p(\d+)_", Path(item["path"]).name).group(1))):
        page = int(re.search(r"p(\d+)_", Path(image["path"]).name).group(1))
        chapter_number = max((number for number, start in starts if start <= page), default=0)
        if not chapter_number:
            continue
        pairs = parse_image(image)
        if not pairs:
            stats["rejectedImages"] += 1
            stats["rejectedPages"][str(page)] = stats["rejectedPages"].get(str(page), 0) + 1
            continue
        stats["acceptedImages"] += 1
        for spanish, english in pairs:
            key = (chapter_number, normalized_key(spanish), normalized_key(english))
            if key in seen:
                continue
            seen.add(key)
            chapters[chapter_number - 1]["words"].append(word_details(spanish, english, page))
    return {
        "source": "Complete Spanish Step-by-Step by Bárbara Bregstein. Regenerate locally from your own PDF.",
        "chapters": chapters,
    }, stats
