"""Generate the synthetic test fixtures (deterministic, seeded).

Run from the repo root:  python tests/fixtures/make_synthetic.py

Produces, next to this script:
- synthetic_simple.png : clean two-column page (headline band, two body columns, caption)
- synthetic_noisy.png  : same layout + noise, salt & pepper, illumination gradient,
                         ~1.5 deg rotation, black scanner-edge bars
- synthetic_layout.json: ground-truth block boxes for the SIMPLE image (x, y, w, h)

The layout ground truth lets unit tests assert "text survived preprocessing inside
these boxes" without depending on OCR.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20260707

W, H = 800, 1000
FONT = cv2.FONT_HERSHEY_SIMPLEX

BODY_WORDS = (
    "the quick brown fox jumps over a lazy dog while fifty judges vex "
    "my black quartz sphinx with bolts of pale liquid gas"
).split()


def _body_lines(rng: np.random.Generator, n_lines: int, words_per_line: int = 5) -> list[str]:
    return [
        " ".join(rng.choice(BODY_WORDS, size=words_per_line)) for _ in range(n_lines)
    ]


def make_simple() -> tuple[np.ndarray, list[dict]]:
    rng = np.random.default_rng(SEED)
    img = np.full((H, W), 255, np.uint8)
    blocks: list[dict] = []

    # headline band
    cv2.putText(img, "SYNTHETIC HEADLINE NEWS", (40, 90), FONT, 1.4, 0, 3, cv2.LINE_AA)
    blocks.append({"name": "headline", "bbox": [40, 55, 700, 50]})

    # two body columns, 18 lines each
    for col, x0 in enumerate((40, 420)):
        y = 180
        for line in _body_lines(rng, 18):
            cv2.putText(img, line, (x0, y), FONT, 0.5, 0, 1, cv2.LINE_AA)
            y += 28
        blocks.append({"name": f"body_col{col + 1}", "bbox": [x0, 160, 340, y - 160]})

    # caption line near the bottom
    cv2.putText(img, "figure caption: a synthetic page for tests", (40, 920), FONT, 0.45, 0, 1, cv2.LINE_AA)
    blocks.append({"name": "caption", "bbox": [40, 900, 420, 30]})

    return img, blocks


def make_noisy(simple: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(SEED + 1)
    img = simple.astype(np.float32)

    # uneven illumination: horizontal gradient 0.65 .. 1.0
    gradient = np.linspace(0.65, 1.0, W, dtype=np.float32)[None, :]
    img *= gradient

    # gaussian noise
    img += rng.normal(0, 12, img.shape).astype(np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)

    # salt & pepper specks (0.5% of pixels)
    n = int(0.005 * W * H)
    ys, xs = rng.integers(0, H, n), rng.integers(0, W, n)
    img[ys[: n // 2], xs[: n // 2]] = 0
    img[ys[n // 2 :], xs[n // 2 :]] = 255

    # mild skew (~1.5 degrees)
    m = cv2.getRotationMatrix2D((W / 2, H / 2), 1.5, 1.0)
    img = cv2.warpAffine(img, m, (W, H), borderValue=255)

    # scanner edge artifacts: black bars on the left and bottom edges
    img[:, :8] = 0
    img[-10:, :] = 0

    return img


def main() -> None:
    simple, blocks = make_simple()
    noisy = make_noisy(simple)
    cv2.imwrite(str(HERE / "synthetic_simple.png"), simple)
    cv2.imwrite(str(HERE / "synthetic_noisy.png"), noisy)
    (HERE / "synthetic_layout.json").write_text(
        json.dumps({"image_size": [W, H], "blocks": blocks}, indent=2), encoding="utf-8"
    )
    print(f"wrote fixtures to {HERE}")


if __name__ == "__main__":
    main()
