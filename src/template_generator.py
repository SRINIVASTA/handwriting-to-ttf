import os
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX, MARKER_RADIUS_PX


def _load_fonts():
    """Loads clean UI fonts and a bold handwriting-style sample font."""
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        sub_font = ImageFont.truetype("DejaVuSans.ttf", 25)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except IOError:
        title_font = label_font = sub_font = name_font = ImageFont.load_default()

    sample_font = None
    for candidate in [
        "SegoePrint.ttf",
        "ComicNeue-Bold.ttf",
        "DejaVuSerif-BoldItalic.ttf",
        "DejaVuSans-Bold.ttf",
    ]:
        try:
            sample_font = ImageFont.truetype(candidate, 118)
            break
        except IOError:
            continue
    if sample_font is None:
        sample_font = ImageFont.load_default()

    return title_font, label_font, sub_font, name_font, sample_font


def generate_template_png(
    output_path: str = "samples/blank_template.png",
    user_name: str = "",
    filled: bool = False,
) -> str:
    """
    Generates a 300 DPI A4 PNG template with 4 registration corner circles and an 11x8 character grid.
    When `filled=True`, populates every cell with properly aligned example characters so users
    can see exact stroke thickness, baseline placement, and cell margins.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # 1. Draw 4 solid black corner registration markers (bullseyes for reliable detection)
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

    title_font, label_font, sub_font, name_font, sample_font = _load_fonts()

    # 2. Header Instructions & User Name Field
    header_title = (
        "HANDWRITING TO TRUETYPE (.TTF) — FILLED EXAMPLE GUIDE"
        if filled
        else "HANDWRITING TO TRUETYPE (.TTF) TEMPLATE"
    )
    draw.text((220, 72), header_title, fill="black", font=title_font)

    display_name = user_name.strip() if user_name.strip() else ("SampleUser" if filled else "___________________________")
    draw.text((1680, 82), f"User / Font Name: {display_name}", fill="#0F172A", font=name_font)

    draw.text(
        (220, 132),
        "1. Use a bold black pen (0.7-1.0 mm) and fill 50%-75% of each box height on the dashed baseline.",
        fill="#334155",
        font=sub_font,
    )
    draw.text(
        (220, 168),
        "2. Keep 100% of letters inside box borders and ensure ALL 4 corner bullseye markers are 100% visible.",
        fill="#334155",
        font=sub_font,
    )

    # 3. Grid Layout Geometry (matches glyph_slicer.py coordinates)
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

        # Light gray outer border (#CBD5E1 so scanner ignores grid lines)
        draw.rectangle([x0, y0, x1, y1], outline="#CBD5E1", width=2)

        # Label header background
        draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + header_band], fill="#F1F5F9")
        draw.line([(x0, y0 + header_band), (x1, y0 + header_band)], fill="#CBD5E1", width=2)

        # Target character prompt
        draw.text((x0 + 18, y0 + 8), char, fill="#0F172A", font=label_font)

        # Dashed baseline guide inside writing area (at 72% height of writing box)
        write_top = y0 + header_band
        write_h = y1 - write_top
        baseline_y = int(write_top + write_h * 0.72)
        for dash_x in range(x0 + 15, x1 - 15, 20):
            draw.line([(dash_x, baseline_y), (dash_x + 10, baseline_y)], fill="#CBD5E1", width=2)

        # If filled=True, draw properly positioned example handwriting anchored on the baseline
        if filled:
            cell_center_x = (x0 + x1) // 2
            draw.text(
                (cell_center_x, baseline_y),
                char,
                fill="#0A0A0A",
                font=sample_font,
                anchor="ms",
            )

    img.save(output_path, dpi=(300, 300))
    return output_path


def generate_template_pdf(
    png_path: str = "samples/blank_template.png",
    pdf_path: str = "samples/blank_template.pdf",
    user_name: str = "",
    filled: bool = False,
) -> str:
    """Wraps the exact-scale 300 DPI PNG into a valid A4 PDF document (210mm x 297mm)."""
    generate_template_png(png_path, user_name=user_name, filled=filled)

    os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.image(png_path, x=0, y=0, w=210, h=297)
    pdf.output(pdf_path)
    return pdf_path


def generate_all_templates() -> None:
    """Generates both the blank templates and the filled reference templates."""
    generate_template_png("samples/blank_template.png", filled=False)
    generate_template_pdf("samples/blank_template.png", "samples/blank_template.pdf", filled=False)
    generate_template_png("samples/sample_filled_paper.png", filled=True)
    generate_template_pdf("samples/sample_filled_paper.png", "samples/sample_filled_paper.pdf", filled=True)


if __name__ == "__main__":
    generate_all_templates()
    print("Generated blank_template (PNG/PDF) and sample_filled_paper (PNG/PDF) in samples/.")
