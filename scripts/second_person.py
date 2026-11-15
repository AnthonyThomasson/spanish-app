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
UNKNOWN_ATTACHED_IMPERATIVE = re.compile(r"^[a-zñ]{2,}[ae](?:me|te|lo|la|le|nos|los|las|les){1,2}$")
# Accented words that end in what looks like a clitic but are not verbs.
NOT_IMPERATIVES = {"ojalá", "además", "quizá", "quizás", "acá", "allá", "allí", "aquí", "ahí", "jamás", "después"}
# Vosotros verb endings with no safe ustedes conversion: such a sentence is dropped.
VOSOTROS_DROP_ENDINGS = re.compile(r"(?:abais|íais|asteis|isteis|arais|ierais|aseis|ieseis)$", re.IGNORECASE)
VOSOTROS_IRREGULAR = {"sois", "vais", "dais", "veis", "seáis", "vayáis", "estéis", "deis", "sepáis", "hayáis"}
PREPOSITIONS_BEFORE_TI = r"(?:a|para|de|por|sin|en|como|según|hacia|hasta|entre)"
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
    r"\b(?:are|do|did|can|could|will|would|have|has|had|should|must|may|were|was|am|shall|does|is|\w+n't)\s+you\b|"
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


def attached_os_form(tokens: list[str], english: str, lexicon: Lexicon) -> bool:
    """A vosotros form with 'os' attached: escribiros, mandároslos, Bañaos, Ponéosla, Divertíos.

    Verb-gated so nouns such as 'tíos' or 'museos' are not caught; a command at the start of the
    sentence with an imperative English gloss is caught even if the verb is not in the lexicon.
    """
    known = {strip_accents(infinitive) for infinitive in lexicon.glosses}
    english_first = (re.findall(r"[a-z']+", english.lower()) or [""])[0]
    for position, token in enumerate(tokens):
        word = strip_accents(token.lower())
        # infinitive + os (+ lo/la/los/las): the clitic makes it certain
        if re.search(r"(?:ar|er|ir)os(?:lo|la|los|las)$", word):
            return True
        match = re.fullmatch(r"(.+(?:ar|er|ir))os", word)
        if match and match.group(1) in known:
            return True
        # command + os (+ clitic): bañaos, poneosla, divertios
        match = re.fullmatch(r"(.+?)([aei])os(?:lo|la|los|las|le|les|me|nos)?", word)
        if match and len(match.group(1)) >= 2:
            infinitive = match.group(1) + {"a": "ar", "e": "er", "i": "ir"}[match.group(2)]
            if infinitive in known:
                return True
            if position == 0 and english_first and english_first not in NON_IMPERATIVE_STARTS and not word.endswith(("caos", "tios", "rios")):
                return True
        match = re.fullmatch(r"(.+(?:ad|ed|id))(?:lo|la|los|las|le|les|me|nos)", word)
        if match and position == 0:
            return True
    return False


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
    if attached_os_form(tokens, english, lexicon):
        return Outcome("dropped", spanish, "vosotros")
    verb_forms = [
        token for token in tokens
        if re.fullmatch(r"[a-záéíóú]+(?:áis|éis)", token.lower()) or token.lower() in VOSOTROS_IRREGULAR
        or VOSOTROS_DROP_ENDINGS.search(token.lower())
    ]
    if not (VOSOTROS_MARKERS.search(spanish) or verb_forms or imperative_at_start):
        return None
    if re.search(r"\bos\b", spanish, re.IGNORECASE):
        return Outcome("dropped", spanish, "vosotros")
    if any(token.lower() in VOSOTROS_IRREGULAR or VOSOTROS_DROP_ENDINGS.search(token.lower()) for token in tokens):
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
        # A possessive before its noun becomes su/sus. After es/son at the end of the clause it becomes
        # "de ustedes" ("es vuestro" -> "es de ustedes"). Anywhere else the sentence is dropped.
        for match in list(re.finditer(r"\bvuestr(?:o|a|os|as)\b", result, re.IGNORECASE))[::-1]:
            before = re.findall(WORD, result[:match.start()])
            previous = before[-1].lower() if before else ""
            after = result[match.end():]
            if previous in {"es", "son"} and re.match(r"\s*[.?!,;]?\s*$", after):
                result = result[:match.start()] + "de ustedes" + after
            elif not before or previous in {"de", "con", "en", "a", "para", "por", "y", "o", "sin", "sobre"}:
                plural = match.group(0).lower().endswith("s")
                result = result[:match.start()] + match_case(match.group(0), "sus" if plural else "su") + after
            else:
                return Outcome("dropped", spanish, "vosotros")
        if imperative_at_start:
            infinitive_form = _vosotros_imperative(first, english)
            if infinitive_form is None:
                return Outcome("dropped", spanish, "vosotros")
            result = re.sub(rf"^{re.escape(tokens[0])}", match_case(tokens[0], infinitive_form), result)
    except ValueError:
        return Outcome("dropped", spanish, "vosotros")
    # Any remaining vosotros-looking verb (-ís, sois, vais, -asteis...) was not understood.
    if re.search(rf"\b(?:{WORD}(?:áis|éis|ís|abais|íais|asteis|isteis|arais|ierais|aseis|ieseis)|sois|vais|dais|veis|seáis|vayáis|estéis)\b", result, re.IGNORECASE):
        return Outcome("dropped", spanish, "vosotros")
    return Outcome("converted", result, "vosotros")


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
        accent_position = next((i for i, char in enumerate(token.lower()) if char in "áéíóú"), -1)
        # The written accent of verb + clitics sits before the clitics; a final accent (ojalá) is not a verb.
        accent_inside = 0 <= accent_position < len(token) - 2
        # One stray OCR letter after the clitics ("Enséñanosa") makes the command unverifiable.
        shapes = [stripped, stripped[:-1]]
        if (
            accent_inside and token.lower() not in NOT_IMPERATIVES
            and any(UNKNOWN_ATTACHED_IMPERATIVE.match(shape) for shape in shapes)
            and not stripped.endswith(("ese", "ense")) and "mos" not in stripped
            and english_first not in NON_IMPERATIVE_STARTS and english_first
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
        elif lower == "ti" and re.fullmatch(PREPOSITIONS_BEFORE_TI, previous_word):
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

    # "te llamas": a reflexive/clitic tú verb must have been converted (or already equal vos).
    vos_equal = {form for form, infinitives in present_index.items() if {vos_present(i) for i in infinitives} == {form}}
    for te_verb in re.finditer(rf"\bte\s+({WORD})", converted, re.IGNORECASE):
        word = te_verb.group(1).lower()
        if re.search(r"(?:as|es)$", word) and word not in vos_equal and word not in {"mas", "tres", "es", "días", "veces"}:
            return Outcome("dropped", spanish, "unverified_tu_verb")
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
    if UD_MARKERS.search(spanish) and not re.search(r"\btú\b|\bcontigo\b|\bti\b", spanish, re.IGNORECASE):
        return Outcome("unchanged", spanish, "formal")
    imperative = convert_tu_imperative(spanish, english, lexicon, indexes["imperative"])
    if imperative is not None:
        return imperative
    if SUBJECT_YOU.search(english) and not re.search(r"\byou all\b|\bthey\b", english, re.IGNORECASE):
        return convert_tu_present(spanish, english, lexicon, indexes["present"])
    # English has no subject "you", but the Spanish can still be addressed to tú: the pronoun, "ti"/"contigo",
    # or a reflexive/clitic verb ("te llamas").
    if (
        re.search(r"\btú\b|\bcontigo\b", spanish, re.IGNORECASE)
        or re.search(rf"\b{PREPOSITIONS_BEFORE_TI}\s+ti\b", spanish, re.IGNORECASE)
        or re.search(r"\bte\s+\w+(?:as|es)\b", spanish, re.IGNORECASE)
    ):
        return convert_tu_present(spanish, english, lexicon, indexes["present"])
    return Outcome("unchanged", spanish, "no_second_person")


def convert_word_card(spanish: str, english: str = "") -> tuple[str, str]:
    """The Argentine form of a vocabulary card: tú -> vos, vosotros -> ustedes. Returns (spanish, english).

    Only certain cases change: the pronouns on their own or after a preposition, 'ti' after a
    preposition, a prenominal vuestro -> su, a bare vuestro card -> 'de ustedes', and 'os' cards, which
    depend on the English gloss (reflexive -> se, "to you" -> les / se lo, se la...). 'contigo' stays.
    The English changes only to keep ustedes cards apart from the singular ones ("to you (all)").
    Anything else, including verb forms, is left as it is.
    """
    standalone = r"(^|\b(?:según|entre|como|excepto|salvo|menos|incluso|que)\s)"
    result = re.sub(rf"{standalone}tú(?=\s*$|\s+y\b)", lambda m: m.group(1) + "vos", spanish, flags=re.IGNORECASE)
    result = re.sub(rf"\b({PREPOSITIONS_BEFORE_TI}) ti\b", lambda m: f"{m.group(1)} vos", result, flags=re.IGNORECASE)
    result = re.sub(rf"{standalone}vosotr(?:os|as)(?=\s*$|\s+y\b)", lambda m: m.group(1) + "ustedes", result, flags=re.IGNORECASE)
    if re.fullmatch(r"vuestr(?:o|os|a|as)(?:/a)?", result, re.IGNORECASE):
        return "de ustedes", english
    prepositions = r"(?:de|con|en|a|para|por|sin|sobre)"
    result = re.sub(rf"(^|\b{prepositions}\s)vuestr(?:o|a)\b(?=\s+\w)", lambda m: m.group(1) + "su", result, flags=re.IGNORECASE)
    result = re.sub(rf"(^|\b{prepositions}\s)vuestr(?:os|as)\b(?=\s+\w)", lambda m: m.group(1) + "sus", result, flags=re.IGNORECASE)

    # 'os' cards, decided by what the English says os means.
    if re.fullmatch(r"os", result, re.IGNORECASE):
        if re.search(r"\bselves\b|\bthemselves\b|\byourselves\b", english):
            return "se", english
        if re.match(r"to you\b", english):
            return "les", english
        if re.fullmatch(r"you(?: \(.*\))?", english):
            return "los, las", english
        return spanish, english
    if re.fullmatch(r"os (?:lo|la|los|las)(?:, os (?:lo|la|los|las))*", result, re.IGNORECASE):
        if re.search(r"\bto you\b", english):
            result = re.sub(r"\bos\b", "se", result)
            english = re.sub(r"\bto you\b(?! \(all\))", "to you (all)", english)
            return result, english
        return spanish, english
    return result, english
