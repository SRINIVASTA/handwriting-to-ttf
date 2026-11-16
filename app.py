import os
import base64
import streamlit as st
import cv2
from src.template_generator import generate_template_png, generate_template_pdf
from src.paper_scanner import scan_and_clean_sheet
from src.glyph_slicer import slice_glyphs
from src.ttf_compiler import compile_ttf, sanitize_font_name

st.set_page_config(
    page_title="Handwriting to TTF Font Generator",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure samples directory and blank templates exist on startup
os.makedirs("samples", exist_ok=True)
PNG_TEMPLATE = "samples/blank_template.png"
PDF_TEMPLATE = "samples/blank_template.pdf"

if not os.path.exists(PNG_TEMPLATE):
    generate_template_png(PNG_TEMPLATE)
if not os.path.exists(PDF_TEMPLATE):
    generate_template_pdf(PNG_TEMPLATE, PDF_TEMPLATE)

with open(PDF_TEMPLATE, "rb") as f:
    PDF_BYTES = f.read()
with open(PNG_TEMPLATE, "rb") as f:
    PNG_BYTES = f.read()

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

    st.divider()

    st.subheader("2. Required Font / User Name")
    user_name = st.text_input(
        "Enter User Name (Required) *",
        value="",
        placeholder="e.g., Srinivas",
        max_chars=40,
        help="Required to name your font file and embed font metadata.",
    ).strip()

    sanitized_name = sanitize_font_name(user_name) if user_name else ""
    is_valid_name = bool(sanitized_name)

    if is_valid_name:
        st.caption(f"Output file: **`{sanitized_name}-Handwriting.ttf`**")
    else:
        st.warning("⚠️ Please enter your **User Name** to enable font generation.")

    st.divider()

    st.subheader("3. Upload Filled Sheet")
    uploaded_file = st.file_uploader(
        "Upload scan or photo (PDF, JPG, PNG)",
        type=["pdf", "jpg", "jpeg", "png"],
    )

    generate_clicked = st.button(
        "🚀 Generate .TTF Font",
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
# MAIN WORKSPACE: TEMPLATE, NAME & PREVIEW
# ==========================================
st.header("Custom TrueType (.TTF) Font Studio")

# Always-visible Step 1 & Step 2 bar in the main workspace
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

with top_col2:
    st.subheader("Step 2: Font Status")
    if not is_valid_name:
        st.error("1️⃣ **User Name Required:** Enter your name in the sidebar before generating your font.")
    else:
        st.success(f"1️⃣ **User Name:** `{sanitized_name}` (`{sanitized_name}-Handwriting.ttf`)")

    if uploaded_file is None:
        st.info("2️⃣ **Scan Needed:** Upload your completed sheet in the sidebar.")
    else:
        st.success(f"2️⃣ **File Ready:** `{uploaded_file.name}`")

st.divider()

if uploaded_file is None or not is_valid_name:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1. Print or Draw")
        st.write("Download the **A4 PDF** to write on paper with a bold black pen, or use the **PNG** on a tablet.")
    with col2:
        st.markdown("### 2. Keep 100% Visible")
        st.write("Ensure all **4 corner bullseyes** are visible and letters fill **50%–75%** of each box height.")
    with col3:
        st.markdown("### 3. Enter Name & Compile")
        st.write("Type your **User Name** in the sidebar, upload your scan, and download your `.ttf` font.")

else:
    should_compile = (
        generate_clicked
        or "compiled_ttf" not in st.session_state
        or st.session_state.get("last_file") != uploaded_file.name
        or st.session_state.get("last_name") != sanitized_name
    )

    if should_compile:
        with st.spinner("Aligning 4 corner markers, isolating pen strokes, and compiling vector glyphs..."):
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
                    ttf_path = compile_ttf(glyph_masks, user_name=sanitized_name)
                    with open(ttf_path, "rb") as ttf_file:
                        ttf_bytes = ttf_file.read()

                    st.session_state["compiled_ttf"] = {
                        "path": ttf_path,
                        "filename": os.path.basename(ttf_path),
                        "bytes": ttf_bytes,
                        "glyph_masks": glyph_masks,
                    }
                    st.session_state["last_file"] = uploaded_file.name
                    st.session_state["last_name"] = sanitized_name
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

    # Render compiled results from session state
    if "compiled_ttf" in st.session_state:
        result = st.session_state["compiled_ttf"]
        glyph_masks = result["glyph_masks"]
        captured_count = len(glyph_masks)
        coverage_pct = round((captured_count / 88) * 100, 1)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Output Font", result["filename"])
        m2.metric("Captured Glyphs", f"{captured_count} / 88")
        m3.metric("Character Coverage", f"{coverage_pct}%")
        m4.metric("File Size", f"{len(result['bytes']) / 1024:.1f} KB")

        if captured_count < 88:
            st.warning(
                f"⚠️ **{88 - captured_count} character(s) were not detected.** "
                "Check the **Inspect Extracted Pen Strokes** grid below. For missing letters, write slightly larger "
                "(**50%–75%** of cell height) with a bolder black pen and verify all **4 corner markers** are 100% visible."
            )

        st.download_button(
            label=f"⬇️ Download {result['filename']}",
            data=result["bytes"],
            file_name=result["filename"],
            mime="font/ttf",
            type="primary",
            use_container_width=True,
        )

        st.divider()

        # Live Browser Font Tester
        b64_font = base64.b64encode(result["bytes"]).decode("utf-8")
        st.subheader("Live Handwriting Font Preview")

        p_col1, p_col2 = st.columns([3, 1])
        with p_col1:
            sample_text = st.text_input(
                "Type text below to preview your font:",
                value="The quick brown fox jumps over the lazy dog! 0123456789",
            )
        with p_col2:
            font_size = st.slider("Preview Size (px)", min_value=24, max_value=72, value=42)

        st.markdown(
            f"""
            <style>
            @font-face {{
                font-family: 'UserCustomFont';
                src: url(data:font/ttf;base64,{b64_font}) format('truetype');
            }}
            .custom-preview {{
                font-family: 'UserCustomFont', sans-serif;
                font-size: {font_size}px;
                line-height: 1.4;
                padding: 24px;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                background-color: #F8FAFC;
                color: #0F172A;
                min-height: 120px;
            }}
            </style>
            <div class="custom-preview">{sample_text}</div>
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
