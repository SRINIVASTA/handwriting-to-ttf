"""
Handwriting-to-TTF Core Package
Shared grid constants and character mapping across generator, slicer, and compiler.
"""

# 88 standard printable ASCII characters arranged in an 11-row x 8-column grid
CHARACTERS = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,!?;:'\"-()[]{}/\\@#$%&*+=<>_"
)

GRID_ROWS = 11
GRID_COLS = 8

# Canonical warped image dimensions (300 DPI A4 aspect ratio)
CANVAS_WIDTH = 2480
CANVAS_HEIGHT = 3508

# Registration marker center coordinates (in pixels on the canonical canvas)
MARGIN_PX = 120
MARKER_RADIUS_PX = 35
