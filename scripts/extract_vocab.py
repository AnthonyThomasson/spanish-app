# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "pillow"]
# ///

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

from vocab_parser import build_vocabulary

CHAPTER_TITLES = [
    "Nouns, Articles, and Adjectives",
    "Estar, Ser, and Subject Pronouns",
    "Hay, Interrogative Words, Days, and Months",
    "Numbers, Dates, and Time",
    "Regular Verbs",
    "Irregular Verbs",
    "Ir and the Future",
    "Adjectives and Adverbs",
    "Negatives and Prepositions",
    "The Indirect Object",
    "The Direct Object",
    "Reflexive Verbs",
    "The Present Subjunctive",
    "The Preterit Tense",
    "The Imperfect Tense",
    "Ser and Estar and the Present Tense",
    "Ser and Estar in the Preterit and Imperfect Tenses",
    "The Present Progressive Tense",
    "The Past Progressive Tenses",
    "The Present Subjunctive",
    "Commands",
    "Nouns, Articles, Adjectives, and Pronouns",
    "The Present Perfect Tense",
    "The Past Perfect Tense",
    "The Future Tense",
    "The Conditional Tense",
    "The Present Perfect Subjunctive",
    "The Imperfect Subjunctive",
    "The Past Perfect Subjunctive",
    "Idioms",
]


def chapter_starts(reader: PdfReader) -> dict[int, int]:
    starts = {}
    for page_index, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        match = re.match(r"^(\d{1,2})\n", text)
        if match:
            number = int(match.group(1))
            if 1 <= number <= len(CHAPTER_TITLES) and number not in starts:
                starts[number] = page_index + 1
    missing = set(range(1, len(CHAPTER_TITLES) + 1)) - set(starts)
    if missing:
        raise RuntimeError(f"Could not locate chapters: {sorted(missing)}")
    return starts


def extract_images(reader: PdfReader, image_dir: Path) -> list[dict]:
    image_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for page_number, page in enumerate(reader.pages, start=1):
        if page_number < 29 or page_number > 740:
            continue
        for image_index, image in enumerate(page.images):
            if image.image.width < 150 or image.image.height < 20:
                continue
            filename = f"p{page_number:03d}_{image_index:02d}.png"
            path = image_dir / filename
            image.image.save(path)
            manifest.append({"page": page_number, "path": str(path)})
    return manifest


def run_ocr(root: Path, manifest: list[dict], output_path: Path) -> None:
    command = ["swift", str(root / "scripts/ocr_images.swift")]
    command.extend(item["path"] for item in manifest)
    with output_path.open("w") as output:
        subprocess.run(command, cwd=root, stdout=output, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract chapter vocabulary from the local book PDF")
    parser.add_argument("pdf", type=Path, help="Path to Complete Spanish Step-by-Step PDF")
    parser.add_argument("--refresh-ocr", action="store_true", help="Run OCR again instead of using the cache")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    work_dir = root / "extraction"
    work_dir.mkdir(exist_ok=True)
    reader = PdfReader(args.pdf)
    starts = chapter_starts(reader)
    manifest = extract_images(reader, work_dir / "images")
    (work_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    ocr_path = work_dir / "ocr.json"
    if args.refresh_ocr or not ocr_path.exists():
        run_ocr(root, manifest, ocr_path)
    vocabulary, stats = build_vocabulary(ocr_path, starts, CHAPTER_TITLES)
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "vocab.json"
    output_path.write_text(json.dumps(vocabulary, ensure_ascii=False, indent=2) + "\n")
    (work_dir / "parser-stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    word_count = sum(len(chapter["words"]) for chapter in vocabulary["chapters"])
    print(f"Extracted {word_count} words across {len(starts)} chapters from {stats['acceptedImages']} table images.")
    print(f"Vocabulary: {output_path}")
    print(f"Parser audit: {work_dir / 'parser-stats.json'}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
