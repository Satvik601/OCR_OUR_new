"""Stage 1 — preprocessing: page scan -> clean binary image (ink=255, bg=0).

Steps (see ARCHITECTURE.md): grayscale -> Gaussian blur -> inverted threshold
(default: global Otsu OR'd with adaptive Gaussian) -> morphological opening ->
border clearing.

All parameters come from the ``preprocessing`` section of config.yaml and are
validated here so a bad config edit fails with a clear message naming the key,
not an opaque OpenCV assertion.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import Config


def _require_odd(value: int, minimum: int, key: str) -> None:
    if not isinstance(value, int) or value < minimum or value % 2 == 0:
        raise ValueError(f"{key} must be an odd integer >= {minimum}, got {value!r}")


def to_grayscale(image: np.ndarray, method: str = "luminance") -> np.ndarray:
    """Accept BGR/BGRA or already-grayscale input; return a single-channel copy.

    method:
    - "luminance":   standard weighted conversion (cv2 BGR2GRAY).
    - "min_channel": darkest of B/G/R per pixel — colored ink (red/blue text,
      reversed boxes) stays dark instead of washing out to mid-gray, at the
      cost of colored photo areas darkening too.
    """
    if image.ndim == 3:
        if image.shape[-1] == 1:  # single channel with explicit axis
            return image[:, :, 0].copy()
        if image.shape[-1] not in (3, 4):
            raise ValueError(f"expected 1, 3 or 4 channels, got shape {image.shape}")
        if method == "min_channel":
            return image[:, :, :3].min(axis=2)
        if method == "luminance":
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        raise ValueError(f"preprocessing.grayscale_method must be 'luminance' or 'min_channel', got {method!r}")
    if image.ndim == 2:
        if method not in ("luminance", "min_channel"):
            raise ValueError(f"preprocessing.grayscale_method must be 'luminance' or 'min_channel', got {method!r}")
        return image.copy()
    raise ValueError(f"expected 2D or 3D image array, got shape {image.shape}")


def binarize(gray: np.ndarray, p: Config) -> np.ndarray:
    """Gaussian blur + thresholding, inverted so ink becomes 255.

    `preprocessing.threshold_method` selects:
    - "otsu":          global Otsu. Fails on pages where large dark masses (headlines,
                       photos) drag the global threshold below small faint body text
                       (verification loop iters 1-2 on the real page).
    - "adaptive":      local Gaussian adaptive threshold. Keeps small text, but hollows
                       out large solid dark areas.
    - "otsu+adaptive": union of both (default) — solid elements from Otsu, small/faint
                       text from adaptive.
    """
    k = p.gaussian_kernel
    _require_odd(k, 1, "preprocessing.gaussian_kernel")
    blurred = cv2.GaussianBlur(gray, (k, k), 0)
    method = p.threshold_method
    otsu = adaptive = None
    if method in ("otsu", "otsu+adaptive"):
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    if method in ("adaptive", "otsu+adaptive"):
        _require_odd(p.adaptive_block_size, 3, "preprocessing.adaptive_block_size")
        adaptive = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            p.adaptive_block_size,
            p.adaptive_c,
        )
    if otsu is not None and adaptive is not None:
        return cv2.bitwise_or(otsu, adaptive)
    if otsu is not None:
        return otsu
    if adaptive is not None:
        return adaptive
    raise ValueError(f"unknown preprocessing.threshold_method: {method!r}")


def remove_specks(binary: np.ndarray, kernel_size: int, iterations: int) -> np.ndarray:
    """Morphological opening: erodes away speckles smaller than the kernel."""
    if not isinstance(kernel_size, int) or kernel_size < 1:
        # a 0x0 kernel would silently disable speck removal
        raise ValueError(f"preprocessing.morph_open_kernel must be >= 1, got {kernel_size!r}")
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=iterations)


def clear_border(binary: np.ndarray, margin: int) -> np.ndarray:
    """Remove connected components whose bbox comes within `margin` px of a page edge.

    Targets scanner-edge artifacts (black bars, page-edge shadows). Vectorized:
    flag doomed labels, then zero them in one pass.
    """
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    height, width = binary.shape
    x = stats[:, cv2.CC_STAT_LEFT]
    y = stats[:, cv2.CC_STAT_TOP]
    w = stats[:, cv2.CC_STAT_WIDTH]
    h = stats[:, cv2.CC_STAT_HEIGHT]
    touches = (x <= margin) | (y <= margin) | (x + w >= width - margin) | (y + h >= height - margin)
    touches[0] = False  # label 0 is the background
    if not touches.any():
        return binary
    return np.where(touches[labels], 0, binary).astype(np.uint8)


def preprocess(image: np.ndarray, config: Config) -> np.ndarray:
    """Full stage-1 chain. Returns uint8 binary image, ink=255, background=0."""
    if image.dtype != np.uint8:
        raise ValueError(f"expected uint8 image, got dtype {image.dtype}")
    p = config.preprocessing
    gray = to_grayscale(image, p.grayscale_method)
    binary = binarize(gray, p)
    opened = remove_specks(binary, p.morph_open_kernel, p.morph_open_iterations)
    return clear_border(opened, p.border_margin_px)
