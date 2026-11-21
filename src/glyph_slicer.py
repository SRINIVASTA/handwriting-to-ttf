import cv2
import numpy as np
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX
from src.template_generator import SENTENCE_LINES


def _extract_clean_ink(crop: np.ndarray) -> np.ndarray:
    """Applies thresholding and morphological cleanup to isolate solid pen strokes."""
    open_kernel = np.ones((2, 2), np.uint8)
    close_kernel = np.ones((3, 3), np.uint8)
    dilate_kernel = np.ones((2, 2), np.uint8)

    # Capture dark pen ink while ignoring light gray (#CBD5E1) borders and dashed baseline
    _, binary = cv2.threshold(crop, 160, 255, cv2.THRESH_BINARY_INV)

    # 1. Remove isolated 1-pixel speckles
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)
    # 2. Bridge tiny gaps inside broken pen strokes
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)
    # 3. Lightly thicken strokes so vector outlines stay solid at all sizes
    cleaned = cv2.dilate(cleaned, dilate_kernel, iterations=1)
    return cleaned


def detect_template_mode(cleaned_sheet: np.ndarray) -> str:
    """
    Auto-detects 'sentence' vs 'grid' mode by checking the top-center fiducial square
    at (CANVAS_WIDTH // 2, MARGIN_PX).
    """
    mid_x = CANVAS_WIDTH // 2
    roi = cleaned_sheet[
        max(0, MARGIN_PX - 16) : MARGIN_PX + 16,
        max(0, mid_x - 16) : mid_x + 16,
    ]
    if roi.size > 0 and float(np.mean(roi)) < 110.0:
        return "sentence"
    return "grid"


def _slice_grid_mode(cleaned_sheet: np.ndarray) -> dict[str, np.ndarray]:
    """Extracts glyphs from the classic 11x8 character box grid."""
    grid_left = MARGIN_PX + 40
    grid_right = CANVAS_WIDTH - MARGIN_PX - 40
    grid_top = 240
    grid_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS
    header_band = 48
    pad = 18

    glyph_masks: dict[str, np.ndarray] = {}

    for idx, char in enumerate(CHARACTERS):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x0 = int(grid_left + col * cell_w)
        y0 = int(grid_top + row * cell_h)
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)

        crop = cleaned_sheet[y0 + header_band + pad : y1 - pad, x0 + pad : x1 - pad]
        cleaned = _extract_clean_ink(crop)

        if cv2.countNonZero(cleaned) >= 15:
            glyph_masks[char] = cleaned

    return glyph_masks


def _score_glyph_candidate(mask: np.ndarray) -> float:
    """
    Scores a candidate glyph mask when a character appears multiple times in sentences.
    Rewards well-centered ink with clean stroke density and penalizes edge-touching ink.
    """
    ink_pixels = cv2.countNonZero(mask)
    if ink_pixels < 15:
        return -1.0

    h, w = mask.shape
    ys, xs = np.where(mask > 0)

    # Penalize strokes touching the left/right edges (likely bleed-over from neighbor letter)
    edge_touches = int(np.sum(xs <= 1) + np.sum(xs >= w - 2))

    # Reward horizontal centering inside the slot
    center_x = float(np.mean(xs))
    center_offset = abs(center_x - (w / 2.0)) / max(w, 1)

    return float(ink_pixels) * (1.0 - 0.5 * center_offset) - (edge_touches * 25.0)


def _slice_sentence_mode(cleaned_sheet: np.ndarray) -> dict[str, np.ndarray]:
    """Extracts glyphs from the 6 guided sentence lines and picks the cleanest sample per character."""
    area_left = MARGIN_PX + 40
    area_right = CANVAS_WIDTH - MARGIN_PX - 40
    area_top = 250
    area_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    num_rows = len(SENTENCE_LINES)
    row_gap = 36
    row_h = (area_bottom - area_top - row_gap * (num_rows - 1)) / num_rows
    prompt_band = 54

    max_slots = max(len(line) for line in SENTENCE_LINES)
    slot_w = (area_right - area_left) / max_slots

    pad_y = 14
    pad_x = 4  # Narrow horizontal pad keeps slot wide while trimming divider lines

    glyph_masks: dict[str, np.ndarray] = {}
    best_scores: dict[str, float] = {}

    for r_idx, sentence in enumerate(SENTENCE_LINES):
        y0 = int(area_top + r_idx * (row_h + row_gap))
        y1 = int(y0 + row_h)

        for c_idx, char in enumerate(sentence):
            if char == " " or char not in CHARACTERS:
                continue

            sx0 = int(area_left + c_idx * slot_w)
            sx1 = int(sx0 + slot_w)

            crop = cleaned_sheet[y0 + prompt_band + pad_y : y1 - pad_y, sx0 + pad_x : sx1 - pad_x]
            cleaned = _extract_clean_ink(crop)

            score = _score_glyph_candidate(cleaned)
            if score > 0 and score > best_scores.get(char, -1.0):
                best_scores[char] = score
                glyph_masks[char] = cleaned

    return glyph_masks


def slice_glyphs(cleaned_sheet: np.ndarray, mode: str | None = None) -> dict[str, np.ndarray]:
    """
    Crops each character cell from the 2480x3508 cleaned sheet and extracts
    a solid, connected binary stroke mask (255 = ink, 0 = white paper).
    Automatically detects 'grid' vs 'sentence' template mode if `mode` is None.
    """
    resolved_mode = mode if mode in ("grid", "sentence") else detect_template_mode(cleaned_sheet)

    if resolved_mode == "sentence":
        return _slice_sentence_mode(cleaned_sheet)
    return _slice_grid_mode(cleaned_sheet)
