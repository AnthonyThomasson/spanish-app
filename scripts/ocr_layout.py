import re
import unicodedata

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
# OCR corrections are side-specific: an English fix must never touch Spanish text ("imposible" is a
# real Spanish word) and the other way round. clean_text(text, "en"/"es") uses its own side only;
# clean_text(text) on mixed text (an infinitive and its gloss in one line) uses both except for
# words that are real in the other language (AMBIGUOUS_CORRECTIONS).
ENGLISH_OCR_CORRECTIONS = {
    "to revieu": "to review",
    "to throu": "to throw",
    "the daun": "the dawn",
    "frequenth": "frequently",
    "where!": "where?",
    "sundays!": "sundays?",
    "somerne": "someone",
    "faceloverlook": "face/overlook",
    "cloudt": "cloudy",
    "siath": "sixth",
    "imposible": "impossible",
    "ơ'clock": "o'clock",
    "tomorrou": "tomorrow",
    "litle": "little",
    "vieu": "view",
    "artice": "article",
    "sweatt": "sweaty",
    # Slips seen in example-sentence images (Vision reads "w" as "u"/"v" and drops letters).
    "sku": "sky",
    "thev": "they",
    "thev're": "they're",
    "wirh": "with",
    "wiht": "with",
    "tne": "the",
    "teh": "the",
    "bookk": "book",
    "tomorow": "tomorrow",
    "wednesdav": "Wednesday",
    "saturdav": "Saturday",
    "mondav": "Monday",
    "tuesdav": "Tuesday",
    "thursdav": "Thursday",
    "fridav": "Friday",
    "sundav": "Sunday",
    "saim": "swim",
    "sau": "saw",
    "hou": "how",
    "oun": "own",
    "nou": "now",
    "kneu": "knew",
    "tere": "there",
    "dallare": "dollars",
    "pensi": "pens",
    "urites": "writes",
    "dass": "class",
    "basehall": "baseball",
    "marketp": "marketplace",
    "didt": "didn't",
    "oneselt": "oneself",
}
SPANISH_OCR_CORRECTIONS = {
    "desparecerse": "desaparecerse",
    "ilevar": "llevar",
    "parce": "parece",
    "aver": "ayer",
    "chóteres": "chóferes",
    "apartmento": "apartamento",
    "ahore": "ahora",
    "a tempo": "a tiempo",
}
AMBIGUOUS_CORRECTIONS = {"imposible"}
# Kept for callers that import the old name: the corrections that are safe on any text.
OCR_CORRECTIONS = {
    wrong: right
    for table in (ENGLISH_OCR_CORRECTIONS, SPANISH_OCR_CORRECTIONS)
    for wrong, right in table.items()
    if wrong not in AMBIGUOUS_CORRECTIONS
}
# "cock" is a real word; it is a slip for "cook" only after a word that takes a verb.
ENGLISH_CONTEXT_CORRECTIONS = [
    (re.compile(r"(to|can|will|must|should|I|you|we|they|she|he|who|let's) cock(s|ed|ing)?\b", re.IGNORECASE), r"\1 cook\2"),
]
# Misreadings of the pronoun "I" at the start of a clause or before a verb ("1 am", "l have").
PRONOUN_I_FIXES = [
    (re.compile(r"(?:^|(?<=[.?!,;:]\s))[1l|]\s+(?=[a-z])"), "I "),
    (
        re.compile(
            r"\b[1l|]\s+(?=(?:am|have|had|will|would|was|can|could|do|did|don't|need|want|like|love|know|see|"
            r"think|go|live|eat|study|work|speak|read|write|play|prefer|feel|say|ask|bring|give|take|"
            r"get|put|make|come|leave|wash|buy|sell|watch|visit|call|help|learn|teach|drink|sleep|wake|"
            r"turn|open|close|hear|listen|look|walk|run|travel|wait|find|lose|keep|start|begin|finish|"
            r"remember|forget|believe|hope|wish|must|should|may|might|shall)\b)"
        ),
        "I ",
    ),
    (re.compile(r"\b[1l|]'(?=m\b|ve\b|ll\b|d\b)"), "I'"),
]
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
INVALID_PAIRS = {("valer", "to male")}


def clean_text(text: str, side: str | None = None) -> str:
    """Normalise whitespace and fix OCR slips. `side` is "en", "es" or None (mixed text)."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^¿\s+", "¿", text)
    text = re.sub(r"\s+([?,!.])", r"\1", text)
    if side == "en":
        corrections = ENGLISH_OCR_CORRECTIONS
    elif side == "es":
        corrections = SPANISH_OCR_CORRECTIONS
    else:
        corrections = OCR_CORRECTIONS
    for wrong, right in corrections.items():
        text = re.sub(rf"(?<![\w'’]){re.escape(wrong)}(?![\w'’])", right, text, flags=re.IGNORECASE)
    if side == "en":
        for pattern, replacement in ENGLISH_CONTEXT_CORRECTIONS:
            text = pattern.sub(replacement, text)
    if side == "es":
        text = text.replace("®", "").replace("  ", " ").strip()
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


def normalized_key(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(character for character in value if not unicodedata.combining(character))).strip()


# ---- language detection and line grouping (used by the sentence/command parsers) ----

SPANISH_WORDS = set(
    "el la los las un una unos unas de del al y o que en es son está están estoy estás estamos eres soy somos "
    "fue era ser estar tengo tiene tienes tenemos tienen hay lo le les nos mi mis tu tus su sus por para con "
    "sin pero muy más menos como cómo qué quién quiénes cuál cuáles dónde cuándo cuánto cuántos cuántas cuánta "
    "porque yo tú vos él ella ellos ellas nosotros nosotras usted ustedes ud uds este esta esto estos estas ese "
    "esa eso aquí allí ahora hoy mañana ayer también ya sí nunca siempre quiero quiere quieres puedo puede "
    "puedes voy va vas vamos van hace hago haces dice dicen vive vivo vivir habla hablo hablas "
    "casa libro día días noche nada nadie alguien algo todo todos todas muchos muchas mucho mucha otro otra "
    "bien mal bueno buena grande pequeño pequeña".split()
)
ENGLISH_WORDS = set(
    "the an and or of to in is are am was were be been i you he she it we they my your his her its our their "
    "this that these those there here what where when who how why with without for from on at not do does "
    "don't doesn't did can will would have has had very more less also but if because yes please "
    "i'm you're he's she's it's we're they're i've can't won't isn't aren't let's let some any "
    "want wants need needs like likes go goes going come comes today tomorrow yesterday always never "
    "book house day night everything everyone someone nothing nobody good bad big small little".split()
)
SPANISH_CHARACTERS = re.compile(r"[áéíóúñü¿¡]", re.IGNORECASE)


def detect_language(text: str, count_accents: bool = True) -> str | None:
    """'es', 'en' or None when the text does not clearly lean either way.

    Pass count_accents=False for text that should be English: accents there are names (María, José).
    """
    tokens = re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑÜ']+", text.lower())
    accented = (len(SPANISH_CHARACTERS.findall(text)) if count_accents else 0)
    spanish = sum(token in SPANISH_WORDS for token in tokens) + 2 * accented
    english = sum(token in ENGLISH_WORDS for token in tokens)
    if spanish > english:
        return "es"
    if english > spanish:
        return "en"
    return None


NON_TERMINAL_ABBREVIATIONS = re.compile(
    r"\b(?:Ud|Uds|Sr|Sra|Srta|Dr|Dra|Mr|Mrs|Ms|etc|a\.m|p\.m|St|vs)\.", re.IGNORECASE
)


def split_sentences(text: str) -> list[str]:
    """Split a run of sentences on terminal punctuation followed by a capital, keeping abbreviations whole."""
    protected = NON_TERMINAL_ABBREVIATIONS.sub(lambda match: match.group(0)[:-1] + "\u0001", text)
    parts = re.split(r"(?<=[.?!])\s+(?=[¿¡A-ZÁÉÍÓÚÑ0-9\"“(])", protected)
    return [part.replace("\u0001", ".").strip() for part in parts if part.strip()]


def is_conjugation_table(observations: list[dict]) -> bool:
    """A conjugation table has pronoun column headers and no real sentences."""
    markers = len(CONJUGATION_MARKERS.findall(" ".join(item["text"] for item in observations)))
    if markers < 2:
        return False
    sentences = sum(
        1 for item in observations
        if re.search(r"[.?!]$", item["text"].strip()) and len(item["text"].split()) >= 3
    )
    return sentences < 2


def merge_row_observations(observations: list[dict]) -> list[dict]:
    """Merge observations that sit on one visual line (same centre y) into single lines, top to bottom."""
    lines: list[dict] = []
    for item in sorted(observations, key=lambda entry: (-center_y(entry), entry["x"])):
        for line in lines:
            if abs(line["center"] - center_y(item)) <= 0.4 * max(line["height"], item["height"]):
                line["items"].append(item)
                break
        else:
            lines.append({"center": center_y(item), "height": item["height"], "items": [item]})
    result = []
    for line in lines:
        items = sorted(line["items"], key=lambda entry: entry["x"])
        result.append({
            "text": clean_text(" ".join(entry["text"] for entry in items)),
            "center": line["center"],
            "height": line["height"],
            "x": items[0]["x"],
        })
    return result


def group_wrapped_lines(lines: list[dict]) -> list[dict]:
    """Join wrapped lines into sentences. A line continues the previous one when the previous has no
    closing punctuation and this one starts in lowercase (or brackets are still open, or the previous
    line ends in a comma)."""
    groups: list[dict] = []
    for line in lines:
        text = line["text"]
        if not text:
            continue
        if groups:
            previous = groups[-1]
            open_brackets = previous["text"].count("(") > previous["text"].count(")")
            unfinished = not re.search(r"[.?!:\"”)]$", previous["text"]) or bool(
                NON_TERMINAL_ABBREVIATIONS.search(previous["text"][-6:])
            )
            comma = previous["text"].endswith(",")
            # Wrapped lines are indented a little further than the line that starts the sentence.
            indented = line["x"] >= previous["x"] + 0.015 and len(previous["text"].split()) >= 3
            if open_brackets or comma or (unfinished and (indented or re.match(r"[a-záéíóúñ]", text))):
                previous["text"] = f"{previous['text']} {text}"
                previous["height"] = max(previous["height"], line["height"])
                continue
        groups.append(dict(line))
    for group in groups:
        group["text"] = clean_text(group["text"])
    return groups


def match_rows(left: list[dict], right: list[dict]) -> tuple[list[tuple[dict, dict]], int]:
    """Pair left and right groups whose first lines sit on the same row. Returns (pairs, unmatched count)."""
    pairs = []
    used: set[int] = set()
    unmatched = 0
    for group in left:
        best_index, best_distance = None, None
        for index, other in enumerate(right):
            if index in used:
                continue
            distance = abs(group["center"] - other["center"])
            if distance <= 0.9 * max(group["height"], other["height"]) and (best_distance is None or distance < best_distance):
                best_index, best_distance = index, distance
        if best_index is None:
            unmatched += 1
            continue
        used.add(best_index)
        pairs.append((group, right[best_index]))
    unmatched += len(right) - len(used)
    return pairs, unmatched


# Words that are real in both languages ("he" = I have, "son" = they are / child, "has", "era"...).
SHARED_WORDS = {
    "let", "some", "any", "more", "less", "can", "will", "have", "had", "he", "has", "ha", "son", "era", "me",
    "no", "a", "an", "as", "so", "mi", "mal", "sin", "come", "van", "va", "vino", "hay", "fue", "vive", "si",
    "to", "o", "e", "an", "i", "it",
}
ENGLISH_ONLY_WORDS = (ENGLISH_WORDS - SPANISH_WORDS) - SHARED_WORDS
SPANISH_ONLY_WORDS = (SPANISH_WORDS - ENGLISH_WORDS) - SHARED_WORDS - {"vivir", "casa", "libro", "bien"}


def mixed_language(spanish: str, english: str) -> bool:
    """True when an English function word sits in the Spanish side or a Spanish one in the English side."""
    spanish_tokens = re.findall(r"[a-záéíóúñ']+", spanish.lower())
    english_tokens = re.findall(r"[a-z']+", re.sub(r"\b[A-ZÁÉÍÓÚÑ]\w*", "", english))
    return any(token in ENGLISH_ONLY_WORDS and token not in ("a",) for token in spanish_tokens) or any(
        token in SPANISH_ONLY_WORDS for token in english_tokens
    )
