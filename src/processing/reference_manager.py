"""
Reference manager for presence gating.

Maintains a small set of downscaled grayscale reference images representing
"no-person" scenes and their pHashes for fast similarity gating.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import cv2

from .image_similarity import compute_phash, phash_distance


@dataclass
class _Reference:
    gray_small: np.ndarray
    phash: int


class ReferenceManager:
    def __init__(self, max_references: int = 3, small_size: Tuple[int, int] = (320, 240)):
        self._max = max_references
        self._size = small_size
        self._refs: List[_Reference] = []

    def size(self) -> int:
        return len(self._refs)

    def add_reference(self, img: np.ndarray) -> None:
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, self._size, interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (3, 3), 0)
        h = compute_phash(small)
        self._refs.append(_Reference(gray_small=small, phash=h))
        if len(self._refs) > self._max:
            # Evict oldest for simplicity
            self._refs.pop(0)

    def get_best_reference(self, img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[int]]:
        if not self._refs:
            return None, None
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, self._size, interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (3, 3), 0)
        h = compute_phash(small)

        best_ref = None
        best_dist = None
        for r in self._refs:
            d = phash_distance(h, r.phash)
            if best_dist is None or d < best_dist:
                best_dist = d
                best_ref = r.gray_small
        return best_ref, best_dist
