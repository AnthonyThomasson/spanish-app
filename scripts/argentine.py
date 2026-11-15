"""A small, curated Spain/neutral -> Argentine word map for the Spanish side of cards.

Only clear, safe substitutions: everyday nouns with one well-known Argentine word, plus two
verbs (conducir -> manejar, coger -> agarrar/tomar). A word whose replacement has another
gender is replaced only when its article can be flipped with it and no adjective follows;
otherwise it is left alone rather than risk breaking agreement.
"""

import re

WORD = r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+"

# spanish word: (argentine word, original gender, new gender)
NOUNS = {
    "coche": ("auto", "m", "m"),
    "carro": ("auto", "m", "m"),
    "ordenador": ("computadora", "m", "f"),
    "computador": ("computadora", "m", "f"),
    "patata": ("papa", "f", "f"),
    "zumo": ("jugo", "m", "m"),
    "melocotón": ("durazno", "m", "m"),
    "fresa": ("frutilla", "f", "f"),
    "aguacate": ("palta", "m", "f"),
    "piscina": ("pileta", "f", "f"),
    "alberca": ("pileta", "f", "f"),
    "falda": ("pollera", "f", "f"),
    "camiseta": ("remera", "f", "f"),
    "playera": ("remera", "f", "f"),
    "autobús": ("colectivo", "m", "m"),
    "móvil": ("celular", "m", "m"),
    "acera": ("vereda", "f", "f"),
    "banqueta": ("vereda", "f", "f"),
    "chaqueta": ("campera", "f", "f"),
    "chamarra": ("campera", "f", "f"),
    "nevera": ("heladera", "f", "f"),
    "refrigerador": ("heladera", "m", "f"),
    "gasolina": ("nafta", "f", "f"),
    "gasolinera": ("estación de servicio", "f", "f"),
    "maleta": ("valija", "f", "f"),
    "apartamento": ("departamento", "m", "m"),
    "elevador": ("ascensor", "m", "m"),
    "cacahuete": ("maní", "m", "m"),
    "cacahuate": ("maní", "m", "m"),
    "frijol": ("poroto", "m", "m"),
    "guisante": ("arveja", "m", "f"),
    "chícharo": ("arveja", "m", "f"),
    "toronja": ("pomelo", "f", "m"),
    "plátano": ("banana", "m", "f"),
    "nata": ("crema", "f", "f"),
    "mesero": ("mozo", "m", "m"),
    "mesera": ("moza", "f", "f"),
    "camarero": ("mozo", "m", "m"),
    "camarera": ("moza", "f", "f"),
    "gafas": ("anteojos", "f", "m"),
    "calcetines": ("medias", "m", "f"),
}
# Nouns that exist only in the plural in the table above.
PLURAL_ONLY = {"gafas", "calcetines"}

MASCULINE_TO_FEMININE = {
    "el": "la", "un": "una", "este": "esta", "ese": "esa", "aquel": "aquella", "los": "las", "unos": "unas",
    "estos": "estas", "esos": "esas", "aquellos": "aquellas", "del": "de la", "al": "a la", "otro": "otra",
    "otros": "otras", "todo": "toda", "todos": "todas", "mucho": "mucha", "muchos": "muchas",
}
FEMININE_TO_MASCULINE = {
    "la": "el", "una": "un", "esta": "este", "esa": "ese", "aquella": "aquel", "las": "los", "unas": "unos",
    "estas": "estos", "esas": "esos", "aquellas": "aquellos", "otra": "otro", "otras": "otros", "toda": "todo",
    "todas": "todos", "mucha": "mucho", "muchas": "muchos",
}
# After a noun whose gender changed, only these may follow (anything else could be an adjective that would disagree).
SAFE_NEXT_WORDS = {
    "de", "en", "con", "para", "por", "sin", "a", "y", "o", "que", "cuesta", "cuestan", "funciona", "hay",
    "se", "me", "te", "nos", "no", "cerca", "lejos", "aquí", "allí", "ahora", "hoy", "ayer", "mañana",
    "también", "pero", "cuando", "donde", "del", "al",
}
# Words in front of the noun that block a gender change (their agreement would break).
BLOCKING_PREVIOUS_WORDS = {
    "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "ese", "esa",
    "cada", "cuánto", "cuánta", "cuántos", "cuántas", "qué", "algún", "alguna", "algunos", "algunas", "ningún",
    "ninguna", "varios", "varias", "tanto", "tanta", "tantos", "tantas", "poco", "poca", "pocos", "pocas",
}
# Words that may precede a bare or possessed noun without their own agreement.
NEUTRAL_PREVIOUS_WORDS = {"", "de", "en", "con", "para", "por", "sin", "a", "y", "o", "mi", "tu", "su", "mis", "tus", "sus"}
TRANSPORT = {"colectivo", "tren", "taxi", "metro", "subte", "avión", "barco", "ómnibus", "micro", "bus", "autobús"}

# Verb forms: the whole conjugation is mapped so the verb stays consistent within a sentence.
_CONDUCIR = {
    "conducir": "manejar", "conduzco": "manejo", "conduces": "manejas", "conducís": "manejás", "conduce": "maneja",
    "conducimos": "manejamos", "conducen": "manejan", "conduje": "manejé", "condujiste": "manejaste",
    "condujo": "manejó", "condujimos": "manejamos", "condujeron": "manejaron", "conducía": "manejaba",
    "conducías": "manejabas", "conducíamos": "manejábamos", "conducían": "manejaban", "conduciendo": "manejando",
    "conducido": "manejado", "conduciré": "manejaré", "conducirá": "manejará", "conduciría": "manejaría",
    "conduzca": "maneje", "conduzcas": "manejes", "conduzcamos": "manejemos", "conduzcan": "manejen",
    "conducí": "manejá",
}
_COGER = {
    "coger": "agarrar", "cojo": "agarro", "coges": "agarras", "cogés": "agarrás", "coge": "agarra",
    "cogemos": "agarramos", "cogen": "agarran", "cogí": "agarré", "cogiste": "agarraste", "cogió": "agarró",
    "cogimos": "agarramos", "cogieron": "agarraron", "cogía": "agarraba", "cogías": "agarrabas",
    "cogíamos": "agarrábamos", "cogían": "agarraban", "cogiendo": "agarrando", "cogido": "agarrado",
    "cogeré": "agarraré", "cogerá": "agarrará", "cogería": "agarraría", "coja": "agarre", "cojas": "agarres",
    "cojamos": "agarremos", "cojan": "agarren",
}
VERBS = {**_CONDUCIR, **_COGER}


def _match_case(original: str, replacement: str) -> str:
    return replacement[:1].upper() + replacement[1:] if original[:1].isupper() else replacement


def _plural(word: str) -> str:
    return word + ("es" if word[-1] in "lrnzd" or word.endswith("ús") else "s")


def _noun_lookup(word: str) -> tuple[str, str, str, bool] | None:
    """(argentine word, old gender, new gender, is_plural) for a mapped noun, singular or plural."""
    lower = word.lower()
    if lower in PLURAL_ONLY and lower in NOUNS:
        replacement, old, new = NOUNS[lower]
        return replacement, old, new, True
    if lower in NOUNS and lower not in PLURAL_ONLY:
        replacement, old, new = NOUNS[lower]
        return replacement, old, new, False
    for suffix in ("es", "s"):
        if lower.endswith(suffix) and lower[: -len(suffix)] in NOUNS and lower[: -len(suffix)] not in PLURAL_ONLY:
            singular = lower[: -len(suffix)]
            if _plural(singular) == lower:
                replacement, old, new = NOUNS[singular]
                return _plural(replacement), old, new, True
    return None


def _tokens(text: str) -> list[tuple[str, bool]]:
    """Split into (piece, is_word) so the text can be rebuilt exactly."""
    pieces = []
    cursor = 0
    for match in re.finditer(WORD, text):
        if match.start() > cursor:
            pieces.append((text[cursor:match.start()], False))
        pieces.append((match.group(0), True))
        cursor = match.end()
    if cursor < len(text):
        pieces.append((text[cursor:], False))
    return pieces


def argentinize(text: str) -> str:
    """Apply the Argentine word map to a Spanish string."""
    pieces = _tokens(text)
    words = [index for index, (_, is_word) in enumerate(pieces) if is_word]
    result = [piece for piece, _ in pieces]
    for position, index in enumerate(words):
        word = pieces[index][0]
        lower = word.lower()
        previous_index = words[position - 1] if position else None
        next_index = words[position + 1] if position + 1 < len(words) else None
        previous_word = pieces[previous_index][0].lower() if previous_index is not None and index - previous_index == 2 else ""
        next_word = pieces[next_index][0].lower() if next_index is not None and next_index - index == 2 else ""

        if lower in VERBS:
            replacement = VERBS[lower]
            if lower in _COGER and next_word in {"el", "un", "la", "una"}:
                after = words[position + 2] if position + 2 < len(words) else None
                if after is not None and pieces[after][0].lower() in TRANSPORT:
                    replacement = "tom" + replacement[len("agarr"):]
            result[index] = _match_case(word, replacement)
            continue

        found = _noun_lookup(word)
        if found is None:
            continue
        replacement, old_gender, new_gender, _ = found
        if old_gender == new_gender:
            result[index] = _match_case(word, replacement)
            continue
        # Gender changes: flip the article, but only when nothing else would have to agree.
        if previous_word in BLOCKING_PREVIOUS_WORDS or (next_word and next_word not in SAFE_NEXT_WORDS):
            continue
        flip = MASCULINE_TO_FEMININE if old_gender == "m" else FEMININE_TO_MASCULINE
        if previous_word in flip:
            article_index = words[position - 1]
            result[article_index] = _match_case(pieces[article_index][0], flip[previous_word])
            result[index] = _match_case(word, replacement)
        elif previous_word in NEUTRAL_PREVIOUS_WORDS:
            result[index] = _match_case(word, replacement)
    # Re-contract "de el" / "a el" left by flipping la -> el.
    return re.sub(r"\b(de|a) el\b", lambda match: "del" if match.group(1) == "de" else "al", "".join(result))
