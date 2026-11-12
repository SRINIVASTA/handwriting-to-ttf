import os
import base64
import streamlit as st
import cv2
from src.template_generator import generate_template_png, generate_template_pdf
from src.paper_scanner import scan_and_clean_sheet
from src.glyph_slicer import slice_glyphs
from src.ttf_compiler import compile_ttf, sanitize_font_name

st.set_page_config(page_title="Handwriting to TTF Font Generator", page_icon="✒️", layout="wide")

# Ensure sample templates exist on startup
PNG_TEMPLATE = "samples/blank_template.png"
PDF_TEMPLATE = "samples/blank_template.pdf"
if not os.path.exists(PNG_TEMPLATE):
    generate_template_png(PNG_TEMPLATE)
if not os.path.exists(PDF_TEMPLATE):
    generate_template_pdf(PNG_TEMPLATE, PDF_TEMPLATE)

st.title("✒️ Handwriting to TrueType (.TTF) Font Generator")
st.markdown("Turn your own handwriting into an installable `.ttf` font in three simple steps.")

# --- STEP 1: DOWNLOAD TEMPLATE ---
st.header("Step 1: Download & Fill the Template")
col1, col2 = st.columns(2)

with col1:
    with open(PDF_TEMPLATE, "rb") as f:
        st.download_button(
            label="📄 Download Printable A4 PDF Template",
            data=f.read(),
            file_name="blank_template.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

with col2:
    with open(PNG_TEMPLATE, "rb") as f:
        st.download_button(
            label="📱 Download High-Res PNG (Tablet / Stylus)",
            data=f.read(),
            file_name="blank_template.png",
            mime="image/png",
            use_container_width=True,
        )

st.divider()

# --- STEP 2: NAME & UPLOAD ---
st.header("Step 2: Name Your Font & Upload Scan")
user_name = st.text_input(
    "Enter Your Name (used for the exported .ttf filename and font metadata)",
    value="MyName",
    max_chars=40,
)
preview_filename = f"{sanitize_font_name(user_name)}-Handwriting.ttf"
st.caption(f"Output file will be named: **`{preview_filename}`**")

uploaded_file = st.file_uploader(
    "Upload your filled template (PDF scan, JPG, or PNG)",
    type=["pdf", "jpg", "jpeg", "png"],
)

# --- STEP 3: COMPILE & PREVIEW ---
if uploaded_file is not None:
    st.divider()
    st.header("Step 3: Compile & Download Your Font")

    if st.button("🚀 Generate TrueType (.TTF) Font", type="primary"):
        with st.spinner("Aligning page, extracting pen strokes, and compiling vector glyphs..."):
            try:
                file_bytes = uploaded_file.read()
                cleaned_sheet = scan_and_clean_sheet(file_bytes, uploaded_file.name)
                glyph_masks = slice_glyphs(cleaned_sheet)

                if not glyph_masks:
                    st.error("No handwriting strokes were detected. Please use a darker pen and ensure the 4 corner dots are visible.")
                else:
                    ttf_path = compile_ttf(glyph_masks, user_name=user_name)
                    st.success(f"Successfully compiled **{len(glyph_masks)}** characters into `{os.path.basename(ttf_path)}`!")

                    with open(ttf_path, "rb") as ttf_file:
                        ttf_bytes = ttf_file.read()

                    st.download_button(
                        label=f"⬇️ Download {os.path.basename(ttf_path)}",
                        data=ttf_bytes,
                        file_name=os.path.basename(ttf_path),
                        mime="font/ttf",
                        use_container_width=True,
                    )

                    # Live Font Preview via injected @font-face CSS
                    b64_font = base64.b64encode(ttf_bytes).decode("utf-8")
                    st.subheader("Live Font Preview")
                    sample_text = st.text_input(
                        "Type anything below to test your new handwriting font:",
                        value="The quick brown fox jumps over the lazy dog! 0123456789",
                    )
                    st.markdown(
                        f"""
                        <style>
                        @font-face {{
                            font-family: 'UserCustomFont';
                            src: url(data:font/ttf;base64,{b64_font}) format('truetype');
                        }}
                        .custom-preview {{
                            font-family: 'UserCustomFont', sans-serif;
                            font-size: 42px;
                            padding: 20px;
                            border: 1px solid #CBD5E1;
                            border-radius: 8px;
                            background-color: #F8FAFC;
                            color: #0F172A;
                        }}
                        </style>
                        <div class="custom-preview">{sample_text}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Show sample extracted glyph crops
                    with st.expander("Inspect Extracted Pen Strokes"):
                        sample_chars = list(glyph_masks.keys())[:16]
                        cols = st.columns(8)
                        for idx, ch in enumerate(sample_chars):
                            inv_preview = cv2.bitwise_not(glyph_masks[ch])
                            cols[idx % 8].image(inv_preview, caption=ch, width=65)

            except Exception as exc:
                st.error(f"Processing failed: {exc}")
