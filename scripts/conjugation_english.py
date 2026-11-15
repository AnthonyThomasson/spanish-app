"""English for conjugation cards, generated from the first sense of an infinitive's gloss.

The book's conjugation tables are Spanish-only, so the English side is built here, deterministically:
'to have lunch' + ella -> 'she has lunch'. The subjects are chosen so that every card in a verb's
set has its own English prompt (the app treats a parenthetical as optional when answering):

    yo I · vos you · él he · ella she · Ud. you (formal) · nosotros we
    ellos they (m.) · ellas they (f.) · Uds. you all
"""

import re

ENGLISH_SUBJECTS = {
    "yo": "I",
    "vos": "you",
    "él": "he",
    "ella": "she",
    "Ud.": "you (formal)",
    "nosotros": "we",
    "ellos": "they (m.)",
    "ellas": "they (f.)",
    "Uds.": "you all",
}
THIRD_PERSON_SINGULAR = {"él", "ella"}
MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}
# Words that cannot start a verb phrase: a gloss that begins with one is not an infinitive.
NOT_A_VERB = {"the", "a", "an", "to", "and", "or", "of", "in", "on", "at", "for", "with", "by", "from", "it", "is"}
IRREGULAR_THIRD_PERSON = {"have": "has", "do": "does", "go": "goes"}
REFLEXIVE_FORMS = {
    "yo": ("myself", "my"),
    "vos": ("yourself", "your"),
    "él": ("himself", "his"),
    "ella": ("herself", "her"),
    "Ud.": ("yourself", "your"),
    "nosotros": ("ourselves", "our"),
    "ellos": ("themselves", "their"),
    "ellas": ("themselves", "their"),
    "Uds.": ("yourselves", "your"),
}
SENSE_SEPARATORS = re.compile(r"[;,/](?![^()]*\))")
PHRASE = re.compile(r"[a-z]+(?:'[a-z]+)?(?: [a-z]+(?:'[a-z]+)?)*")


def first_sense(gloss: str) -> str | None:
    """'to have lunch, to eat lunch' -> 'have lunch'. None when the gloss is empty or not trustworthy.

    Parentheticals are dropped ('to enter (in)' -> 'enter'); the gloss must start with 'to' or a modal.
    """
    if gloss.count("(") != gloss.count(")"):
        return None
    sense = SENSE_SEPARATORS.split(gloss.strip().lower(), maxsplit=1)[0]
    sense = re.sub(r"\s*\([^)]*\)", "", sense)
    sense = re.sub(r"\s+", " ", sense).strip(" .")
    starts_with_to = re.match(r"to\s+", sense)
    if starts_with_to:
        sense = sense[starts_with_to.end():]
    elif sense.split(" ")[0] not in MODALS:
        return None
    if not PHRASE.fullmatch(sense) or sense.split(" ")[0] in NOT_A_VERB:
        return None
    return sense


def _third_person(verb: str) -> str:
    if verb in IRREGULAR_THIRD_PERSON:
        return IRREGULAR_THIRD_PERSON[verb]
    if re.search(r"(?:s|x|z|ch|sh)$", verb) or re.search(r"[^aeiou]o$", verb):
        return verb + "es"
    if re.search(r"[^aeiou]y$", verb):
        return verb[:-1] + "ies"
    return verb + "s"


def _be(pronoun: str) -> str:
    if pronoun == "yo":
        return "am"
    return "is" if pronoun in THIRD_PERSON_SINGULAR else "are"


def conjugate_english(gloss: str, pronoun: str, reflexive: bool) -> str | None:
    """The English card text for a pronoun and a gloss ('he has lunch'), or None when it cannot be trusted.

    `reflexive` is accepted for symmetry with the Spanish side: the verb phrase is the same either way
    ('to get up' -> 'I get up'), and 'oneself' / "one's" in a gloss follow the subject.
    """
    subject = ENGLISH_SUBJECTS.get(pronoun)
    sense = first_sense(gloss)
    if subject is None or sense is None:
        return None
    words = sense.split(" ")
    oneself, ones = REFLEXIVE_FORMS[pronoun]
    words = [oneself if word == "oneself" else ones if word == "one's" else word for word in words]
    verb = words[0]
    if verb == "be":
        words[0] = _be(pronoun)
    elif verb not in MODALS and pronoun in THIRD_PERSON_SINGULAR:
        words[0] = _third_person(verb)
    return f"{subject} {' '.join(words)}"
