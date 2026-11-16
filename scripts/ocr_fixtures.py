"""Synthetic OCR helpers for the Python tests. All text in the tests is invented, never from the book."""


def obs(text: str, x: float, y: float, width: float = 0.3, height: float = 0.05) -> dict:
    """One OCR observation: `y` is the line's vertical centre (0 = bottom, 1 = top)."""
    return {"text": text, "x": x, "y": y - height / 2, "width": width, "height": height}


def image(name: str, observations: list[dict]) -> dict:
    return {"path": f"/tmp/images/{name}", "width": 600, "height": 400, "observations": observations}


def two_columns(rows: list[tuple[str, str]], name: str = "p050_00.png", left_x: float = 0.0, right_x: float = 0.55) -> dict:
    """An image with Spanish on the left and English on the right, one row per pair, top to bottom."""
    observations = []
    for index, (spanish, english) in enumerate(rows):
        y = 0.9 - index * 0.12
        observations.append(obs(spanish, left_x, y))
        observations.append(obs(english, right_x, y))
    return image(name, observations)
