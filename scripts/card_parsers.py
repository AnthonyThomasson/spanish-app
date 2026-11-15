"""Registry of per-image card parsers, run in this order for every image."""

import command_cards
import extra_vocab
import sentence_cards

# Word cards (the original two-column tables) are produced by vocab_parser.parse_image,
# which build_vocabulary runs first. Add new card types here.
PARSERS = [
    sentence_cards.parse_image,
    command_cards.parse_image,
    extra_vocab.parse_image,
]
