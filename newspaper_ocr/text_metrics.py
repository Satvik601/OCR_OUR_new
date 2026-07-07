"""Word-level text metrics shared by the OCR verification (phase 4) and the
evaluation harness (phase 6).

Word accuracy = 1 - word_level_levenshtein(gt, ocr) / len(gt_words), floored at 0.
Tokens are lowercased with leading/trailing punctuation stripped, so "Trains?" and
"trains" count as the same word — the metric measures reading accuracy, not
punctuation fidelity.
"""

from __future__ import annotations

import string

_STRIP = string.punctuation + "‘’“”—–"


def tokenize(text: str) -> list[str]:
    """Lowercased whitespace tokens with edge punctuation stripped; empties dropped."""
    tokens = []
    for raw in text.split():
        token = raw.strip(_STRIP).lower()
        if token:
            tokens.append(token)
    return tokens


def word_levenshtein(a: list[str], b: list[str]) -> int:
    """Levenshtein distance over word sequences (insert/delete/substitute = 1)."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, wa in enumerate(a, start=1):
        cur = [i]
        for j, wb in enumerate(b, start=1):
            cost = 0 if wa == wb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def word_accuracy(ground_truth: str, ocr_text: str) -> float:
    """1 - normalized word edit distance; 0.0 floor. Empty ground truth -> 1.0 if the
    OCR text is also empty, else 0.0."""
    gt = tokenize(ground_truth)
    hyp = tokenize(ocr_text)
    if not gt:
        return 1.0 if not hyp else 0.0
    distance = word_levenshtein(gt, hyp)
    return max(0.0, 1.0 - distance / len(gt))
