import os
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX, MARKER_RADIUS_PX


# 7 guided sentence lines covering every single character in CHARACTERS (A-Z, a-z, 0-9, punctuation)
SENTENCE_LINES = [
    "the quick brown fox jumps over the lazy dog.",
    "PACK MY BOX WITH FIVE DOZEN LIQUOR JUGS!",
    "Call 123-456-7890 or pay $50.99 + 18% = $60.",
    "\"Wait,\" she asked, 'is it Tom's #1 book? Yes!'",
    "Email @ user_name [v2.0] (dev/ops) {a*b & c^d}~",
    "Check: <tag> | pipe \\ slash ; colon : semi `tick`",
]


def _load_fonts():
    """Loads clean UI fonts and a bold handwriting-style sample font."""
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        prompt_font = ImageFont.truetype("DejaVuSansMono.ttf", 28)
        sub_font = ImageFont.truetype("DejaVuSans.ttf", 25)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except IOError:
        title_font = label_font = prompt_font = sub_font = name_font = ImageFont.load_default()

    sample_font = None
    for candidate in [
        "SegoePrint.ttf",
        "ComicNeue-Bold.ttf",
        "DejaVuSerif-BoldItalic.ttf",
        "DejaVuSans-Bold.ttf",
    ]:
        try:
            sample_font = ImageFont.truetype(candidate, 110)
            break
        except IOError:
            continue
    if sample_font is None:
        sample_font = ImageFont.load_default()

    return title_font, label_font, prompt_font, sub_font, name_font, sample_font


def _draw_header_and_markers(draw: ImageDraw.ImageDraw, user_name: str, filled: bool, mode: str):
    """Draws the 4 corner registration bullseyes, mode fiducial marker, and instructions."""
    corners = [
        (MARGIN_PX, MARGIN_PX),
        (CANVAS_WIDTH - MARGIN_PX, MARGIN_PX),
        (MARGIN_PX, CANVAS_HEIGHT - MARGIN_PX),
        (CANVAS_WIDTH - MARGIN_PX, CANVAS_HEIGHT - MARGIN_PX),
    ]
    for cx, cy in corners:
        draw.ellipse(
            [cx - MARKER_RADIUS_PX, cy - MARKER_RADIUS_PX, cx + MARKER_RADIUS_PX, cy + MARKER_RADIUS_PX],
            fill="black",
        )
        draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill="white")

    # Auto-detection fiducial: solid black square at top-center ONLY for 'sentence' mode
    if mode == "sentence":
        mid_x = CANVAS_WIDTH // 2
        draw.rectangle([mid_x - 24, MARGIN_PX - 24, mid_x + 24, MARGIN_PX + 24], fill="black")

    title_font, _, _, sub_font, name_font, _ = _load_fonts()

    mode_tag = "SENTENCE FLOW" if mode == "sentence" else "CLASSIC GRID"
    header_title = (
        f"HANDWRITING TO .TTF ({mode_tag}) — EXAMPLE GUIDE"
        if filled
        else f"HANDWRITING TO .TTF ({mode_tag}) TEMPLATE"
    )
    draw.text((220, 72), header_title, fill="black", font=title_font)

    display_name = user_name.strip() if user_name.strip() else ("SampleUser" if filled else "___________________________")
    draw.text((1680, 82), f"User / Font Name: {display_name}", fill="#0F172A", font=name_font)

    if mode == "sentence":
        inst_1 = "1. Write each sentence naturally along the dashed baseline—one letter per light slot."
        inst_2 = "2. Use a bold black pen (0.7-1.0 mm) and keep all 4 corner markers + top square visible."
    else:
        inst_1 = "1. Use a bold black pen (0.7-1.0 mm) and fill 50%-75% of each box height on the dashed baseline."
        inst_2 = "2. Keep 100% of letters inside box borders and ensure ALL 4 corner bullseye markers are 100% visible."

    draw.text((220, 132), inst_1, fill="#334155", font=sub_font)
    draw.text((220, 168), inst_2, fill="#334155", font=sub_font)


def _draw_grid_body(draw: ImageDraw.ImageDraw, filled: bool):
    """Renders the classic 11x8 character grid."""
    _, label_font, _, _, _, sample_font = _load_fonts()

    grid_left = MARGIN_PX + 40
    grid_right = CANVAS_WIDTH - MARGIN_PX - 40
    grid_top = 240
    grid_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS
    header_band = 48

    for idx, char in enumerate(CHARACTERS):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x0 = int(grid_left + col * cell_w)
        y0 = int(grid_top + row * cell_h)
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)

        draw.rectangle([x0, y0, x1, y1], outline="#CBD5E1", width=2)
        draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + header_band], fill="#F1F5F9")
        draw.line([(x0, y0 + header_band), (x1, y0 + header_band)], fill="#CBD5E1", width=2)
        draw.text((x0 + 18, y0 + 8), char, fill="#0F172A", font=label_font)

        write_top = y0 + header_band
        write_h = y1 - write_top
        baseline_y = int(write_top + write_h * 0.72)
        for dash_x in range(x0 + 15, x1 - 15, 20):
            draw.line([(dash_x, baseline_y), (dash_x + 10, baseline_y)], fill="#CBD5E1", width=2)

        if filled:
            cell_center_x = (x0 + x1) // 2
            draw.text((cell_center_x, baseline_y), char, fill="#0A0A0A", font=sample_font, anchor="ms")


def _draw_sentence_body(draw: ImageDraw.ImageDraw, filled: bool):
    """Renders 6 continuous guided sentence rows with subtle per-character slot dividers."""
    _, _, prompt_font, _, _, sample_font = _load_fonts()

    area_left = MARGIN_PX + 40
    area_right = CANVAS_WIDTH - MARGIN_PX - 40
    area_top = 250
    area_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    num_rows = len(SENTENCE_LINES)
    row_gap = 36
    row_h = (area_bottom - area_top - row_gap * (num_rows - 1)) / num_rows
    prompt_band = 54

    # Fixed slot width based on max sentence length (48 chars) so coordinates stay deterministic
    max_slots = max(len(line) for line in SENTENCE_LINES)
    slot_w = (area_right - area_left) / max_slots

    for r_idx, sentence in enumerate(SENTENCE_LINES):
        y0 = int(area_top + r_idx * (row_h + row_gap))
        y1 = int(y0 + row_h)

        # Row container & top reference prompt bar
        draw.rectangle([area_left, y0, area_right, y1], outline="#CBD5E1", width=2)
        draw.rectangle([area_left + 2, y0 + 2, area_right - 2, y0 + prompt_band], fill="#F1F5F9")
        draw.line([(area_left, y0 + prompt_band), (area_right, y0 + prompt_band)], fill="#CBD5E1", width=2)

        write_top = y0 + prompt_band
        write_h = y1 - write_top
        baseline_y = int(write_top + write_h * 0.74)

        # Continuous dashed baseline across the whole sentence row
        for dash_x in range(area_left + 12, area_right - 12, 22):
            draw.line([(dash_x, baseline_y), (dash_x + 11, baseline_y)], fill="#CBD5E1", width=2)

        for c_idx, ch in enumerate(sentence):
            sx0 = int(area_left + c_idx * slot_w)
            sx1 = int(sx0 + slot_w)
            slot_center_x = (sx0 + sx1) // 2

            # Print target character directly above its writing slot
            if ch != " ":
                draw.text((slot_center_x, y0 + 12), ch, fill="#0F172A", font=prompt_font, anchor="ma")
                # Faint vertical tick lines so letters stay separated without feeling like boxes
                draw.line([(sx0, write_top + 8), (sx0, y1 - 8)], fill="#E2E8F0", width=1)
                draw.line([(sx1, write_top + 8), (sx1, y1 - 8)], fill="#E2E8F0", width=1)

                if filled:
                    draw.text((slot_center_x, baseline_y), ch, fill="#0A0A0A", font=sample_font, anchor="ms")


def generate_template_png(
    output_path: str = "samples/blank_template.png",
    user_name: str = "",
    filled: bool = False,
    mode: str = "grid",
) -> str:
    """
    Generates a 300 DPI A4 PNG template in either 'grid' (11x8 boxes) or 'sentence' (guided flow) mode.
    """
    if mode not in ("grid", "sentence"):
        raise ValueError("mode must be either 'grid' or 'sentence'")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    _draw_header_and_markers(draw, user_name=user_name, filled=filled, mode=mode)

    if mode == "sentence":
        _draw_sentence_body(draw, filled=filled)
    else:
        _draw_grid_body(draw, filled=filled)

    img.save(output_path, dpi=(300, 300))
    return output_path


def generate_template_pdf(
    png_path: str = "samples/blank_template.png",
    pdf_path: str = "samples/blank_template.pdf",
    user_name: str = "",
    filled: bool = False,
    mode: str = "grid",
) -> str:
    """Wraps the exact-scale 300 DPI PNG into a valid A4 PDF document (210mm x 297mm)."""
    generate_template_png(png_path, user_name=user_name, filled=filled, mode=mode)

    os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.image(png_path, x=0, y=0, w=210, h=297)
    pdf.output(pdf_path)
    return pdf_path


def generate_all_templates() -> None:
    """Generates blank and filled templates for both Grid and Sentence modes."""
    for mode in ("grid", "sentence"):
        suffix = "" if mode == "grid" else "_sentence"
        generate_template_png(f"samples/blank_template{suffix}.png", filled=False, mode=mode)
        generate_template_pdf(
            f"samples/blank_template{suffix}.png",
            f"samples/blank_template{suffix}.pdf",
            filled=False,
            mode=mode,
        )
        generate_template_png(f"samples/sample_filled_paper{suffix}.png", filled=True, mode=mode)
        generate_template_pdf(
            f"samples/sample_filled_paper{suffix}.png",
            f"samples/sample_filled_paper{suffix}.pdf",
            filled=True,
            mode=mode,
        )


if __name__ == "__main__":
    generate_all_templates()
    print("Generated blank_template (PNG/PDF) and sample_filled_paper (PNG/PDF) in samples/.")
