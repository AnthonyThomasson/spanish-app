"""Shared card model for the extraction pipeline.

Each card type lives in its own module and exposes a parser

    parse_image(image: dict, report: Counter) -> list[Card]

that turns one OCR'd image into cards. `card_parsers.PARSERS` lists them in order.
To add a card type (for example conjugation tables), write a module with such a
parser and append it there; `vocab_parser.build_vocabulary` handles the rest.
"""

from dataclasses import dataclass

WORD = "word"
SENTENCE = "sentence"
CONJUGATION = "conjugation"
KINDS = (WORD, SENTENCE, CONJUGATION)


@dataclass(frozen=True)
class Card:
    spanish: str
    english: str
    kind: str = WORD
    # Set when the card's Spanish side was written for tú/vosotros and still has to be
    # converted (or dropped) once the verb lexicon exists.
    needs_second_person_pass: bool = False
