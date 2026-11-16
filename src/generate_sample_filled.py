import os
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX, MARKER_RADIUS_PX


def generate_filled_sample(
    png_path: str = "samples/sample_filled_paper.png",
    pdf_path: str = "samples/sample_filled_paper.pdf",
) -> tuple[str, str]:
    """
    Creates an example filled-out template (PNG + A4 PDF) demonstrating proper
    stroke thickness, baseline alignment, and safe cell margins for all 88 characters.
    """
    os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)

    img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # 1. Draw 4 corner registration bullseyes
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

    # Load clean fonts for template UI and bold sample handwriting
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        sub_font = ImageFont.truetype("DejaVuSans.ttf", 25)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        # Try a natural cursive/handwriting font if installed, otherwise bold DejaVuSerif
        for candidate in ["SegoePrint.ttf", "ComicNeue-Bold.ttf", "DejaVuSerif-BoldItalic.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                sample_font = ImageFont.truetype(candidate, 118)
                break
            except IOError:
                sample_font = ImageFont.load_default()
    except IOError:
        title_font = label_font = sub_font = name_font = sample_font = ImageFont.load_default()

    # 2. Header & Sample User Name
    draw.text((220, 72), "HANDWRITING TO TRUETYPE (.TTF) TEMPLATE", fill="black", font=title_font)
    draw.text((1680, 82), "User / Font Name: SampleUser", fill="#0F172A", font=name_font)
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

    # 3. Grid Layout Geometry
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

        # Top label header
        draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + header_band], fill="#F1F5F9")
        draw.line([(x0, y0 + header_band), (x1, y0 + header_band)], fill="#CBD5E1", width=2)
        draw.text((x0 + 18, y0 + 8), char, fill="#0F172A", font=label_font)

        # Dashed writing baseline at 72% height of writing area
        write_top = y0 + header_band
        write_h = y1 - write_top
        baseline_y = int(write_top + write_h * 0.72)
        for dash_x in range(x0 + 15, x1 - 15, 20):
            draw.line([(dash_x, baseline_y), (dash_x + 10, baseline_y)], fill="#CBD5E1", width=2)

        # Draw centered sample character anchored accurately to the baseline
        cell_center_x = (x0 + x1) // 2
        draw.text(
            (cell_center_x, baseline_y),
            char,
            fill="#0A0A0A",
            font=sample_font,
            anchor="ms",  # Middle-Baseline anchor places ascenders & descenders accurately
        )

    img.save(png_path, dpi=(300, 300))

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.image(png_path, x=0, y=0, w=210, h=297)
    pdf.output(pdf_path)

    return png_path, pdf_path


if __name__ == "__main__":
    png_out, pdf_out = generate_filled_sample()
    print(f"Generated filled sample reference:\n- {png_out}\n- {pdf_out}")
