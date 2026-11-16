import os
import re
import html
import base64
from fpdf import FPDF


def render_letter_html(
    letter_text: str,
    user_name: str,
    reg_bytes: bytes,
    bold_bytes: bytes,
    font_size_px: int = 28,
) -> str:
    """
    Renders a clean, print-ready A4 HTML letter embedding both the Regular
    and Bold custom TrueType (.ttf) fonts. Words wrapped in **double asterisks**
    are styled with the Bold font weight.
    """
    b64_reg = base64.b64encode(reg_bytes).decode("utf-8")
    b64_bold = base64.b64encode(bold_bytes).decode("utf-8")

    escaped = html.escape(letter_text)
    formatted_body = re.sub(
        r"\*\*(.+?)\*\*",
        r'<span class="hw-bold">\1</span>',
        escaped,
    ).replace("\n", "<br>")

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8">
    <title>{html.escape(user_name)} - Handwritten Letter</title>
    <style>
        @font-face {{
            font-family: 'EnterpriseCustomRegular';
            src: url(data:font/ttf;base64,{b64_reg}) format('truetype');
            font-weight: 400;
        }}
        @font-face {{
            font-family: 'EnterpriseCustomBold';
            src: url(data:font/ttf;base64,{b64_bold}) format('truetype');
            font-weight: 700;
        }}
        body {{
            margin: 0;
            padding: 16px;
            background-color: #F1F5F9;
        }}
        .letter-page {{
            font-family: 'EnterpriseCustomRegular', sans-serif;
            font-size: {font_size_px}px;
            line-height: 1.65;
            color: #0F172A;
            background: #FFFFFF;
            padding: 44px 52px;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
            max-width: 780px;
            margin: auto;
        }}
        .hw-bold {{
            font-family: 'EnterpriseCustomBold', sans-serif;
            font-weight: 700;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 0;
                background: #FFFFFF;
            }}
            .letter-page {{
                border: none;
                box-shadow: none;
                padding: 18mm;
                max-width: 100%;
            }}
        }}
    </style>
    </head>
    <body>
        <div class="letter-page">{formatted_body}</div>
    </body>
    </html>
    """


def export_letter_pdf(
    letter_text: str,
    reg_ttf_path: str,
    bold_ttf_path: str,
    output_pdf_path: str,
    font_size_pt: int = 15,
) -> str:
    """
    Exports an A4 PDF letter directly using the compiled Regular and Bold .ttf files.
    Supports **bold** inline segments via FPDF2 markdown parsing.
    """
    os.makedirs(os.path.dirname(output_pdf_path) or ".", exist_ok=True)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=18, top=18, right=18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.add_font("CustomHW", style="", fname=reg_ttf_path)
    pdf.add_font("CustomHW", style="B", fname=bold_ttf_path)
    pdf.set_font("CustomHW", size=font_size_pt)

    for paragraph in letter_text.split("\n"):
        pdf.set_x(pdf.l_margin)
        if not paragraph.strip():
            pdf.ln(7)
        else:
            pdf.multi_cell(
                w=pdf.epw,
                h=9,
                text=paragraph,
                markdown=True,
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.output(output_pdf_path)
    return output_pdf_path
