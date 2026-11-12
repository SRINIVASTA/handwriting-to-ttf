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

# Ensure sample templates exist on startup
PNG_TEMPLATE = "samples/blank_template.png"
PDF_TEMPLATE = "samples/blank_template.pdf"
if not os.path.exists(PNG_TEMPLATE):
    generate_template_png(PNG_TEMPLATE)
if not os.path.exists(PDF_TEMPLATE):
    generate_template_pdf(PNG_TEMPLATE, PDF_TEMPLATE)

# ==========================================
# SIDEBAR: TEMPLATE DOWNLOADS, NAME & UPLOAD
# ==========================================
with st.sidebar:
    st.title("✒️ Handwriting to TTF")
    st.caption("Local TrueType Font Compiler")
    st.divider()

    # --- STEP 1: DOWNLOAD TEMPLATE ---
    st.subheader("1. Download Template")
    with open(PDF_TEMPLATE, "rb") as f:
        st.download_button(
            label="📄 Printable A4 PDF",
            data=f.read(),
            file_name="blank_template.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with open(PNG_TEMPLATE, "rb") as f:
        st.download_button(
            label="📱 Tablet / Stylus PNG",
            data=f.read(),
            file_name="blank_template.png",
            mime="image/png",
            use_container_width=True,
        )

    st.divider()

    # --- STEP 2: FONT NAME & UPLOAD ---
    st.subheader("2. Name & Upload Scan")
    user_name = st.text_input(
        "Font / Creator Name",
        value="MyName",
        max_chars=40,
    )
    preview_filename = f"{sanitize_font_name(user_name)}-Handwriting.ttf"
    st.caption(f"Target file: **`{preview_filename}`**")

    uploaded_file = st.file_uploader(
        "Upload filled sheet (PDF, JPG, PNG)",
        type=["pdf", "jpg", "jpeg", "png"],
    )

    generate_clicked = st.button(
        "🚀 Generate .TTF Font",
        type="primary",
        use_container_width=True,
        disabled=(uploaded_file is None),
    )

    st.divider()
    with st.expander("✍️ Writing Tips"):
        st.markdown(
            "- Use a **dark black pen**.\n"
            "- Rest letters on the **dashed line**.\n"
            "- Keep all **4 corner dots** visible."
        )

# ==========================================
# MAIN WORKSPACE: PREVIEW, METRICS & EXPORT
# ==========================================
st.header("Custom TrueType (.TTF) Font Studio")

if uploaded_file is None:
    st.info("👈 Start in the sidebar: download a blank template, fill it out, enter your name, and upload your scan.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### Step 1: Print or Draw")
        st.write("Download the **A4 PDF** to write on paper with a black pen, or use the **PNG** on a tablet.")
    with col2:
        st.markdown("### Step 2: Scan & Upload")
        st.write("Take a clear photo or scan keeping all four corner bullseyes visible, then upload it on the left.")
    with col3:
        st.markdown("### Step 3: Test & Install")
        st.write("Preview your live handwriting right in the browser and download your installable `.ttf` font.")

else:
    # Run compilation automatically on upload or when button is clicked
    if generate_clicked or "compiled_ttf" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name or st.session_state.get("last_name") != user_name:
        with st.spinner("Aligning page, isolating strokes, and compiling vector glyphs..."):
            try:
                file_bytes = uploaded_file.read()
                cleaned_sheet = scan_and_clean_sheet(file_bytes, uploaded_file.name)
                glyph_masks = slice_glyphs(cleaned_sheet)

                if not glyph_masks:
                    st.error("No handwriting strokes detected. Ensure a dark pen was used and all 4 corner markers are visible.")
                    st.session_state.pop("compiled_ttf", None)
                else:
                    ttf_path = compile_ttf(glyph_masks, user_name=user_name)
                    with open(ttf_path, "rb") as ttf_file:
                        ttf_bytes = ttf_file.read()

                    st.session_state["compiled_ttf"] = {
                        "path": ttf_path,
                        "filename": os.path.basename(ttf_path),
                        "bytes": ttf_bytes,
                        "glyph_masks": glyph_masks,
                    }
                    st.session_state["last_file"] = uploaded_file.name
                    st.session_state["last_name"] = user_name
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

    # Render compiled results from session state
    if "compiled_ttf" in st.session_state:
        result = st.session_state["compiled_ttf"]
        glyph_masks = result["glyph_masks"]

        m1, m2, m3 = st.columns(3)
        m1.metric("Output Font", result["filename"])
        m2.metric("Captured Glyphs", f"{len(glyph_masks)} / 88")
        m3.metric("File Size", f"{len(result['bytes']) / 1024:.1f} KB")

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
