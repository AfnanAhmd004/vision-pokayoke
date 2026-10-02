"""Synthetic production images of a bracket with known defects.

The good part: a rectangular plate, four mounting holes, an orientation notch in one corner and a
connector (bright square) fitted at a fixed spot. Defect types:

    missing_hole      one hole not drilled
    missing_connector connector not fitted
    flipped           part loaded rotated 180 degrees (notch on the wrong side)
    misplaced         part off its nominal position beyond tolerance
    scratch           surface scratch
    wrong_variant     a different bracket variant (holes in different places)
"""
from __future__ import annotations

import cv2
import numpy as np

W, H = 320, 240
PART_W, PART_H = 200, 120
HOLES = [(-75, -35), (75, -35), (-75, 35), (75, 35)]
HOLES_VARIANT_B = [(-55, -35), (55, -35), (-55, 35), (55, 35)]
CONNECTOR = (30, 0, 18)  # centre offset x, y and half-size
DEFECTS = ["ok", "missing_hole", "missing_connector", "flipped", "misplaced", "scratch", "wrong_variant"]


def _rot(pts, ang, c):
    a = np.deg2rad(ang)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (np.asarray(pts, float) @ R.T + c).astype(np.int32)


def render(defect: str = "ok", seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = np.full((H, W), 40, np.uint8)
    angle = rng.uniform(-4, 4) + (180 if defect == "flipped" else 0)
    jitter = rng.uniform(-4, 4, 2)
    if defect == "misplaced":
        jitter += rng.choice([-1, 1], 2) * rng.uniform(18, 25, 2)
    c = np.array([W / 2, H / 2]) + jitter
    hw, hh = PART_W / 2, PART_H / 2
    plate = _rot([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)], angle, c)
    cv2.fillPoly(img, [plate], 170)
    notch = _rot([(-hw, -hh), (-hw + 22, -hh), (-hw, -hh + 22)], angle, c)  # cut corner = orientation key
    cv2.fillPoly(img, [notch], 40)
    holes = list(HOLES_VARIANT_B if defect == "wrong_variant" else HOLES)
    if defect == "missing_hole":
        holes.pop(rng.integers(len(holes)))
    for hx, hy in holes:
        cv2.circle(img, tuple(_rot([(hx, hy)], angle, c)[0]), 9, 40, -1)
    if defect != "missing_connector":
        cx, cy, s = CONNECTOR
        cv2.fillPoly(img, [_rot([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)], angle, c)], 245)
    if defect == "scratch":
        p0 = _rot([(rng.uniform(-60, -10), rng.uniform(-40, 40))], angle, c)[0]
        p1 = p0 + rng.integers(30, 60, 2) * np.array([1, rng.choice([-1, 1])])
        cv2.line(img, tuple(int(v) for v in p0), tuple(int(v) for v in p1), 95, 2)
    noise = rng.normal(0, 4, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)
