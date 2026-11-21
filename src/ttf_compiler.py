import os
import re
import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


NARROW_CHARS = set("il1.,;:'|!`\"()[]{}")


def sanitize_font_name(raw_name: str) -> str:
    """Converts user input (e.g. 'T A Srinivas') into a clean filename-safe prefix ('TA-Srinivas')."""
    if not raw_name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9\s-]", "", raw_name).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


def _signed_area(pts: list[tuple[int, int]]) -> float:
    """Computes signed polygon area (positive = counter-clockwise, negative = clockwise)."""
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += (x1 * y2) - (x2 * y1)
    return area / 2.0


def compile_ttf(
    glyph_masks: dict[str, np.ndarray],
    user_name: str,
    output_dir: str = "output_fonts",
    bold: bool = False,
) -> str:
    """
    Traces OpenCV contours from each glyph mask into TrueType quadratic outlines
    and exports either `<UserName>-Handwriting.ttf` (Regular) or
    `<UserName>-Handwriting-Bold.ttf` (Bold).
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_prefix = sanitize_font_name(user_name) or "Custom"
    family_name = f"{safe_prefix} Handwriting"
    style_name = "Bold" if bold else "Regular"
    ps_name = f"{safe_prefix}-Handwriting-Bold" if bold else f"{safe_prefix}-Handwriting"
    output_path = os.path.join(output_dir, f"{ps_name}.ttf")

    units_per_em = 1000
    ascender = 800
    descender = -200
    default_lsb = 42

    fb = FontBuilder(units_per_em, isTTF=True)

    glyph_order = [".notdef", "space"]
    cmap: dict[int, str] = {32: "space"}
    char_to_gname: dict[str, str] = {}

    for char in glyph_masks:
        codepoint = ord(char)
        gname = f"uni{codepoint:04X}"
        glyph_order.append(gname)
        cmap[codepoint] = gname
        char_to_gname[char] = gname

    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)

    glyph_table = {}
    metrics = {}

    # 1. Empty .notdef and space glyphs
    empty_pen = TTGlyphPen(None)
    glyph_table[".notdef"] = empty_pen.glyph()
    metrics[".notdef"] = (500, 0)

    space_pen = TTGlyphPen(None)
    glyph_table["space"] = space_pen.glyph()
    metrics["space"] = (350 if bold else 320, 0)

    # Ellipse kernel for smooth, natural bold stroke thickening
    bold_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # 2. Convert each binary glyph mask into vector contours
    for char, raw_mask in glyph_masks.items():
        gname = char_to_gname[char]
        mask = cv2.dilate(raw_mask, bold_kernel, iterations=1) if bold else raw_mask
        cell_h, cell_w = mask.shape

        scale = units_per_em / float(cell_h)
        baseline_px = cell_h * 0.72

        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        valid_contours: list[tuple[np.ndarray, bool]] = []
        min_x, max_x = cell_w, 0

        if hierarchy is not None:
            for idx, cnt in enumerate(contours):
                if cv2.contourArea(cnt) < 4.0:
                    continue

                epsilon = 1.1
                approx = cv2.approxPolyDP(cnt, epsilon, closed=True)
                if len(approx) < 3:
                    continue

                # hierarchy[0][idx][3] != -1 means this contour is an inner hole (e.g., inside 'o', 'e', 'a')
                is_hole = hierarchy[0][idx][3] != -1

                pts = approx.reshape(-1, 2)
                for px, _ in pts:
                    min_x = min(min_x, px)
                    max_x = max(max_x, px)
                valid_contours.append((pts, is_hole))

        pen = TTGlyphPen(None)

        if valid_contours and max_x >= min_x:
            lsb = 30 if char in NARROW_CHARS else default_lsb

            for pts, is_hole in valid_contours:
                font_pts = []
                for px, py in pts:
                    fx = int(round((px - min_x) * scale)) + lsb
                    fy = int(round((baseline_px - py) * scale))
                    font_pts.append((fx, fy))

                # Enforce TrueType winding order: outer strokes clockwise (< 0), holes counter-clockwise (> 0)
                area = _signed_area(font_pts)
                if (not is_hole and area > 0) or (is_hole and area < 0):
                    font_pts.reverse()

                pen.moveTo(font_pts[0])
                for pt in font_pts[1:]:
                    pen.lineTo(pt)
                pen.closePath()

            ink_width = int(round((max_x - min_x) * scale))
            min_width = 140 if char in NARROW_CHARS else 210
            glyph_width = max(ink_width + (lsb * 2), min_width)
            glyph_table[gname] = pen.glyph()
            metrics[gname] = (glyph_width, lsb)
        else:
            glyph_table[gname] = empty_pen.glyph()
            metrics[gname] = (400, 0)

    fb.setupGlyf(glyph_table)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascender, descent=descender)
    fb.setupNameTable(
        {
            "familyName": family_name,
            "styleName": style_name,
            "uniqueFontIdentifier": f"1.000;{ps_name}",
            "fullName": f"{family_name} {style_name}",
            "psName": ps_name,
            "version": "Version 1.000",
        }
    )
    fb.setupOS2(
        sTypoAscender=ascender,
        sTypoDescender=descender,
        usWinAscent=ascender,
        usWinDescent=abs(descender),
        usWeightClass=700 if bold else 400,
        fsSelection=0x0020 if bold else 0x0040,
    )
    fb.setupPost()

    fb.save(output_path)
    return output_path


def compile_font_family(
    glyph_masks: dict[str, np.ndarray],
    user_name: str,
    output_dir: str = "output_fonts",
) -> dict[str, str]:
    """Compiles both Regular and Bold TrueType fonts and returns their file paths."""
    regular_path = compile_ttf(glyph_masks, user_name=user_name, output_dir=output_dir, bold=False)
    bold_path = compile_ttf(glyph_masks, user_name=user_name, output_dir=output_dir, bold=True)
    return {"regular": regular_path, "bold": bold_path}
