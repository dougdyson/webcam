"""
Image similarity utilities for presence gating.

Includes:
- Perceptual hash (pHash) using DCT on downscaled grayscale.
- Edge-based SSIM (global) using Sobel magnitude and simplified SSIM formula.

No external dependencies beyond OpenCV and NumPy.
"""
from __future__ import annotations

import numpy as np
import cv2
from typing import Tuple


def _ensure_gray(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("Input image is None")
    if img.ndim == 2:
        return img
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    raise ValueError("Unsupported image shape for grayscale conversion")


def compute_phash(img: np.ndarray, size: int = 32, dct_size: int = 8) -> int:
    """Compute a 64-bit perceptual hash for an image.

    Pipeline: grayscale -> resize to `size` -> DCT -> take top-left `dct_size`x`dct_size`
    coefficients (excluding DC) -> threshold by median -> pack bits.
    """
    if dct_size * dct_size != 64:
        # Implementation expects 8x8 = 64 bits
        raise ValueError("dct_size must be 8 for 64-bit hash")

    gray = _ensure_gray(img)
    # Resize to square
    small = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    small_f = np.float32(small)
    dct = cv2.dct(small_f)
    # Top-left block
    dct_low = dct[:dct_size, :dct_size].copy()
    # Exclude DC component at (0,0) by setting to median later
    dct_flat = dct_low.flatten()
    # Compute median excluding DC to avoid bias
    med = np.median(dct_flat[1:]) if dct_flat.size > 1 else dct_flat[0]
    # Create bitstring (True where coefficient > median, except DC forced True/False by comparison anyway)
    bits = (dct_low > med).astype(np.uint8)
    # Pack 8x8 into 64-bit integer, row-major
    bitstring = 0
    for b in bits.flatten():
        bitstring = (bitstring << 1) | int(b)
    return int(bitstring)


def phash_distance(h1: int, h2: int) -> int:
    """Hamming distance between two 64-bit pHashes."""
    return int((h1 ^ h2).bit_count())


def edge_ssim(img1: np.ndarray, img2: np.ndarray, size: Tuple[int, int] = (320, 240)) -> float:
    """Compute a simplified SSIM on Sobel edge magnitude images.

    - Convert to grayscale
    - Resize to `size`
    - Compute Sobel X/Y and magnitude
    - Global SSIM (non-windowed) using standard constants
    """
    g1 = _ensure_gray(img1)
    g2 = _ensure_gray(img2)

    if size is not None:
        g1 = cv2.resize(g1, size, interpolation=cv2.INTER_AREA)
        g2 = cv2.resize(g2, size, interpolation=cv2.INTER_AREA)

    def sobel_mag(g: np.ndarray) -> np.ndarray:
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        # Normalize to 0..255 for SSIM constants
        mag = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        return mag

    x = sobel_mag(g1).astype(np.float32)
    y = sobel_mag(g2).astype(np.float32)

    # Global SSIM (non-windowed)
    L = 255.0
    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    mu_x = float(np.mean(x))
    mu_y = float(np.mean(y))
    sigma_x2 = float(np.var(x))
    sigma_y2 = float(np.var(y))
    sigma_xy = float(np.mean((x - mu_x) * (y - mu_y)))

    numerator = (2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)
    denominator = (mu_x ** 2 + mu_y ** 2 + C1) * (sigma_x2 + sigma_y2 + C2)
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    ssim = numerator / denominator
    # Clip to [0,1] for robustness
    return float(max(0.0, min(1.0, ssim)))

