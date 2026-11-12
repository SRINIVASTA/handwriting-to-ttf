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


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points into [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _find_corner_markers(gray: np.ndarray) -> np.ndarray | None:
    """Finds the centers of the 4 circular bullseye registration markers."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15
    )

    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return None

    h, w = gray.shape
    min_area = (w * h) * 0.00015
    max_area = (w * h) * 0.005

    candidates = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if not (min_area < area < max_area):
            continue

        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * (area / (perimeter * perimeter))

        # Bullseye markers have high circularity and a child inner white circle
        has_child = hierarchy[0][i][2] != -1
        if circularity > 0.72 and has_child:
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                candidates.append((cx, cy))

    if len(candidates) < 4:
        return None

    # Pick the candidate closest to each of the 4 image corners
    img_corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype="float32")
    pts = np.array(candidates, dtype="float32")
    selected = []
    for corner in img_corners:
        dists = np.linalg.norm(pts - corner, axis=1)
        selected.append(pts[np.argmin(dists)])

    return _order_points(np.array(selected, dtype="float32"))


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
        # Fallback for digital tablet templates where full canvas was uploaded directly
        warped = cv2.resize(gray, (CANVAS_WIDTH, CANVAS_HEIGHT), interpolation=cv2.INTER_CUBIC)

    # Illumination normalization: divide image by smoothed background to eliminate shadows
    bg = cv2.GaussianBlur(warped, (91, 91), 0)
    normalized = cv2.divide(warped, bg, scale=255)

    return normalized
