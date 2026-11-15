"""Turn tú / vosotros example sentences into the Argentine vos / ustedes forms, or drop them.

The deck is Argentine: vos, not tú, and ustedes, not vosotros. A sentence is converted
only when every second-person verb in it can be identified from the verb lexicon
(the infinitives the book teaches) and mapped by rule. When a sentence is clearly
addressed to tú or vosotros but cannot be converted with certainty, it is dropped.
"""

import re
from dataclasses import dataclass, field

from spanish_verbs import (
    SAFE_REGULAR,
    english_base_forms,
    peel_clitics,
    split_reflexive,
    strip_accents,
    tu_imperative_form,
    tu_present_forms,
    verb_class,
    vos_imperative,
    vos_present,
)

# Verbs whose second-person forms matter in almost every lesson. They are always in the lexicon,
# with the English they are glossed by.
CORE_VERBS = {
    "ser": "to be", "estar": "to be", "ir": "to go", "tener": "to have", "hacer": "to do, to make",
    "decir": "to say, to tell", "poner": "to put", "venir": "to come", "salir": "to leave, to go out",
    "ver": "to see", "dar": "to give", "saber": "to know", "poder": "to be able to, can",
    "querer": "to want", "haber": "to have", "traer": "to bring", "oír": "to hear",
}

WORD = r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+"
UNKNOWN_ATTACHED_IMPERATIVE = re.compile(r"^[a-z]{2,}[ae](?:me|te|lo|la|le|nos|los|las|les){1,2}$")
DETERMINERS_BEFORE_NOUN = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "mis", "tus", "sus", "mi", "tu", "su", "de", "del",
    "al", "en", "con", "por", "para", "sin", "muchas", "muchos", "otras", "otros", "estas", "estos", "esas", "esos",
    "algunas", "algunos", "varias", "varios", "las", "tantas", "tantos", "dos", "tres", "cuatro", "cinco",
}
UD_MARKERS = re.compile(r"\b(?:ud|uds|usted|ustedes)\b\.?", re.IGNORECASE)
VOSOTROS_MARKERS = re.compile(r"\b(?:vosotros|vosotras|vuestro|vuestra|vuestros|vuestras|os)\b", re.IGNORECASE)
# Endings that are the same for tú and vos (preterit, imperfect, future, conditional) and so need no change.
SHARED_TU_VOS_ENDINGS = re.compile(
    r"(?:aste|iste|abas|ías|arás|erás|irás|arías|erías|irías|ases|ieses|aras|ieras)$", re.IGNORECASE
)
# English: "you" as the subject of a clause (so the Spanish needs a second-person verb).
SUBJECT_YOU = re.compile(
    r"(?:^|[.?!,;:]\s*)(?:you|do you|are you|can you|will you|would you|did you|have you|should you|could you|"
    r"were you|was you|must you|may you)\b|"
    r"\b(?:are|do|did|can|could|will|would|have|has|had|should|must|may|were|was|am|shall|does|is)\s+you\b|"
    r"\b(?:that|if|when|because|where|what|how|why|who|whom|while|as|since|than|and|but|so|or|unless|until|"
    r"before|after|whether)\s+you\b",
    re.IGNORECASE,
)
ANY_YOU = re.compile(r"\byou(?:r|rs|rself)?\b", re.IGNORECASE)
NON_IMPERATIVE_STARTS = {
    "it's", "i'm", "he's", "she's", "we're", "they're", "there's", "that's", "what's", "here's", "i'll", "i've",
    "you're", "we've", "they've", "isn't", "aren't", "tonight", "today", "tomorrow", "yesterday", "now", "then",
    "later", "soon", "always", "never", "sometimes", "often", "usually", "his", "hers", "some", "many", "all",
    "everyone", "everybody", "nobody", "someone", "no", "not", "one", "two", "three", "each", "every", "both",
    "i", "you", "he", "she", "it", "we", "they", "the", "a", "an", "this", "that", "these", "those", "there",
    "my", "your", "his", "her", "our", "their", "its", "what", "who", "how", "when", "where", "why", "which",
}


@dataclass
class Lexicon:
    """Infinitives the book teaches, with the English they are glossed by."""
    glosses: dict[str, set[str]] = field(default_factory=dict)

    def add(self, infinitive: str, gloss: str) -> None:
        base, _ = split_reflexive(infinitive.strip().lower())
        if verb_class(base) is None or " " in base:
            return
        self.glosses.setdefault(base, set()).update(english_base_forms(gloss))

    @classmethod
    def from_word_cards(cls, cards) -> "Lexicon":
        lexicon = cls()
        for infinitive, gloss in CORE_VERBS.items():
            lexicon.add(infinitive, gloss)
        for card in cards:
            if card.kind == "word" and re.match(r"^to\b", card.english, re.IGNORECASE):
                spanish = re.sub(r"\s*\(.*?\)", "", card.spanish).strip()
                if re.fullmatch(r"[a-záéíóúñü]+", spanish):
                    lexicon.add(spanish, card.english)
        return lexicon

    def tu_present_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}
        for infinitive in self.glosses:
            for form in tu_present_forms(infinitive):
                index.setdefault(form, []).append(infinitive)
        return index

    def tu_imperative_index(self) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}
        for infinitive in self.glosses:
            form = tu_imperative_form(infinitive)
            if form:
                index.setdefault(strip_accents(form), []).append(infinitive)
        return index


@dataclass
class Outcome:
    status: str  # unchanged | converted | dropped
    spanish: str
    reason: str = ""


def match_case(original: str, replacement: str) -> str:
    return replacement[:1].upper() + replacement[1:] if original[:1].isupper() else replacement


def convert_vosotros(spanish: str, english: str, lexicon: Lexicon) -> Outcome | None:
    """Handle a sentence addressed to vosotros. None if the sentence is not about vosotros."""
    tokens = re.findall(WORD, spanish)
    first = tokens[0].lower() if tokens else ""
    imperative_at_start = ANY_YOU.search(english) is None and bool(
        first == "id"
        or (
            re.fullmatch(r"[a-záéíóú]+(?:ad|ed|id)", first)
            and first[:-2] + {"ad": "ar", "ed": "er", "id": "ir"}[first[-2:]] in lexicon.glosses
        )
    )
    attached_os = _is_attached_os_imperative(first, lexicon) or bool(
        re.fullmatch(r"[a-záéíóú]{2,}[aei]d(?:lo|la|los|las|le|les|me|nos)", first)
    )
    verb_forms = [token for token in tokens if re.fullmatch(r"[a-záéíóú]+(?:áis|éis)|sois|vais|dais|veis", token.lower())]
    if attached_os:
        return Outcome("dropped", spanish, "vosotros")
    if not (VOSOTROS_MARKERS.search(spanish) or verb_forms or imperative_at_start):
        return None
    if re.search(r"\bos\b", spanish, re.IGNORECASE):
        return Outcome("dropped", spanish, "vosotros")

    result = spanish

    def verb_replacement(match: re.Match) -> str:
        word = match.group(0)
        lower = word.lower()
        for suffix, new in (("áis", "an"), ("éis", "en")):
            if lower.endswith(suffix):
                stem = lower[: -len(suffix)]
                if any(stem + ending in SAFE_REGULAR for ending in ("ar", "er", "ir")):
                    return match_case(word, stem + new)
        raise ValueError(word)

    try:
        result = re.sub(rf"\b{WORD}(?:áis|éis)\b", verb_replacement, result, flags=re.IGNORECASE)
        result = re.sub(r"\bvosotros\b|\bvosotras\b", lambda m: match_case(m.group(0), "ustedes"), result, flags=re.IGNORECASE)
        # A possessive before its noun becomes su/sus; one after the noun ("los amigos vuestros") is not
        # certain to read right, so the sentence is dropped.
        for match in re.finditer(r"\bvuestr(?:o|a|os|as)\b", result, re.IGNORECASE):
            before = re.findall(WORD, result[:match.start()])
            if before and before[-1].lower() not in {"de", "con", "en", "a", "para", "por", "y", "o", "sin", "sobre", "es", "son"}:
                return Outcome("dropped", spanish, "vosotros")
        result = re.sub(r"\bvuestr(?:o|a)\b", lambda m: match_case(m.group(0), "su"), result, flags=re.IGNORECASE)
        result = re.sub(r"\bvuestr(?:os|as)\b", lambda m: match_case(m.group(0), "sus"), result, flags=re.IGNORECASE)
        if imperative_at_start:
            infinitive_form = _vosotros_imperative(first, english)
            if infinitive_form is None:
                return Outcome("dropped", spanish, "vosotros")
            result = re.sub(rf"^{re.escape(tokens[0])}", match_case(tokens[0], infinitive_form), result)
    except ValueError:
        return Outcome("dropped", spanish, "vosotros")
    # Any remaining vosotros-looking verb (-ís, sois, vais...) was not understood.
    if re.search(rf"\b(?:{WORD}(?:áis|éis|ís)|sois|vais|dais|veis|seáis|vayáis|estéis)\b", result, re.IGNORECASE):
        return Outcome("dropped", spanish, "vosotros")
    return Outcome("converted", result, "vosotros")


def _is_attached_os_imperative(word: str, lexicon: Lexicon) -> bool:
    """'divertíos' / 'levantaos': a vosotros command with the pronoun attached (divertid + os)."""
    if not word.endswith(("íos", "aos", "eos")) or len(word) < 5:
        return False
    stem = strip_accents(word[:-2])  # 'divertí' -> 'diverti'
    infinitive = stem[:-1] + {"a": "ar", "e": "er", "i": "ir"}[stem[-1]]
    return infinitive in lexicon.glosses


def _vosotros_imperative(token: str, english: str) -> str | None:
    """'mirad' -> 'miren' when the verb is a trusted regular one and the English is an imperative."""
    first_english = (re.findall(r"[a-z']+", english.lower()) or [""])[0]
    for ending, new in (("ad", "en"), ("ed", "an"), ("id", "an")):
        if token.endswith(ending):
            stem = token[: -len(ending)]
            infinitive = stem + {"ad": "ar", "ed": "er", "id": "ir"}[ending]
            if infinitive in SAFE_REGULAR and first_english in english_base_forms("to " + first_english):
                return stem + new
    return None


def convert_tu_imperative(spanish: str, english: str, lexicon: Lexicon, index: dict[str, list[str]]) -> Outcome | None:
    """A sentence starting with a tú command ('Ven acá.', 'Escríbeme la carta.') -> vos command."""
    match = re.match(rf"^([¡¿]?)({WORD})", spanish)
    if not match:
        return None
    token = match.group(2)
    english_tokens = re.findall(r"[a-z']+", english.lower())
    if english_tokens and english_tokens[0] == "please" and len(english_tokens) > 1:
        english_tokens = english_tokens[1:]
    english_first = english_tokens[0] if english_tokens else ""
    candidates = []
    for verb, clitics in peel_clitics(strip_accents(token.lower())):
        for infinitive in index.get(verb, []):
            # Without attached pronouns the written accent must match too (está/esta, sé/se).
            if not clitics and (tu_imperative_form(infinitive) or "") != token.lower():
                continue
            candidates.append((infinitive, clitics))
    if not candidates:
        # An imperative with attached pronouns whose verb we do not know ("Lávate", "Háblame") could be
        # tú or Ud.; we cannot tell, so it is dropped instead of kept in a form the deck should not teach.
        stripped = strip_accents(token.lower())
        if (
            token.lower() != stripped and UNKNOWN_ATTACHED_IMPERATIVE.match(stripped)
            and not stripped.endswith(("ese", "ense")) and "mos" not in stripped and english_first not in NON_IMPERATIVE_STARTS and english_first
        ):
            return Outcome("dropped", spanish, "unverified_imperative")
        return None
    imperative_start = english_first not in NON_IMPERATIVE_STARTS and english_first != ""
    unambiguous = token.lower() in {"di", "haz", "pon", "sal", "sé", "ten", "ven"} and imperative_start
    confirmed = [
        (infinitive, clitics) for infinitive, clitics in candidates
        if english_first in lexicon.glosses.get(infinitive, set()) or (unambiguous and not clitics)
    ]
    if not confirmed:
        if english_first in NON_IMPERATIVE_STARTS or not english_first:
            return None  # an ordinary statement ('Come mucho.' / 'He eats a lot.')
        return Outcome("dropped", spanish, "unverified_imperative")
    forms = {vos_imperative(infinitive, clitics) for infinitive, clitics in confirmed}
    forms.discard(None)
    if len(forms) != 1:
        return Outcome("dropped", spanish, "ambiguous_imperative")
    vos = next(iter(forms))
    converted = match.group(1) + match_case(token, vos) + spanish[match.end():]
    return Outcome("converted", converted, "imperative")



def convert_tu_present(spanish: str, english: str, lexicon: Lexicon, present_index: dict[str, list[str]]) -> Outcome:
    """Tú -> vos for sentences whose English has 'you' as a subject."""
    changed = False
    recognised = False

    tokens = list(re.finditer(WORD, spanish))
    pieces: list[str] = []
    cursor = 0
    previous_word = ""
    for match in tokens:
        word = match.group(0)
        lower = word.lower()
        replacement = word
        if lower == "tú":
            replacement = match_case(word, "vos")
            recognised = True
        elif lower == "contigo":
            replacement = match_case(word, "con vos")
            recognised = True
        elif lower == "ti" and previous_word in {"a", "para", "de", "por", "sin", "en", "como", "según", "hacia", "hasta"}:
            replacement = "vos"
            recognised = True
        elif lower in present_index and previous_word not in DETERMINERS_BEFORE_NOUN:
            options = {vos_present(infinitive) for infinitive in present_index[lower]}
            options.discard(None)
            if len(options) == 1:
                vos = next(iter(options))
                replacement = match_case(word, vos)
                recognised = True
            else:
                return Outcome("dropped", spanish, "ambiguous_verb")
        elif lower.endswith("ías") and (lower[:-3] + "iar") in lexicon.glosses:
            return Outcome("dropped", spanish, "ambiguous_verb")  # envías: present tú of enviar, not imperfect
        elif SHARED_TU_VOS_ENDINGS.search(lower) or lower in {"tu", "tus", "te"}:
            recognised = recognised or lower not in {"tu", "tus", "te"}
        pieces.append(spanish[cursor:match.start()])
        pieces.append(replacement)
        cursor = match.end()
        changed = changed or replacement != word
        previous_word = lower
    pieces.append(spanish[cursor:])
    converted = "".join(pieces)

    # Present subjunctive after "que" is the same for tú and vos.
    if not recognised and re.search(r"\bque\s+(?:\w+\s+)?\w+(?:as|es)\b", spanish, re.IGNORECASE):
        recognised = True
    if changed:
        return Outcome("converted", converted, "present")
    if recognised:
        return Outcome("unchanged", spanish, "tu_equals_vos")
    return Outcome("dropped", spanish, "unverified_second_person")


def convert_sentence(spanish: str, english: str, lexicon: Lexicon, indexes: dict | None = None) -> Outcome:
    """Decide what to do with one example sentence: keep, convert to voseo/ustedes, or drop."""
    indexes = indexes or {"present": lexicon.tu_present_index(), "imperative": lexicon.tu_imperative_index()}
    vosotros = convert_vosotros(spanish, english, lexicon)
    if vosotros is not None:
        return vosotros
    if UD_MARKERS.search(spanish) and not re.search(r"\btú\b|\bcontigo\b", spanish, re.IGNORECASE):
        return Outcome("unchanged", spanish, "formal")
    imperative = convert_tu_imperative(spanish, english, lexicon, indexes["imperative"])
    if imperative is not None:
        return imperative
    if SUBJECT_YOU.search(english) and not re.search(r"\byou all\b|\bthey\b", english, re.IGNORECASE):
        return convert_tu_present(spanish, english, lexicon, indexes["present"])
    # English has no subject "you": a tú form is still possible when the Spanish has the pronoun "tú".
    if re.search(r"\btú\b", spanish, re.IGNORECASE) or re.search(r"\bcontigo\b", spanish, re.IGNORECASE):
        return convert_tu_present(spanish, english, lexicon, indexes["present"])
    return Outcome("unchanged", spanish, "no_second_person")
