import os
import re
import cv2
import numpy as np
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def sanitize_font_name(raw_name: str) -> str:
    """Converts user input (e.g. 'T A Srinivas') into a clean filename-safe prefix ('TA-Srinivas')."""
    if not raw_name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9\s-]", "", raw_name).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned


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
    safe_prefix = sanitize_font_name(user_name) or "Custom"
    family_name = f"{safe_prefix} Handwriting"
    ps_name = f"{safe_prefix}-Handwriting"
    output_path = os.path.join(output_dir, f"{ps_name}.ttf")

    units_per_em = 1000
    ascender = 800
    descender = -200
    default_lsb = 45  # Consistent left margin so typed characters do not drift

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

        valid_contours = []
        min_x, max_x = cell_w, 0

        for cnt in contours:
            # Keep small dots (i, j, period, colon, exclamation) while filtering dust
            if cv2.contourArea(cnt) < 4.0:
                continue

            # Simplify jagged pixel steps into smooth vector polylines
            epsilon = 1.1
            approx = cv2.approxPolyDP(cnt, epsilon, closed=True)
            if len(approx) < 3:
                continue

            pts = approx.reshape(-1, 2)
            for px, _ in pts:
                min_x = min(min_x, px)
                max_x = max(max_x, px)
            valid_contours.append(pts)

        pen = TTGlyphPen(None)

        if valid_contours and max_x >= min_x:
            # Normalize horizontal coordinates so every glyph starts cleanly at default_lsb
            for pts in valid_contours:
                font_pts = []
                for px, py in pts:
                    fx = int(round((px - min_x) * scale)) + default_lsb
                    fy = int(round((baseline_px - py) * scale))
                    font_pts.append((fx, fy))

                pen.moveTo(font_pts[0])
                for pt in font_pts[1:]:
                    pen.lineTo(pt)
                pen.closePath()

            ink_width = int(round((max_x - min_x) * scale))
            glyph_width = max(ink_width + (default_lsb * 2), 200)
            glyph_table[gname] = pen.glyph()
            metrics[gname] = (glyph_width, default_lsb)
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
    fb.setupOS2(
        sTypoAscender=ascender,
        sTypoDescender=descender,
        usWinAscent=ascender,
        usWinDescent=abs(descender),
    )
    fb.setupPost()

    fb.save(output_path)
    return output_path
