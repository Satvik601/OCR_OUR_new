"""Unit tests for word-level text metrics."""

from __future__ import annotations

import pytest

from newspaper_ocr.text_metrics import tokenize, word_accuracy, word_levenshtein


def test_tokenize_strips_punctuation_and_lowers():
    assert tokenize("Trains? REWORK stations:") == ["trains", "rework", "stations"]


def test_tokenize_drops_pure_punctuation():
    assert tokenize("hello -- world !!") == ["hello", "world"]


def test_levenshtein_identity():
    assert word_levenshtein(["a", "b", "c"], ["a", "b", "c"]) == 0


def test_levenshtein_substitution_insertion_deletion():
    assert word_levenshtein(["a", "b"], ["a", "x"]) == 1
    assert word_levenshtein(["a", "b"], ["a", "b", "c"]) == 1
    assert word_levenshtein(["a", "b", "c"], ["a", "c"]) == 1


def test_word_accuracy_perfect():
    assert word_accuracy("The quick brown fox", "the quick brown fox.") == pytest.approx(1.0)


def test_word_accuracy_half():
    assert word_accuracy("one two three four", "one two x y") == pytest.approx(0.5)


def test_word_accuracy_floor_at_zero():
    assert word_accuracy("a b", "x y z w v u") == 0.0


def test_word_accuracy_empty_ground_truth():
    assert word_accuracy("", "") == 1.0
    assert word_accuracy("", "noise") == 0.0
