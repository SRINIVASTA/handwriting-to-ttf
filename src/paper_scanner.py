import cv2
import numpy as np
from pdf2image import convert_from_bytes
from src import CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX


def load_image_from_bytes(file_bytes: bytes, filename: str) -> np.ndarray:
    """Loads an uploaded PDF (first page at 300 DPI) or image file into an OpenCV BGR array."""
    if filename.lower().endswith(".pdf"):
        pages = convert_from_bytes(file_bytes, dpi=300, first_page=1, last_page=1)
        rgb_img = np.array(pages[0])
        return cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

    file_array = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to decode uploaded image file.")
    return img


def _find_corner_markers(gray: np.ndarray) -> np.ndarray | None:
    """Finds the centers of the 4 circular corner registration markers."""
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 110, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    min_area = (w * h) * 0.00005
    max_area = (w * h) * 0.008

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (min_area < area < max_area):
            continue

        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * (area / (perimeter * perimeter))

        # Accept both solid circles and bullseyes (outer contour is always circular)
        if circularity > 0.70:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                candidates.append((cx, cy))

    if len(candidates) < 4:
        return None

    # Search strictly inside each corner quadrant (outer 25% of width/height)
    quadrants = [
        (0, 0, w * 0.28, h * 0.25, np.array([0, 0])),         # Top-Left
        (w * 0.72, 0, w, h * 0.25, np.array([w, 0])),         # Top-Right
        (w * 0.72, h * 0.75, w, h, np.array([w, h])),         # Bottom-Right
        (0, h * 0.75, w * 0.28, h, np.array([0, h])),         # Bottom-Left
    ]

    selected = []
    for x_min, y_min, x_max, y_max, corner_pt in quadrants:
        q_pts = [p for p in candidates if x_min <= p[0] <= x_max and y_min <= p[1] <= y_max]
        if not q_pts:
            return None
        q_arr = np.array(q_pts, dtype="float32")
        dists = np.linalg.norm(q_arr - corner_pt, axis=1)
        selected.append(q_arr[np.argmin(dists)])

    return np.array(selected, dtype="float32")


def scan_and_clean_sheet(file_bytes: bytes, filename: str) -> np.ndarray:
    """
    1. Reads PDF/Image scan
    2. Applies 4-point perspective warp using corner markers (falls back to resize if already flat)
    3. Normalizes paper illumination and returns a clean grayscale image (2480x3508)
    """
    bgr = load_image_from_bytes(file_bytes, filename)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    src_pts = _find_corner_markers(gray)
    if src_pts is not None:
        dst_pts = np.array(
            [
                [MARGIN_PX, MARGIN_PX],
                [CANVAS_WIDTH - MARGIN_PX, MARGIN_PX],
                [CANVAS_WIDTH - MARGIN_PX, CANVAS_HEIGHT - MARGIN_PX],
                [MARGIN_PX, CANVAS_HEIGHT - MARGIN_PX],
            ],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(gray, matrix, (CANVAS_WIDTH, CANVAS_HEIGHT))
    else:
        # Fallback for digital tablet templates where full A4 canvas was uploaded directly
        h, w = gray.shape
        aspect_ratio = w / float(h)
        if not (0.68 <= aspect_ratio <= 0.74):
            raise ValueError(
                "Could not detect all 4 corner markers. Make sure all 4 corner circles are 100% visible in the photo."
            )
        warped = cv2.resize(gray, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_CUBIC)

    # Illumination normalization: divide image by smoothed background to eliminate shadows
    bg = cv2.GaussianBlur(warped, (151, 151), 0)
    normalized = cv2.divide(warped, bg, scale=255)

    return normalized
