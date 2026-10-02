"""Layered inspection: locate -> orientation -> position -> features -> surface, each check explainable."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from .parts import CONNECTOR, H, HOLES, PART_H, PART_W, W, render


@dataclass
class Spec:
    position_tol_px: float = 12.0
    angle_tol_deg: float = 8.0
    hole_count: int = 4
    hole_pattern_tol_px: float = 8.0
    min_connector_brightness: float = 200.0
    max_scratch_area: int = 25


@dataclass
class Result:
    passed: bool
    failed_checks: list[str] = field(default_factory=list)
    measurements: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return asdict(self)


def _locate(img):
    _, bw = cv2.threshold(img, 105, 255, cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    (cx, cy), (w, h), ang = cv2.minAreaRect(c)
    if w < h:  # normalise so the long side is the x axis
        w, h, ang = h, w, ang + 90
    return np.array([cx, cy]), ang, (w, h)


def _to_part_frame(img, centre, ang):
    """Warp the image so the part is centred and axis-aligned (up to a 180-degree ambiguity)."""
    M = cv2.getRotationMatrix2D(tuple(centre), ang, 1.0)
    M[:, 2] += np.array([W / 2, H / 2]) - centre
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=40)


def _notch_quadrant(part):
    """The notched corner is darker. Return the mean brightness of the four corner patches."""
    hw, hh, s = PART_W // 2, PART_H // 2, 10
    c = np.array([W // 2, H // 2])
    corners = {"tl": (-hw + 3, -hh + 3), "tr": (hw - 3 - s, -hh + 3), "bl": (-hw + 3, hh - 3 - s), "br": (hw - 3 - s, hh - 3 - s)}
    return {k: float(part[c[1] + y : c[1] + y + s, c[0] + x : c[0] + x + s].mean()) for k, (x, y) in corners.items()}


def inspect(img: np.ndarray, golden: np.ndarray, spec: Spec | None = None) -> Result:
    spec = spec or Spec()
    res = Result(passed=True)
    loc = _locate(img)
    if loc is None:
        return Result(False, ["part_present"], {})
    centre, ang, size = loc
    part = _to_part_frame(img, centre, ang)
    corners = _notch_quadrant(part)
    dark = min(corners, key=corners.get)
    if dark == "br":  # notch on the opposite corner: rotate the view 180 so features line up
        part, ang = cv2.rotate(part, cv2.ROTATE_180), ang + 180
    flipped = dark not in ("tl", "br")  # mirrored or unexpected corner
    rel_angle = (ang + 180) % 360 - 180
    m = res.measurements
    m.update(centre_x=float(centre[0]), centre_y=float(centre[1]), angle_deg=float(rel_angle), notch=dark)

    # 1. orientation (poka-yoke against loading the part the wrong way round)
    if flipped or abs(rel_angle) > spec.angle_tol_deg:
        res.failed_checks.append("orientation")
    # 2. position in the fixture
    offset = float(np.linalg.norm(centre - np.array([W / 2, H / 2])))
    m["offset_px"] = offset
    if offset > spec.position_tol_px:
        res.failed_checks.append("position")
    # 3. hole count and pattern (also catches the wrong variant)
    _, holes_bw = cv2.threshold(part, 105, 255, cv2.THRESH_BINARY_INV)
    inner = holes_bw[H // 2 - PART_H // 2 + 6 : H // 2 + PART_H // 2 - 6, W // 2 - PART_W // 2 + 6 : W // 2 + PART_W // 2 - 6]
    n, _, stats, cents = cv2.connectedComponentsWithStats(inner)
    def is_hole(i):  # round blob of the right size; rejects scratches and edge slivers
        w, h, a = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT], stats[i, cv2.CC_STAT_AREA]
        return 120 < a < 400 and 0.7 < w / h < 1.4 and a / (w * h) > 0.6

    found = [tuple(cents[i] - np.array(inner.shape[::-1]) / 2) for i in range(1, n) if is_hole(i)]
    m["holes"] = len(found)
    if len(found) != spec.hole_count:
        res.failed_checks.append("hole_count")
    elif max(min(np.hypot(fx - hx, fy - hy) for fx, fy in found) for hx, hy in HOLES) > spec.hole_pattern_tol_px:
        res.failed_checks.append("hole_pattern")
    # 4. connector presence
    cx, cy, s = CONNECTOR
    roi = part[H // 2 + cy - s + 3 : H // 2 + cy + s - 3, W // 2 + cx - s + 3 : W // 2 + cx + s - 3]
    m["connector_brightness"] = float(roi.mean())
    if roi.mean() < spec.min_connector_brightness:
        res.failed_checks.append("connector")
    # 5. surface: difference against the golden image in the part frame
    g_loc = _locate(golden)
    g_part = _to_part_frame(golden, g_loc[0], g_loc[1])
    diff = cv2.absdiff(cv2.GaussianBlur(part, (3, 3), 0), cv2.GaussianBlur(g_part, (3, 3), 0))
    mask = np.zeros_like(diff)
    cv2.rectangle(mask, (W // 2 - PART_W // 2 + 12, H // 2 - PART_H // 2 + 12), (W // 2 + PART_W // 2 - 12, H // 2 + PART_H // 2 - 12), 255, -1)
    for hx, hy in HOLES:  # ignore edges of expected features
        cv2.circle(mask, (W // 2 + hx, H // 2 + hy), 14, 0, -1)
    cv2.rectangle(mask, (W // 2 + cx - s - 5, H // 2 + cy - s - 5), (W // 2 + cx + s + 5, H // 2 + cy + s + 5), 0, -1)
    defect = ((diff > 45) & (mask > 0)).astype(np.uint8)
    m["surface_defect_px"] = int(defect.sum())
    if not res.failed_checks and defect.sum() > spec.max_scratch_area:
        res.failed_checks.append("surface")
    res.passed = not res.failed_checks
    return res


def golden_image() -> np.ndarray:
    return render("ok", seed=10_000)
