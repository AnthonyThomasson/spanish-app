"""Rule-based Spanish verb helpers for the Argentine (voseo) deck.

Nothing here reads the book. It holds the conjugation rules the extraction
needs: vos forms from an infinitive, the tú forms a sentence might contain (so
they can be recognised and converted), and imperatives.

The conjugation-table job can reuse `vos_present` and `vos_imperative` directly.
"""

import re
import unicodedata

# vos present: stem + ás / és / ís, no stem change. These are the exceptions.
IRREGULAR_VOS_PRESENT = {
    "ser": "sos",
    "ir": "vas",
    "ver": "ves",
    "dar": "das",
    "estar": "estás",
    "haber": "has",
}

# Tú present forms that are not "regular stem + as/es", beyond the stem-change table.
IRREGULAR_TU_PRESENT = {
    "ser": {"eres"},
    "ir": {"vas"},
    "ver": {"ves"},
    "dar": {"das"},
    "estar": {"estás"},
    "haber": {"has"},
    "oír": {"oyes"},
    "oler": {"hueles"},
    "errar": {"yerras"},
    "decir": {"dices"},
    "tener": {"tienes"},
    "venir": {"vienes"},
    "reír": {"ríes"},
    "sonreír": {"sonríes"},
    "freír": {"fríes"},
}

# Tú affirmative imperatives that are not the 3rd-person present.
IRREGULAR_TU_IMPERATIVE = {
    "dar": "da",
    "decir": "di",
    "estar": "está",
    "hacer": "haz",
    "ir": "ve",
    "oír": "oye",
    "reír": "ríe",
    "sonreír": "sonríe",
    "ver": "ve",
    "poner": "pon",
    "salir": "sal",
    "ser": "sé",
    "tener": "ten",
    "venir": "ven",
}

# Vos affirmative imperatives that are not "infinitive minus r, last vowel accented".
IRREGULAR_VOS_IMPERATIVE = {
    "ir": "andá",
    "ser": "sé",
    "ver": "ve",
    "reír": "reí",
    "sonreír": "sonreí",
    "oír": "oí",
}

STEM_CHANGE = {
    "e>ie": (
        "acertar advertir apretar ascender atender atravesar calentar cerrar comenzar confesar convertir "
        "defender descender despertar divertir empezar encender encerrar entender enterrar extender fregar "
        "gobernar helar herir hervir invertir manifestar mentir merendar negar nevar pensar perder preferir "
        "querer recomendar referir regar reventar sembrar sentar sentir sugerir temblar tender tener venir "
        "arrepentir quebrar"
    ).split(),
    "o>ue": (
        "acordar acostar almorzar apostar aprobar avergonzar colgar conmover contar costar demostrar devolver "
        "disolver doler dormir encontrar envolver forzar llover morder morir mostrar mover poder probar "
        "recordar recostar renovar resolver rogar soler sonar soñar torcer volar volcar volver"
    ).split(),
    "e>i": (
        "competir concebir conseguir corregir derretir despedir elegir gemir impedir medir pedir "
        "rendir reñir repetir seguir servir teñir vestir"
    ).split(),
    "u>ue": ["jugar"],
}
_STEM_KIND = {verb: kind for kind, verbs in STEM_CHANGE.items() for verb in verbs}

# Regular -ar/-er/-ir verbs with no stem change, spelling change or irregular
# present subjunctive. The only ones we trust when turning a vosotros form into
# the ustedes form.
SAFE_REGULAR = set(
    "hablar trabajar estudiar caminar escuchar mirar bailar cantar comprar tomar usar necesitar cocinar "
    "limpiar viajar visitar llamar ayudar esperar preparar terminar lavar nadar "
    "acabar pagar llegar buscar tocar entrar cenar desayunar pasear gustar olvidar enseñar mandar "
    "comer beber leer aprender comprender correr deber vender responder "
    "vivir escribir abrir decidir recibir subir compartir asistir".split()
)

ACCENTS = str.maketrans("áéíóúü", "aeiouu")


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFC", "".join(
        char for char in unicodedata.normalize("NFD", text) if not unicodedata.combining(char) or char == "̃"
    ))


def split_reflexive(infinitive: str) -> tuple[str, bool]:
    """'sentarse' -> ('sentar', True)."""
    infinitive = infinitive.strip().lower()
    if infinitive.endswith("se") and infinitive[:-2].endswith(("ar", "er", "ir", "ír")):
        return infinitive[:-2], True
    return infinitive, False


def verb_class(infinitive: str) -> str | None:
    """'ar', 'er' or 'ir' for a plain infinitive, else None."""
    if len(infinitive) < 2:
        return None
    ending = infinitive[-2:]
    if ending in ("ar", "er", "ir"):
        return ending
    if ending == "ír":
        return "ir"
    return None


def vos_present(infinitive: str) -> str | None:
    """Vos present: 'hablar' -> 'hablás', 'pensar' -> 'pensás', 'dormir' -> 'dormís', 'ser' -> 'sos'.

    A reflexive infinitive keeps its pronoun separate: 'sentarse' -> 'te sentás'.
    """
    base, reflexive = split_reflexive(infinitive)
    form = IRREGULAR_VOS_PRESENT.get(base)
    if form is None:
        kind = verb_class(base)
        if kind is None:
            return None
        stem = base[:-2]
        form = stem + {"ar": "ás", "er": "és", "ir": "ís"}[kind]
    return f"te {form}" if reflexive else form


def _replace_last(text: str, old: str, new: str) -> str:
    index = text.rfind(old)
    return text if index < 0 else text[:index] + new + text[index + len(old):]


def _stem_variants(stem: str, kind: str) -> set[str]:
    """Stem-changed stem: the last e/o/u of the stem changes (pens- -> piens-, cont- -> cuent-)."""
    old, new = {"e>ie": ("e", "ie"), "o>ue": ("o", "ue"), "e>i": ("e", "i"), "u>ue": ("u", "ue")}[kind]
    return {_replace_last(stem, old, new)}


def tu_present_forms(infinitive: str) -> set[str]:
    """Every tú present form this infinitive can produce: regular, stem-changed or irregular.

    Verbs we cannot be sure of (an accented -ír verb we do not know) give an empty set.
    """
    base, _ = split_reflexive(infinitive)
    if base in IRREGULAR_TU_PRESENT:
        return set(IRREGULAR_TU_PRESENT[base])
    kind = verb_class(base)
    if kind is None or base.endswith("ír"):
        return set()
    stem = base[:-2]
    if base.endswith("uir") and not base.endswith(("guir", "quir")):
        return {stem + "yes"}
    ending = "as" if kind == "ar" else "es"
    change = _STEM_KIND.get(base)
    if change:
        return {variant + ending for variant in _stem_variants(stem, change)}
    return {stem + ending}


def tu_imperative_form(infinitive: str) -> str | None:
    """Tú affirmative imperative (without clitics), for the verbs we can be sure about."""
    base, _ = split_reflexive(infinitive)
    if base in IRREGULAR_TU_IMPERATIVE:
        return IRREGULAR_TU_IMPERATIVE[base]
    kind = verb_class(base)
    if kind is None or base.endswith("ír"):
        return None
    stem = base[:-2]
    if base.endswith("uir") and not base.endswith(("guir", "quir")):
        return stem + "ye"
    change = _STEM_KIND.get(base)
    if change:
        stem = next(iter(_stem_variants(stem, change)))
    return stem + ("a" if kind == "ar" else "e")


def vos_imperative_base(infinitive: str) -> str | None:
    """Vos affirmative imperative of a plain infinitive: 'hablar' -> 'hablá', 'venir' -> 'vení'."""
    base, _ = split_reflexive(infinitive)
    if base in IRREGULAR_VOS_IMPERATIVE:
        return IRREGULAR_VOS_IMPERATIVE[base]
    kind = verb_class(base)
    if kind is None:
        return None
    return base[:-2] + {"ar": "á", "er": "é", "ir": "í"}[kind]


def attach_clitics(vos_base: str, clitics: list[str]) -> str:
    """Attach pronouns to a vos imperative. One clitic keeps the stress natural (decime);
    two need the written accent (decímelo)."""
    if not clitics:
        return vos_base
    if len(clitics) == 1:
        if vos_base.endswith(("eí", "aí", "oí")):
            return vos_base + clitics[0]  # reíte, oíme: the accent marks the hiatus
        return strip_accents(vos_base) + clitics[0]
    return vos_base + "".join(clitics)


def vos_imperative(infinitive: str, clitics: list[str] | None = None) -> str | None:
    """Vos imperative of an infinitive; reflexive verbs get 'te': 'sentarse' -> 'sentate', 'venir' -> 'vení'."""
    base_infinitive, reflexive = split_reflexive(infinitive)
    form = vos_imperative_base(base_infinitive)
    if form is None:
        return None
    pronouns = list(clitics or [])
    if reflexive and "te" not in pronouns:
        pronouns.insert(0, "te")
    return attach_clitics(form, pronouns)


CLITICS = ("me", "te", "se", "lo", "la", "le", "nos", "los", "las", "les")


def peel_clitics(token: str) -> list[tuple[str, list[str]]]:
    """Possible (verb, clitics) splits of an imperative with attached pronouns, most clitics last.

    'escribeme' -> [('escribeme', []), ('escribe', ['me'])]; 'dimelo' -> [..., ('di', ['me', 'lo'])].
    The caller keeps only the splits whose verb it recognises.
    """
    results = [(token, [])]

    def peel(rest: str, found: list[str]) -> None:
        if len(found) == 2:
            return
        for clitic in sorted(CLITICS, key=len, reverse=True):
            if rest.endswith(clitic) and len(rest) > len(clitic):
                verb = rest[: -len(clitic)]
                results.append((verb, [clitic] + found))
                peel(verb, [clitic] + found)

    peel(token, [])
    return results


# ---- vosotros -> ustedes (regular verbs only) ----------------------------------

def ustedes_from_vosotros_present(vosotros_form: str, infinitive: str) -> str | None:
    base, _ = split_reflexive(infinitive)
    if base not in SAFE_REGULAR:
        return None
    kind = verb_class(base)
    stem = base[:-2]
    expected = {"ar": stem + "áis", "er": stem + "éis", "ir": stem + "ís"}[kind]
    if strip_accents(vosotros_form.lower()) != strip_accents(expected):
        return None
    return stem + ("an" if kind == "ar" else "en")


def ustedes_from_vosotros_imperative(vosotros_form: str, infinitive: str) -> str | None:
    """'mirad' -> 'miren' (ustedes command, regular verbs only)."""
    base, _ = split_reflexive(infinitive)
    if base not in SAFE_REGULAR:
        return None
    kind = verb_class(base)
    stem = base[:-2]
    expected = stem + {"ar": "ad", "er": "ed", "ir": "id"}[kind]
    if strip_accents(vosotros_form.lower()) != strip_accents(expected):
        return None
    return stem + ("en" if kind == "ar" else "an")


def english_base_forms(gloss: str) -> set[str]:
    """First word of each sense of an English infinitive gloss: 'to take, to have' -> {'take', 'have'}."""
    forms = set()
    for sense in re.split(r"[;,/]", gloss.lower()):
        sense = re.sub(r"\(.*?\)", "", sense).strip()
        sense = re.sub(r"^to\s+", "", sense)
        match = re.match(r"[a-z']+", sense)
        if match:
            forms.add(match.group(0))
    return forms
