import os
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from src import CHARACTERS, GRID_ROWS, GRID_COLS, CANVAS_WIDTH, CANVAS_HEIGHT, MARGIN_PX, MARKER_RADIUS_PX


def generate_template_png(output_path: str = "samples/blank_template.png") -> str:
    """Generates a 300 DPI A4 PNG template with 4 registration corner circles and an 11x8 character grid."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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
        draw.ellipse(
            [cx - 14, cy - 14, cx + 14, cy + 14],
            fill="white",
        )

    # Load clean fallback fonts for instructions and labels
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        sub_font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except IOError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    # 2. Header Instructions
    draw.text((220, 95), "HANDWRITING TO TRUETYPE (.TTF) TEMPLATE", fill="black", font=title_font)
    draw.text(
        (220, 155),
        "Write each character inside the dashed box using a dark black pen. Keep 4 corner dots visible.",
        fill="#475569",
        font=sub_font,
    )

    # 3. Grid Layout Geometry
    grid_left = MARGIN_PX + 40
    grid_right = CANVAS_WIDTH - MARGIN_PX - 40
    grid_top = 240
    grid_bottom = CANVAS_HEIGHT - MARGIN_PX - 60

    cell_w = (grid_right - grid_left) / GRID_COLS
    cell_h = (grid_bottom - grid_top) / GRID_ROWS

    header_band = 48  # Top label bar inside each cell

    for idx, char in enumerate(CHARACTERS):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x0 = int(grid_left + col * cell_w)
        y0 = int(grid_top + row * cell_h)
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)

        # Outer cell border
        draw.rectangle([x0, y0, x1, y1], outline="#94A3B8", width=3)

        # Label header background
        draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + header_band], fill="#F1F5F9")
        draw.line([(x0, y0 + header_band), (x1, y0 + header_band)], fill="#CBD5E1", width=2)

        # Target character prompt
        draw.text((x0 + 18, y0 + 8), char, fill="#0F172A", font=label_font)

        # Subtle baseline guide inside writing area (at 72% height of writing box)
        write_top = y0 + header_band
        write_h = y1 - write_top
        baseline_y = int(write_top + write_h * 0.72)
        for dash_x in range(x0 + 15, x1 - 15, 20):
            draw.line([(dash_x, baseline_y), (dash_x + 10, baseline_y)], fill="#CBD5E1", width=2)

    img.save(output_path, dpi=(300, 300))
    return output_path


def generate_template_pdf(
    png_path: str = "samples/blank_template.png",
    pdf_path: str = "samples/blank_template.pdf",
) -> str:
    """Wraps the exact-scale 300 DPI PNG into an A4 PDF document (210mm x 297mm)."""
    if not os.path.exists(png_path):
        generate_template_png(png_path)

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.image(png_path, x=0, y=0, w=210, h=297)
    pdf.output(pdf_path)
    return pdf_path


if __name__ == "__main__":
    png_file = generate_template_png()
    pdf_file = generate_template_pdf(png_file)
    print(f"Generated {png_file} and {pdf_file}")
