import os
import re
import html
import base64
from io import BytesIO
from fpdf import FPDF
from pypdf import PdfReader


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


def export_letter_pdf_bytes(
    letter_text: str,
    reg_ttf_path: str,
    bold_ttf_path: str,
    font_size_pt: int = 15,
) -> bytes:
    """
    Generates a valid A4 PDF in memory using the compiled Regular and Bold .ttf files.
    Splits **bold** segments explicitly so FPDF2 embeds both font styles cleanly.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=18, top=18, right=18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.add_font("CustomHWReg", style="", fname=reg_ttf_path)
    pdf.add_font("CustomHWBold", style="", fname=bold_ttf_path)
    pdf.set_font("CustomHWReg", size=font_size_pt)

    tokens = re.split(r"(\*\*.*?\*\*)", letter_text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            pdf.set_font("CustomHWBold", size=font_size_pt)
            pdf.write(h=9, text=token[2:-2])
        else:
            pdf.set_font("CustomHWReg", size=font_size_pt)
            pdf.write(h=9, text=token)

    return bytes(pdf.output())


def export_letter_pdf(
    letter_text: str,
    reg_ttf_path: str,
    bold_ttf_path: str,
    output_pdf_path: str,
    font_size_pt: int = 15,
) -> str:
    """Writes the generated A4 PDF bytes to disk and returns the output file path."""
    os.makedirs(os.path.dirname(output_pdf_path) or ".", exist_ok=True)
    pdf_bytes = export_letter_pdf_bytes(
        letter_text=letter_text,
        reg_ttf_path=reg_ttf_path,
        bold_ttf_path=bold_ttf_path,
        font_size_pt=font_size_pt,
    )
    with open(output_pdf_path, "wb") as f:
        f.write(pdf_bytes)
    return output_pdf_path


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts selectable text from every page of an uploaded PDF document."""
    reader = PdfReader(BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted.strip():
            pages_text.append(extracted.strip())
    return "\n\n".join(pages_text)


def convert_pdf_to_handwriting_bytes(
    source_pdf_bytes: bytes,
    reg_ttf_path: str,
    bold_ttf_path: str,
    font_size_pt: int = 15,
) -> tuple[str, bytes]:
    """
    Extracts text from an existing PDF (written in any standard font) and
    re-renders it into a new A4 PDF using the user's Regular & Bold handwriting fonts.
    """
    extracted_text = extract_text_from_pdf(source_pdf_bytes)
    if not extracted_text.strip():
        raise ValueError(
            "No selectable text found in the uploaded PDF. Please upload a text-based PDF."
        )

    new_pdf_bytes = export_letter_pdf_bytes(
        letter_text=extracted_text,
        reg_ttf_path=reg_ttf_path,
        bold_ttf_path=bold_ttf_path,
        font_size_pt=font_size_pt,
    )
    return extracted_text, new_pdf_bytes
