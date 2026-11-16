import os
import base64
import streamlit as st
import cv2
from src import CHARACTERS
from src.template_generator import generate_all_templates
from src.paper_scanner import scan_and_clean_sheet
from src.glyph_slicer import slice_glyphs
from src.ttf_compiler import compile_font_family, sanitize_font_name

st.set_page_config(
    page_title="Handwriting to TTF Font Generator",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure samples directory, blank templates, and filled example templates exist on startup
os.makedirs("samples", exist_ok=True)
PNG_TEMPLATE = "samples/blank_template.png"
PDF_TEMPLATE = "samples/blank_template.pdf"
FILLED_PNG = "samples/sample_filled_paper.png"
FILLED_PDF = "samples/sample_filled_paper.pdf"

if not all(os.path.exists(p) for p in [PNG_TEMPLATE, PDF_TEMPLATE, FILLED_PNG, FILLED_PDF]):
    generate_all_templates()

with open(PDF_TEMPLATE, "rb") as f:
    PDF_BYTES = f.read()
with open(PNG_TEMPLATE, "rb") as f:
    PNG_BYTES = f.read()
with open(FILLED_PDF, "rb") as f:
    FILLED_PDF_BYTES = f.read()

# ==========================================
# SIDEBAR: QUICK CONTROLS & VISIBILITY GUIDE
# ==========================================
with st.sidebar:
    st.title("✒️ Handwriting to TTF")
    st.caption("Local TrueType Font Compiler")
    st.divider()

    st.subheader("1. Download Blank Template")
    st.download_button(
        label="📄 Download A4 PDF Template",
        data=PDF_BYTES,
        file_name="blank_template.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="sb_pdf_dl",
    )
    st.download_button(
        label="📱 Download Tablet PNG Template",
        data=PNG_BYTES,
        file_name="blank_template.png",
        mime="image/png",
        use_container_width=True,
        key="sb_png_dl",
    )
    st.download_button(
        label="📥 Download Filled Example PDF",
        data=FILLED_PDF_BYTES,
        file_name="sample_filled_paper.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="sb_filled_dl",
    )

    st.divider()

    st.subheader("2. Required Font / User Name")
    user_name = st.text_input(
        "Enter User Name (Required) *",
        value="",
        placeholder="e.g., Srinivas",
        max_chars=40,
        help="Required to name your font files and embed font metadata.",
    ).strip()

    sanitized_name = sanitize_font_name(user_name) if user_name else ""
    is_valid_name = bool(sanitized_name)

    if is_valid_name:
        st.caption(
            f"Regular: **`{sanitized_name}-Handwriting.ttf`**\n\n"
            f"Bold: **`{sanitized_name}-Handwriting-Bold.ttf`**"
        )
    else:
        st.warning("⚠️ Please enter your **User Name** to enable font generation.")

    st.divider()

    st.subheader("3. Upload Filled Sheet")
    uploaded_file = st.file_uploader(
        "Upload scan or photo (PDF, JPG, PNG)",
        type=["pdf", "jpg", "jpeg", "png"],
    )

    generate_clicked = st.button(
        "🚀 Generate Regular & Bold .TTF",
        type="primary",
        use_container_width=True,
        disabled=(uploaded_file is None or not is_valid_name),
    )

    st.divider()
    with st.expander("📐 100% Clarity & Visibility Guide", expanded=True):
        st.markdown(
            "- **100% Corner Visibility:** Keep all **4 corner bullseye markers** completely inside the photo frame.\n"
            "- **80%–95% Frame Fill:** Fill most of the camera frame with even lighting and zero shadows.\n"
            "- **50%–75% Cell Height:** Write each letter large enough to fill half to three-quarters of its box on the dashed baseline.\n"
            "- **100% Inside Borders:** Keep ascenders and descenders inside the cell lines so they are not sliced off.\n"
            "- **Bold Black Ink:** Use a **0.7 mm – 1.0 mm black pen** (or thick stylus brush) for clean stroke detection."
        )

# ==========================================
# MAIN WORKSPACE: TEMPLATE, EXAMPLE & PREVIEW
# ==========================================
st.header("Custom TrueType (.TTF) Font Studio")

top_col1, top_col2 = st.columns([1.2, 1])

with top_col1:
    st.subheader("Step 1: Get Your Blank Template")
    st.write("Print the **A4 PDF** at **100% Actual Size** (disable Fit-to-Page) or draw directly on the **300 DPI PNG**.")
    dl_c1, dl_c2 = st.columns(2)
    with dl_c1:
        st.download_button(
            label="📄 Download A4 PDF",
            data=PDF_BYTES,
            file_name="blank_template.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="main_pdf_dl",
        )
    with dl_c2:
        st.download_button(
            label="📱 Download 300 DPI PNG",
            data=PNG_BYTES,
            file_name="blank_template.png",
            mime="image/png",
            use_container_width=True,
            key="main_png_dl",
        )

    with st.expander("👀 See How to Fill the Template (Filled Example Sheet)", expanded=(uploaded_file is None)):
        st.image(
            FILLED_PNG,
            caption="Example: Write every character bold and centered on the dashed baseline, keeping all 4 corner bullseyes visible.",
            use_container_width=True,
        )
        st.download_button(
            label="📥 Download Filled Example PDF (Reference)",
            data=FILLED_PDF_BYTES,
            file_name="sample_filled_paper.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="main_filled_dl",
        )

with top_col2:
    st.subheader("Step 2: Font Status")
    if not is_valid_name:
        st.error("1️⃣ **User Name Required:** Enter your name in the sidebar before generating your fonts.")
    else:
        st.success(f"1️⃣ **Font Family:** `{sanitized_name} Handwriting` (Regular & Bold)")

    if uploaded_file is None:
        st.info("2️⃣ **Scan Needed:** Upload your completed sheet in the sidebar (or test with `sample_filled_paper.pdf`).")
    else:
        st.success(f"2️⃣ **File Ready:** `{uploaded_file.name}`")

st.divider()

if uploaded_file is None or not is_valid_name:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1. Print or Draw")
        st.write("Download the **A4 PDF** to write on paper with a bold black pen, or use the **PNG** on a tablet.")
    with col2:
        st.markdown("### 2. Follow the Filled Guide")
        st.write("Match the filled reference above: rest letters on the **dashed line** and keep all **4 corner markers** 100% visible.")
    with col3:
        st.markdown("### 3. Enter Name & Compile")
        st.write("Type your **User Name** in the sidebar, upload your scan, and download both Regular & Bold `.ttf` fonts.")

else:
    should_compile = (
        generate_clicked
        or "compiled_ttf" not in st.session_state
        or "reg_filename" not in st.session_state["compiled_ttf"]
        or st.session_state.get("last_file") != uploaded_file.name
        or st.session_state.get("last_name") != sanitized_name
    )

    if should_compile:
        with st.spinner("Aligning 4 corner markers, isolating pen strokes, and compiling Regular & Bold vector glyphs..."):
            try:
                file_bytes = uploaded_file.getvalue()
                cleaned_sheet = scan_and_clean_sheet(file_bytes, uploaded_file.name)
                glyph_masks = slice_glyphs(cleaned_sheet)

                if not glyph_masks:
                    st.error(
                        "No handwriting strokes detected. Make sure a dark black pen was used "
                        "and all 4 corner registration markers are 100% visible."
                    )
                    st.session_state.pop("compiled_ttf", None)
                else:
                    paths = compile_font_family(glyph_masks, user_name=sanitized_name)
                    with open(paths["regular"], "rb") as reg_f:
                        reg_bytes = reg_f.read()
                    with open(paths["bold"], "rb") as bold_f:
                        bold_bytes = bold_f.read()

                    st.session_state["compiled_ttf"] = {
                        "reg_filename": os.path.basename(paths["regular"]),
                        "reg_bytes": reg_bytes,
                        "bold_filename": os.path.basename(paths["bold"]),
                        "bold_bytes": bold_bytes,
                        "glyph_masks": glyph_masks,
                    }
                    st.session_state["last_file"] = uploaded_file.name
                    st.session_state["last_name"] = sanitized_name
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

    # Render compiled Regular + Bold results from session state
    if "compiled_ttf" in st.session_state and "reg_filename" in st.session_state["compiled_ttf"]:
        result = st.session_state["compiled_ttf"]
        glyph_masks = result["glyph_masks"]
        captured_count = len(glyph_masks)
        total_chars = len(CHARACTERS)
        coverage_pct = round((captured_count / total_chars) * 100, 1)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Font Family", f"{sanitized_name} Handwriting")
        m2.metric("Captured Glyphs", f"{captured_count} / {total_chars}")
        m3.metric("Character Coverage", f"{coverage_pct}%")
        m4.metric("Styles Generated", "Regular & Bold")

        if captured_count < total_chars:
            st.warning(
                f"⚠️ **{total_chars - captured_count} character(s) were not detected.** "
                "Check the **Inspect Extracted Pen Strokes** grid below. For missing letters, write slightly larger "
                "(**50%–75%** of cell height) with a bolder black pen and verify all **4 corner markers** are 100% visible."
            )

        # Side-by-side Download Buttons for Regular & Bold TTFs
        dl_reg, dl_bold = st.columns(2)
        with dl_reg:
            st.download_button(

                label=f"⬇️ Download Regular ({result['reg_filename']})",
                data=result["reg_bytes"],
                file_name=result["reg_filename"],
                mime="font/ttf",
                type="primary",
                use_container_width=True,
            )
        with dl_bold:
            st.download_button(
                label=f"⬇️ Download Bold ({result['bold_filename']})",
                data=result["bold_bytes"],
                file_name=result["bold_filename"],
                mime="font/ttf",
                type="primary",
                use_container_width=True,
            )

        st.divider()

        # Live Browser Font Tester for both Regular and Bold
        b64_reg = base64.b64encode(result["reg_bytes"]).decode("utf-8")
        b64_bold = base64.b64encode(result["bold_bytes"]).decode("utf-8")
        st.subheader("Live Handwriting Font Preview (Regular & Bold)")

        p_col1, p_col2 = st.columns([3, 1])
        with p_col1:
            sample_text = st.text_input(
                "Type text below to preview both styles:",
                value="The quick brown fox jumps over the lazy dog! 0123456789",
            )
        with p_col2:
            font_size = st.slider("Preview Size (px)", min_value=24, max_value=72, value=42)

        st.markdown(
            f"""
            <style>
            @font-face {{
                font-family: 'UserCustomRegular';
                src: url(data:font/ttf;base64,{b64_reg}) format('truetype');
                font-weight: 400;
            }}
            @font-face {{
                font-family: 'UserCustomBold';
                src: url(data:font/ttf;base64,{b64_bold}) format('truetype');
                font-weight: 700;
            }}
            .preview-label {{
                font-size: 13px;
                font-weight: 600;
                color: #475569;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .custom-preview-reg {{
                font-family: 'UserCustomRegular', sans-serif;
                font-size: {font_size}px;
                line-height: 1.4;
                padding: 20px;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                background-color: #F8FAFC;
                color: #0F172A;
                margin-bottom: 16px;
            }}
            .custom-preview-bold {{
                font-family: 'UserCustomBold', sans-serif;
                font-size: {font_size}px;
                line-height: 1.4;
                padding: 20px;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                background-color: #F8FAFC;
                color: #0F172A;
            }}
            </style>
            <div class="preview-label">Regular (Weight 400)</div>
            <div class="custom-preview-reg">{sample_text}</div>
            <div class="preview-label">Bold (Weight 700)</div>
            <div class="custom-preview-bold">{sample_text}</div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Extracted Strokes Grid
        with st.expander("🔍 Inspect Extracted Pen Strokes", expanded=True):
            chars = list(glyph_masks.keys())
            cols_per_row = 11
            for row_start in range(0, len(chars), cols_per_row):
                cols = st.columns(cols_per_row)
                for idx, ch in enumerate(chars[row_start : row_start + cols_per_row]):
                    inv_preview = cv2.bitwise_not(glyph_masks[ch])
                    cols[idx].image(inv_preview, caption=ch, use_container_width=True)
