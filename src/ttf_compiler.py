import os
import re
import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def sanitize_font_name(raw_name: str) -> str:
    """Converts user input (e.g. 'T A Srinivas') into a clean filename-safe prefix ('TA-Srinivas')."""
    cleaned = re.sub(r"[^A-Za-z0-9\s-]", "", raw_name).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned if cleaned else "Custom"


def compile_ttf(
    glyph_masks: dict[str, np.ndarray],
    user_name: str,
    output_dir: str = "output_fonts",
) -> str:
    """
    Traces OpenCV contours from each glyph mask into TrueType quadratic outlines
    and exports `<UserName>-Handwriting.ttf`.
    """
    os.makedirs(output_dir, exist_ok=True)
    safe_prefix = sanitize_font_name(user_name)
    family_name = f"{safe_prefix} Handwriting"
    ps_name = f"{safe_prefix}-Handwriting"
    output_path = os.path.join(output_dir, f"{ps_name}.ttf")

    units_per_em = 1000
    ascender = 800
    descender = -200

    fb = FontBuilder(units_per_em, isTTF=True)

    # Register .notdef, space, and all captured characters
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
    metrics["space"] = (320, 0)

    # 2. Convert each binary glyph mask into vector contours
    for char, mask in glyph_masks.items():
        gname = char_to_gname[char]
        cell_h, cell_w = mask.shape

        # Scale cell height to match font EM box (1000 units)
        scale = units_per_em / float(cell_h)
        baseline_px = cell_h * 0.72  # Matches dashed baseline on the template

        # Find outer and inner (hole) contours
        contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        pen = TTGlyphPen(None)
        min_x, max_x = cell_w, 0
        has_contours = False

        for cnt in contours:
            if cv2.contourArea(cnt) < 12:
                continue

            # Simplify jagged pixel steps into smooth vector polylines
            epsilon = 1.4
            approx = cv2.approxPolyDP(cnt, epsilon, closed=True)
            if len(approx) < 3:
                continue

            has_contours = True
            pts = approx.reshape(-1, 2)

            # Transform pixel coordinates (Y-down) to Font coordinates (Y-up from baseline)
            font_pts = []
            for px, py in pts:
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                fx = int(round(px * scale))
                fy = int(round((baseline_px - py) * scale))
                font_pts.append((fx, fy))

            # Shift left side-bearing to x = 40 units
            pen.moveTo(font_pts[0])
            for pt in font_pts[1:]:
                pen.lineTo(pt)
            pen.closePath()

        if has_contours and max_x > min_x:
            glyph_width = int(round((max_x - min_x) * scale)) + 110
            lsb = int(round(min_x * scale))
            glyph_table[gname] = pen.glyph()
            metrics[gname] = (max(glyph_width, 220), lsb)
        else:
            glyph_table[gname] = empty_pen.glyph()
            metrics[gname] = (400, 0)

    fb.setupGlyf(glyph_table)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascender, descent=descender)
    fb.setupNameTable(
        {
            "familyName": family_name,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"1.000;{ps_name}",
            "fullName": f"{family_name} Regular",
            "psName": ps_name,
            "version": "Version 1.000",
        }
    )
    fb.setupOS2(sTypoAscender=ascender, sTypoDescender=descender, usWinAscent=ascender, usWinDescent=abs(descender))
    fb.setupPost()

    fb.save(output_path)
    return output_path
