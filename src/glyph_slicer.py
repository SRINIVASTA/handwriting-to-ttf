import cv2
import numpy as np
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX


def slice_glyphs(cleaned_sheet: np.ndarray) -> dict[str, np.ndarray]:
    """
    Crops each character cell from the 2480x3508 cleaned sheet and extracts
    a solid, connected binary stroke mask (255 = ink, 0 = white paper).
    """
    grid_left = MARGIN_PX + 40
    grid_right = CANVAS_WIDTH - MARGIN_PX - 40
    grid_top = 240
    grid_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS
    header_band = 48

    glyph_masks: dict[str, np.ndarray] = {}

    open_kernel = np.ones((2, 2), np.uint8)
    close_kernel = np.ones((3, 3), np.uint8)
    dilate_kernel = np.ones((2, 2), np.uint8)

    for idx, char in enumerate(CHARACTERS):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x0 = int(grid_left + col * cell_w)
        y0 = int(grid_top + row * cell_h)
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)

        # Inset margins to exclude printed cell borders and top label header
        pad = 18
        crop = cleaned_sheet[y0 + header_band + pad : y1 - pad, x0 + pad : x1 - pad]

        # Capture dark pen ink while ignoring light gray (#CBD5E1) borders and dashed baseline
        _, binary = cv2.threshold(crop, 160, 255, cv2.THRESH_BINARY_INV)

        # 1. Remove isolated 1-pixel speckles
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)
        # 2. Bridge tiny gaps inside broken pen strokes
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)
        # 3. Lightly thicken strokes so vector outlines stay solid at all sizes
        cleaned = cv2.dilate(cleaned, dilate_kernel, iterations=1)

        if cv2.countNonZero(cleaned) >= 15:
            glyph_masks[char] = cleaned

    return glyph_masks
