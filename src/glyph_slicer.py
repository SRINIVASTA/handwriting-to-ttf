import cv2
import numpy as np
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX


def slice_glyphs(cleaned_sheet: np.ndarray) -> dict[str, np.ndarray]:
    """
    Crops each character cell from the 2480x3508 cleaned sheet and extracts
    a binary stroke mask (255 = ink, 0 = white paper) for each written glyph.
    """
    grid_left = MARGIN_PX + 40
    grid_right = CANVAS_WIDTH - MARGIN_PX - 40
    grid_top = 240
    grid_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS
    header_band = 48

    glyph_masks: dict[str, np.ndarray] = {}

    # Gentle 2x2 kernel preserves thin 0.5mm pen strokes while removing single-pixel noise
    clean_kernel = np.ones((2, 2), np.uint8)

    for idx, char in enumerate(CHARACTERS):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x0 = int(grid_left + col * cell_w)
        y0 = int(grid_top + row * cell_h)
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)

        # Inset margins to exclude the printed cell borders and top label header
        pad = 12
        crop = cleaned_sheet[y0 + header_band + pad : y1 - pad, x0 + pad : x1 - pad]

        # Threshold dark pen strokes (165 captures medium-dark ink while ignoring #CBD5E1 dashed baseline)
        _, binary = cv2.threshold(crop, 165, 255, cv2.THRESH_BINARY_INV)

        # Remove single-pixel speckles without erasing thin strokes or punctuation dots
        cleaned_ink = cv2.morphologyEx(binary, cv2.MORPH_OPEN, clean_kernel)

        # Minimum 12 ink pixels ensures small punctuation (., -, ', :) is retained
        if cv2.countNonZero(cleaned_ink) >= 12:
            glyph_masks[char] = cleaned_ink

    return glyph_masks
