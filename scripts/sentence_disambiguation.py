"""Make the prompts of a chapter's sentence cards unambiguous.

The deck is Argentine, so a plain "you" in an English prompt means vos. A sentence addressed to Ud. or Uds.
says so up front, in words a voice can read: "Formal: Where are you from?", "Plural: Don't yell." The label is
added to every sentence whose Spanish is certainly formal or plural (an explicit Ud./Uds., or a command whose
English starts with a verb the book teaches), and the app treats it as optional when answering.

Once every card of a chapter exists, some sentence cards still share an English prompt but have different Spanish
answers ("Drink." for Bebé / Beba / Beban, "I wanted to go." for quise / quería). Asked English to Spanish, the
learner cannot know which one is wanted. A vos / Ud. / Uds. group is told apart with the same labels (the vos card
keeps its plain English); any other group gets a short parenthetical tag that the app treats as optional when
answering and does not speak:

    (m.) (f.)                      a clitic that differs only in gender (ayudarlos / ayudarlas)
    (preterit) (imperfect)         only when the differing verb forms are certainly one or the other
    (pronoun before) (pronoun attached)   me la va a dar / va a dármela
    (Sp. word)                     fallback: the distinguishing Spanish word(s)

src/spoken-text.ts strips exactly these tags for sentence cards; keep DISAMBIGUATION_TAG there in step (a test compares it with FIXED_TAGS) with this list.
Spanish-side collisions (one Spanish prompt, several English answers) are merged into one card whose English
lists the alternatives with " / ". Word and conjugation cards are never touched.
"""

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from spanish_verbs import peel_clitics, strip_accents

SENTENCE = "sentence"
VOS, UD, UDS = "vos", "Ud.", "Uds."
# How a formal or plural prompt starts. src/matching.ts treats it as optional; keep ADDRESSEE_LABEL there in step.
ADDRESSEE_LABELS = {UD: "Formal", UDS: "Plural"}
# The fixed tags (besides "Sp. <words>"); src/spoken-text.ts strips these, and a test keeps the two in step.
MASCULINE, FEMININE = "m.", "f."
PRETERIT, IMPERFECT_TENSE = "preterit", "imperfect"
BEFORE, ATTACHED = "pronoun before", "pronoun attached"
FIXED_TAGS = (MASCULINE, FEMININE, PRETERIT, IMPERFECT_TENSE, BEFORE, ATTACHED)
TOKEN = re.compile(r"[a-záéíóúüñ]+")
SUBJECTS = {"yo", "el", "ella", "ellos", "ellas", "nosotros", "ud", "uds", "vos"}
CLITICS = {"se", "te", "me", "nos", "lo", "la", "los", "las", "le", "les"}


def fold(text: str) -> str:
    """The comparison form of a prompt: lowercase, accent-free, no punctuation."""
    text = strip_accents(text.lower().replace("ñ", "\0"))
    return " ".join(re.sub(r"[^a-z0-9\0]+", " ", text).replace("\0", "ñ").split())


def spanish_key(text: str) -> str:
    """Identity of a Spanish prompt: casefolded, punctuation removed, accents kept ('Hablo' is not 'Habló')."""
    return " ".join(re.sub(r"[¿?¡!.,;:\"'“”‘’()\-–]+", " ", text.casefold()).split())


def is_prefix_of(shorter: str, longer: str) -> bool:
    return longer == shorter or longer.startswith(shorter + " ")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def insert_tag(english: str, tag: str) -> str:
    """'Drink.' -> 'Drink (m.).' The tag goes before the closing punctuation, in each ' / ' alternative."""

    def tagged(part: str) -> str:
        terminal = re.search(r"[.?!]+[\"”'’]*$", part)
        if not terminal:
            return f"{part} ({tag})"
        return f"{part[:terminal.start()]} ({tag}){terminal.group(0)}"

    return " / ".join(tagged(part) for part in english.split(" / "))


def has_addressee_label(english: str) -> bool:
    return any(english.startswith(f"{label}: ") for label in ADDRESSEE_LABELS.values())


def label_addressee(english: str, addressee: str) -> str:
    """'Drink.' -> 'Formal: Drink.' for Ud. and 'Plural: Drink.' for Uds. A vos prompt stays as it is."""
    label = ADDRESSEE_LABELS.get(addressee)
    if not label or has_addressee_label(english):
        return english
    return f"{label}: {english}"


# --- classifiers: each takes a card's Spanish and returns a tag, or None when it cannot say -------------

NOT_A_COMMAND_START = {
    "the", "a", "an", "i", "he", "she", "it", "we", "they", "you", "this", "that", "these", "those", "there",
    "my", "your", "his", "her", "our", "their", "what", "where", "when", "who", "why", "how", "which", "is",
    "are", "was", "were", "am", "will", "would", "has", "have", "had", "if",
}


def explicit_pronoun(words: list[str]) -> str | None:
    if "uds" in words or "ustedes" in words:
        return UDS
    if "ud" in words or "usted" in words:
        return UD
    return None


def is_vos_imperative(word: str, infinitives: set[str]) -> bool:
    """'escribime', 'dámela', 'ponete': a vos imperative is the infinitive without its r, pronouns attached."""
    return any(len(verb) > 1 and strip_accents(verb) + "r" in infinitives for verb, _ in peel_clitics(word))


def classify_command(
    spanish: str, english: str, infinitives: set[str] = frozenset(), max_words: int = 6
) -> str | None:
    """vos / Ud. / Uds. for a short imperative, from its pronoun or its verb ending. `infinitives` (the verbs
    the book teaches) lets an unaccented vos form with attached pronouns ('Dame', 'Escribime') be recognised."""
    words = tokens(spanish)
    english_words = tokens(english)
    if "¿" in spanish or not words or len(words) > max_words or len(english_words) > max_words:
        return None
    if english_words[:2] == ["don", "t"]:
        english_words = english_words[2:]
    if not english_words or english_words[0] in NOT_A_COMMAND_START:
        return None
    pronoun = explicit_pronoun(words)
    if pronoun:
        return pronoun
    negative = words[0] == "no"
    verbs = [word for word in (words[1:] if negative else words) if word not in CLITICS]
    if not verbs:
        return None
    verb = verbs[0]
    if negative:
        if verb.endswith("s"):
            return VOS
        if verb.endswith("n"):
            return UDS
        return UD if verb[-1] in "ea" else None
    if verb[-1] in "áéí" or is_vos_imperative(verb, infinitives):
        return VOS
    if verb.endswith("nse"):
        return UDS
    if verb.endswith("se") and len(verb) > 4:
        return UD
    if len(verb) >= 7 and verb.endswith(("ate", "ete", "ite")):
        return VOS
    if verb.endswith("n"):
        return UDS
    return UD if verb[-1] in "ea" else None


NOT_VOS = {"atrás", "jamás", "además", "quizás", "después", "inglés", "francés", "interés", "país", "ananás"}


def classify_addressee(spanish: str, english: str) -> str | None:
    """vos / Ud. / Uds. for a sentence that says "you": from the pronoun, or a clear second-person form."""
    if not {"you", "your", "yours"} & set(tokens(english)):
        return None
    words = tokens(spanish)
    pronoun = explicit_pronoun(words)
    if pronoun:
        return pronoun
    for word in words:
        if word == "vos" or re.search(r"(?:aste|iste)$", word) and len(word) > 5:
            return VOS
        if re.search(r"[áéí]s$", word) and len(word) > 3 and word not in NOT_VOS:
            return VOS
    return None


YOU_WORDS = {"you", "your", "yours", "yourself", "yourselves"}


def command_verb(english: str) -> str:
    """The English verb a command starts with: "Don't open the window." -> 'open'."""
    words = tokens(english)
    if words[:2] == ["don", "t"]:
        words = words[2:]
    return words[0] if words else ""


def formal_or_plural(spanish: str, english: str, english_verbs: set[str], infinitives: set[str]) -> str | None:
    """Ud. / Uds. when a sentence is certainly addressed to one, otherwise None (a vos sentence, or unsure).

    Certain means an explicit Ud. / Uds. in a "you" sentence or a command, or a command whose ending says Ud. /
    Uds. and that is plainly a command: "No ..." for "Don't ...", or English that starts with a verb the book
    teaches (so "Paula es doctora." is not read as one).
    """
    command = classify_command(spanish, english, infinitives, max_words=12)
    pronoun = explicit_pronoun(tokens(spanish))
    if pronoun and (command or YOU_WORDS & set(tokens(english))):
        return pronoun
    if command not in (UD, UDS):
        return None
    negative = tokens(spanish)[:1] == ["no"] and tokens(english)[:2] == ["don", "t"]
    verb = command_verb(english)
    return command if negative or (verb in english_verbs and verb != "let") else None


# Imperfect endings are only trusted on a word that differs between the cards, never on "María" or "día".
IMPERFECT = re.compile(r"(?:aba|abas|ábamos|aban|ía|ías|íamos|ían)$")
IMPERFECT_IRREGULAR = {"era", "eras", "éramos", "eran", "iba", "ibas", "íbamos", "iban"}
PRETERIT_IRREGULAR = set()
for _stem_forms in (
    "fui fuiste fue fuimos fueron", "quise quiso quisimos quisieron", "pude pudo pudimos pudieron",
    "puse puso pusimos pusieron", "tuve tuvo tuvimos tuvieron", "estuve estuvo estuvimos estuvieron",
    "hice hizo hicimos hicieron", "dije dijo dijimos dijeron", "vine vino vinimos vinieron",
    "supe supo supimos supieron", "traje trajo trajimos trajeron", "anduve anduvo anduvimos anduvieron",
):
    PRETERIT_IRREGULAR.update(_stem_forms.split())
PRETERIT_REGULAR = re.compile(r"(?:[aeiou]ron|(?:aste|iste)(?<=.{6})|[^aeiou]ó|[^aeiou]é)$")
NOT_PRETERIT = {"qué", "café", "porqué", "canapé", "bebé", "sofá"}


def tense_of(word: str) -> str | None:
    if word in IMPERFECT_IRREGULAR or IMPERFECT.search(word) and len(word) > 4:
        return IMPERFECT_TENSE
    if word in PRETERIT_IRREGULAR or (len(word) > 3 and word not in NOT_PRETERIT and PRETERIT_REGULAR.search(word)):
        return PRETERIT
    return None


CLITIC_END = re.compile(r"(?:^|[aeiouáéíóú]r|ndo)(lo|la|los|las)$")
ATTACHED_CLITIC = re.compile(
    r"\w+(?:[áéí]r|ándo|iéndo|yéndo)(?:me|te|se|nos|lo|la|le|los|las|les)+$"
    r"|\w+(?:ar|er|ir)(?:me|te|se|nos|lo|la|le|los|las|les)$"
)


# --- strategies: each maps a collision group to one tag per card, or None if it cannot tell them apart -----

def distinguishing(word_lists: list[list[str]]) -> list[list[str]]:
    """For each card, the words that no other card lines up with (so a word repeated elsewhere still counts)."""
    result = []
    for index, words in enumerate(word_lists):
        shared: set[int] | None = None
        for other_index, other in enumerate(word_lists):
            if other_index == index:
                continue
            matched = {
                position
                for block in SequenceMatcher(None, words, other, autojunk=False).get_matching_blocks()
                for position in range(block.a, block.a + block.size)
            }
            shared = matched if shared is None else shared & matched
        result.append([word for position, word in enumerate(words) if position not in (shared or set())])
    return result


def by_command(cards: list[dict], infinitives: set[str] = frozenset()) -> list[str] | None:
    return [classify_command(card["spanish"], card["english"], infinitives) for card in cards]


def by_addressee(cards: list[dict], infinitives: set[str] = frozenset()) -> list[str] | None:
    return [classify_addressee(card["spanish"], card["english"]) for card in cards]


def by_gender(cards: list[dict], infinitives: set[str] = frozenset()) -> list[str] | None:
    differing = distinguishing([tokens(card["spanish"]) for card in cards])
    if any(len(words) != 1 for words in differing):
        return None
    ends = [CLITIC_END.search(words[0]) for words in differing]
    if not all(ends):
        return None
    stems = {words[0][: match.start(1)] for words, match in zip(differing, ends)}
    if len(stems) != 1:
        return None
    return [MASCULINE if match.group(1).endswith(("o", "os")) else FEMININE for match in ends]


def by_tense(cards: list[dict], infinitives: set[str] = frozenset()) -> list[str] | None:
    differing = distinguishing([tokens(card["spanish"]) for card in cards])
    if any(len(words) != 1 for words in differing):
        return None
    return [tense_of(words[0]) for words in differing]


def by_clitic_position(cards: list[dict], infinitives: set[str] = frozenset()) -> list[str] | None:
    letters = {
        "".join(sorted("".join(w for w in fold(card["spanish"]).split() if w not in SUBJECTS)))
        for card in cards
    }
    if len(letters) != 1:  # the same words, only the pronouns moved
        return None
    attached = [any(ATTACHED_CLITIC.match(word) for word in tokens(card["spanish"])) for card in cards]
    return [ATTACHED if value else BEFORE for value in attached]


def spanish_hints(cards: list[dict]) -> list[list[str]]:
    """Candidate hints per card, from the most to the least specific; the first level that is unique wins."""
    word_lists = [tokens(card["spanish"]) for card in cards]
    differing = [" ".join(words) for words in distinguishing(word_lists)]
    openings = [" ".join(words[:3]) + "…" for words in word_lists]
    whole = [" ".join(words) for words in word_lists]
    return [differing, openings, whole]


ADDRESSEE_STRATEGIES = {"command", "addressee"}  # their tags become labels, not parentheticals
STRATEGIES = [
    ("command", by_command),
    ("addressee", by_addressee),
    ("gender", by_gender),
    ("tense", by_tense),
    ("clitic_position", by_clitic_position),
]


def usable(tags: list[str] | None) -> bool:
    return bool(tags) and all(tags) and len(set(tags)) == len(tags)


def tags_for(cards: list[dict], infinitives: set[str] = frozenset()) -> tuple[str, list[str]]:
    for name, strategy in STRATEGIES:
        tags = strategy(cards, infinitives)
        if usable(tags):
            return name, tags
    for hints in spanish_hints(cards):
        tags = [f"Sp. {hint}" if hint else "" for hint in hints]
        if usable(tags):
            return "hint", tags
    return "none", []


# --- the pass ------------------------------------------------------------------------------------------

def is_sentence(card: dict) -> bool:
    return card.get("kind") == SENTENCE


def merge_spanish_collisions(words: list[dict], report: Counter) -> list[dict]:
    """One Spanish prompt with several English answers becomes one card listing them with ' / '.
    An answer that is only the start of another (a truncated copy) is dropped in favour of the longer one."""
    first: dict[str, dict] = {}
    result = []
    for card in words:
        if not is_sentence(card):
            result.append(card)
            continue
        key = spanish_key(card["spanish"])
        kept = first.get(key)
        if kept is None:
            first[key] = kept = dict(card)
            result.append(kept)
            continue
        alternatives = kept["english"].split(" / ")
        new = card["english"]
        if any(is_prefix_of(fold(new), fold(part)) for part in alternatives):
            report["disambiguation.duplicates_dropped"] += 1  # same answer, or a truncated copy of one
            continue
        shorter = [part for part in alternatives if is_prefix_of(fold(part), fold(new))]
        if shorter:
            alternatives = [new if part in shorter else part for part in alternatives]
            kept["english"] = " / ".join(dict.fromkeys(alternatives))
            report["disambiguation.truncated_replaced"] += 1
        else:
            kept["english"] = f"{kept['english']} / {new}"
            report["disambiguation.merged_spanish"] += 1
    return result


def without_trailing_pronoun(spanish: str) -> str:
    return re.sub(r"\s+(?:Uds?\.?|ustedes?)(?=[.!?]*$)", "", spanish, flags=re.IGNORECASE)


def drop_pronoun_duplicates(words: list[dict], report: Counter) -> list[dict]:
    """'Caminen Uds.' beside 'Caminen.' with the same English is one card said twice."""
    by_prompt: dict[str, list[dict]] = defaultdict(list)
    for card in words:
        if is_sentence(card):
            by_prompt[fold(card["english"])].append(card)
    dropped = set()
    for cards in by_prompt.values():
        plain = {spanish_key(card["spanish"]) for card in cards}
        for card in cards:
            stripped = spanish_key(without_trailing_pronoun(card["spanish"]))
            if stripped != spanish_key(card["spanish"]) and stripped in plain:
                dropped.add(id(card))
    report["disambiguation.duplicates_dropped"] += len(dropped)
    return [card for card in words if id(card) not in dropped]


def collision_groups(words: list[dict]) -> list[list[dict]]:
    """Sentence cards that share an English prompt (or one alternative of a merged prompt) but have different
    Spanish answers. Cards linked through any shared prompt end up in the same group."""
    cards = [card for card in words if is_sentence(card)]
    parent = list(range(len(cards)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    owner: dict[str, int] = {}
    for index, card in enumerate(cards):
        for alternative in card["english"].split(" / "):
            key = fold(alternative)
            if key in owner:
                parent[find(index)] = find(owner[key])
            else:
                owner[key] = index
    grouped: dict[int, list[dict]] = defaultdict(list)
    for index, card in enumerate(cards):
        grouped[find(index)].append(card)
    return [group for group in grouped.values() if len({spanish_key(card["spanish"]) for card in group}) > 1]


def label_formal_and_plural(
    words: list[dict], report: Counter, english_verbs: set[str], infinitives: set[str]
) -> list[dict]:
    """Every sentence certainly addressed to Ud. or Uds. starts with its label; vos sentences stay plain."""
    result = []
    for card in words:
        if is_sentence(card) and not has_addressee_label(card["english"]):
            addressee = formal_or_plural(card["spanish"], card["english"], english_verbs, infinitives)
            if addressee:
                card = {**card, "english": label_addressee(card["english"], addressee)}
                report["disambiguation.addressee_labels"] += 1
        result.append(card)
    return result


def disambiguate_sentences(
    words: list[dict],
    report: Counter,
    english_verbs: set[str] = frozenset(),
    infinitives: set[str] = frozenset(),
) -> list[dict]:
    """One chapter's cards in, the same cards out with formal / plural prompts labelled and ambiguous sentence
    prompts tagged. `english_verbs` and `infinitives` are the verbs the book teaches, in each language."""
    words = drop_pronoun_duplicates(merge_spanish_collisions(words, report), report)
    words = label_formal_and_plural(words, report, english_verbs, infinitives)
    replacements: dict[int, str] = {}
    for cards in collision_groups(words):
        report["disambiguation.groups"] += 1
        strategy, tags = tags_for(cards, infinitives)
        report[f"disambiguation.strategy.{strategy}"] += 1
        for card, tag in zip(cards, tags):
            if strategy in ADDRESSEE_STRATEGIES:
                replacements[id(card)] = label_addressee(card["english"], tag)
            else:
                replacements[id(card)] = insert_tag(card["english"], tag)
    result = []
    for card in words:
        if replacements.get(id(card), card["english"]) != card["english"]:
            card = {**card, "english": replacements[id(card)]}
            report["disambiguation.cards_tagged"] += 1
        result.append(card)
    return result
