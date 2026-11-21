import os
import base64
import streamlit as st
import cv2
from src import CHARACTERS
from src.template_generator import generate_all_templates
from src.paper_scanner import scan_and_clean_sheet
from src.glyph_slicer import slice_glyphs, detect_template_mode
from src.ttf_compiler import compile_font_family, sanitize_font_name
from src.letter_printer import (
    render_letter_html,
    export_letter_pdf_bytes,
    convert_pdf_to_handwriting_bytes,
)

st.set_page_config(
    page_title="Handwriting to TTF Font Generator",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _load_template_assets() -> dict[str, dict[str, bytes | str]]:
    """Generates both Grid and Sentence templates once and caches their bytes."""
    os.makedirs("samples", exist_ok=True)
    generate_all_templates()

    assets: dict[str, dict[str, bytes | str]] = {}
    for mode_key, suffix in [("sentence", "_sentence"), ("grid", "")]:
        png_path = f"samples/blank_template{suffix}.png"
        pdf_path = f"samples/blank_template{suffix}.pdf"
        filled_png_path = f"samples/sample_filled_paper{suffix}.png"
        filled_pdf_path = f"samples/sample_filled_paper{suffix}.pdf"

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        with open(png_path, "rb") as f:
            png_bytes = f.read()
        with open(filled_pdf_path, "rb") as f:
            filled_pdf_bytes = f.read()

        assets[mode_key] = {
            "pdf_bytes": pdf_bytes,
            "png_bytes": png_bytes,
            "filled_pdf_bytes": filled_pdf_bytes,
            "filled_png_path": filled_png_path,
            "pdf_filename": os.path.basename(pdf_path),
            "png_filename": os.path.basename(png_path),
            "filled_filename": os.path.basename(filled_pdf_path),
        }
    return assets


TEMPLATE_ASSETS = _load_template_assets()
with st.sidebar:
    st.title("✒️ Handwriting to TTF")
    st.caption("Local TrueType Font Compiler")
    st.divider()

    st.subheader("1. Choose & Download Template")
    template_choice = st.radio(
        "Template Style:",
        options=["sentence", "grid"],
        format_func=lambda m: (
            "✍️ Sentence Flow (Natural Writing)"
            if m == "sentence"
            else "🔲 Classic Grid (A–Z Boxes)"
        ),
        index=0,
        help="Sentence Flow captures natural handwriting slant and baseline; Classic Grid isolates each character in boxes.",
    )
    active_tpl = TEMPLATE_ASSETS[template_choice]

    st.download_button(
        label="📄 Download A4 PDF Template",
        data=active_tpl["pdf_bytes"],
        file_name=active_tpl["pdf_filename"],
        mime="application/pdf",
        use_container_width=True,
        key="sb_pdf_dl",
    )
    st.download_button(
        label="📱 Download Tablet PNG Template",
        data=active_tpl["png_bytes"],
        file_name=active_tpl["png_filename"],
        mime="image/png",
        use_container_width=True,
        key="sb_png_dl",
    )
    st.download_button(
        label="📥 Download Filled Example PDF",
        data=active_tpl["filled_pdf_bytes"],
        file_name=active_tpl["filled_filename"],
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
        help="Auto-detects whether you uploaded a Sentence Flow or Classic Grid sheet.",
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
            "- **50%–75% Height:** Write letters clearly on the dashed baseline without crossing slot/cell borders.\n"
            "- **Bold Black Ink:** Use a **0.7 mm – 1.0 mm black pen** (or thick stylus brush) for clean stroke detection."
        )
st.header("Custom TrueType (.TTF) Font Studio")

top_col1, top_col2 = st.columns([1.2, 1])

with top_col1:
    mode_badge = "Sentence Flow" if template_choice == "sentence" else "Classic Grid"
    st.subheader(f"Step 1: Get Your Blank Template ({mode_badge})")
    st.write(
        "Print the **A4 PDF** at **100% Actual Size** (disable Fit-to-Page) or draw directly on the **300 DPI PNG**. "
        "Switch between **Sentence Flow** and **Classic Grid** anytime in the sidebar."
    )
    dl_c1, dl_c2 = st.columns(2)
    with dl_c1:
        st.download_button(
            label=f"📄 Download {mode_badge} PDF",
            data=active_tpl["pdf_bytes"],
            file_name=active_tpl["pdf_filename"],
            mime="application/pdf",
            use_container_width=True,
            key="main_pdf_dl",
        )
    with dl_c2:
        st.download_button(
            label=f"📱 Download {mode_badge} PNG",
            data=active_tpl["png_bytes"],
            file_name=active_tpl["png_filename"],
            mime="image/png",
            use_container_width=True,
            key="main_png_dl",
        )

    with st.expander(f"👀 See How to Fill the {mode_badge} Template (Example Sheet)", expanded=(uploaded_file is None)):
        st.image(
            active_tpl["filled_png_path"],
            caption="Example: Write every character bold and centered on the dashed baseline, keeping all 4 corner bullseyes visible.",
            use_container_width=True,
        )
        st.download_button(
            label=f"📥 Download {mode_badge} Filled Example PDF",
            data=active_tpl["filled_pdf_bytes"],
            file_name=active_tpl["filled_filename"],
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
        st.info(f"2️⃣ **Scan Needed:** Upload your completed sheet in the sidebar (or test with `{active_tpl['filled_filename']}`).")
    else:
        st.success(f"2️⃣ **File Ready:** `{uploaded_file.name}`")

st.divider()

if uploaded_file is None or not is_valid_name:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1. Print or Draw")
        st.write("Pick **Sentence Flow** for natural writing rhythm or **Classic Grid** for individual character boxes.")
    with col2:
        st.markdown("### 2. Follow the Filled Guide")
        st.write("Rest letters on the **dashed baseline** and keep all **4 corner markers** 100% visible.")
    with col3:
        st.markdown("### 3. Enter Name & Compile")
        st.write("Type your **User Name** in the sidebar, upload your scan, and download both Regular & Bold `.ttf` fonts.")

else:
    should_compile = (
        generate_clicked
        or "compiled_ttf" not in st.session_state
        or "reg_path" not in st.session_state["compiled_ttf"]
        or st.session_state.get("last_file") != uploaded_file.name
        or st.session_state.get("last_name") != sanitized_name
    )

    if should_compile:
        with st.spinner("Aligning 4 corner markers, auto-detecting template mode, and compiling Regular & Bold vector glyphs..."):
            try:
                file_bytes = uploaded_file.getvalue()
                cleaned_sheet = scan_and_clean_sheet(file_bytes, uploaded_file.name)
                detected_mode = detect_template_mode(cleaned_sheet)
                glyph_masks = slice_glyphs(cleaned_sheet, mode=detected_mode)

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
                        "reg_path": paths["regular"],
                        "bold_path": paths["bold"],
                        "reg_filename": os.path.basename(paths["regular"]),
                        "reg_bytes": reg_bytes,
                        "bold_filename": os.path.basename(paths["bold"]),
                        "bold_bytes": bold_bytes,
                        "glyph_masks": glyph_masks,
                        "detected_mode": detected_mode,
                    }
                    st.session_state["last_file"] = uploaded_file.name
                    st.session_state["last_name"] = sanitized_name
            except Exception as exc:
                st.error(f"Processing failed: {exc}")
    if "compiled_ttf" in st.session_state and "reg_path" in st.session_state["compiled_ttf"]:
        result = st.session_state["compiled_ttf"]
        glyph_masks = result["glyph_masks"]
        captured_count = len(glyph_masks)
        total_chars = len(CHARACTERS)
        coverage_pct = round((captured_count / total_chars) * 100, 1)
        detected_label = (
            "Sentence Flow" if result.get("detected_mode") == "sentence" else "Classic Grid"
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Font Family", f"{sanitized_name} Handwriting")
        m2.metric("Detected Template", detected_label)
        m3.metric("Captured Glyphs", f"{captured_count} / {total_chars} ({coverage_pct}%)")
        m4.metric("Styles Generated", "Regular & Bold")

        if captured_count < total_chars:
            st.warning(
                f"⚠️ **{total_chars - captured_count} character(s) were not detected.** "
                "Check the **Inspect Extracted Pen Strokes** grid below. For missing letters, write slightly larger "
                "(**50%–75%** of height) with a bolder black pen and verify all **4 corner markers** are 100% visible."
            )

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
        st.subheader("✉️ Letter & PDF Font Converter Studio")

        tab_write, tab_convert = st.tabs([
            "✍️ Write a New Handwritten Letter",
            "🔄 Convert Existing PDF to My Font (Optional)",
        ])

        with tab_write:
            l_col1, l_col2 = st.columns([1.1, 1.3])
            default_letter = (
                f"**Date:** November 21, 2026\n\n"
                f"**Dear Partner,**\n\n"
                f"This letter is printed using my **custom enterprise handwriting font**. "
                f"Both **Regular** and **Bold** styles are compiled directly from my own strokes.\n\n"
                f"**Best regards,**\n"
                f"**{sanitized_name}**"
            )

            with l_col1:
                letter_text = st.text_area(
                    "Letter Content (**text** = Bold):",
                    value=default_letter,
                    height=260,
                    key="new_letter_text",
                )
                letter_size = st.slider(
                    "Letter Size (px)",
                    min_value=20,
                    max_value=44,
                    value=26,
                    key="new_letter_size",
                )

            letter_html = render_letter_html(
                letter_text=letter_text,
                user_name=sanitized_name,
                reg_bytes=result["reg_bytes"],
                bold_bytes=result["bold_bytes"],
                font_size_px=letter_size,
            )
            letter_pdf_bytes = export_letter_pdf_bytes(
                letter_text=letter_text,
                reg_ttf_path=result["reg_path"],
                bold_ttf_path=result["bold_path"],
                font_size_pt=max(12, int(letter_size * 0.6)),
            )

            with l_col2:
                st.components.v1.html(letter_html, height=340, scrolling=True)
                dl_l1, dl_l2 = st.columns(2)
                with dl_l1:
                    st.download_button(
                        label="🖨️ Download Printable HTML",
                        data=letter_html.encode("utf-8"),
                        file_name=f"{sanitized_name}-Letter.html",
                        mime="text/html",
                        use_container_width=True,
                        key="dl_new_letter_html",
                    )
                with dl_l2:
                    st.download_button(
                        label="📄 Download Ready-to-Print PDF",
                        data=letter_pdf_bytes,
                        file_name=f"{sanitized_name}-Letter.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_new_letter_pdf",
                    )

        with tab_convert:
            st.write(
                "Upload any existing PDF document (typed in Arial, Times, Calibri, etc.) "
                "to rewrite it in **your own handwriting font**."
            )
            other_pdf = st.file_uploader(
                "Upload another PDF to convert (Optional)",
                type=["pdf"],
                key="convert_other_pdf",
            )
            conv_font_pt = st.slider(
                "Converted PDF Font Size (pt)",
                min_value=12,
                max_value=24,
                value=15,
                key="conv_pdf_pt",
            )

            if other_pdf is not None:
                try:
                    extracted_txt, _ = convert_pdf_to_handwriting_bytes(
                        source_pdf_bytes=other_pdf.getvalue(),
                        reg_ttf_path=result["reg_path"],
                        bold_ttf_path=result["bold_path"],
                        font_size_pt=conv_font_pt,
                    )

                    c_col1, c_col2 = st.columns([1, 1.3])
                    with c_col1:
                        edited_extracted = st.text_area(
                            "Extracted Text (Optional: wrap words in **bold** before downloading):",
                            value=extracted_txt,
                            height=260,
                            key="edited_extracted_pdf_text",
                        )
                        final_conv_pdf = export_letter_pdf_bytes(
                            letter_text=edited_extracted,
                            reg_ttf_path=result["reg_path"],
                            bold_ttf_path=result["bold_path"],
                            font_size_pt=conv_font_pt,
                        )

                    with c_col2:
                        conv_html = render_letter_html(
                            letter_text=edited_extracted,
                            user_name=sanitized_name,
                            reg_bytes=result["reg_bytes"],
                            bold_bytes=result["bold_bytes"],
                            font_size_px=int(conv_font_pt * 1.65),
                        )
                        st.components.v1.html(conv_html, height=340, scrolling=True)
                        st.download_button(
                            label=f"⬇️ Download Converted PDF ({sanitized_name}-{other_pdf.name})",
                            data=final_conv_pdf,
                            file_name=f"{sanitized_name}-{other_pdf.name}",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True,
                            key="dl_converted_pdf",
                        )
                except Exception as conv_err:
                    st.error(f"Could not convert PDF: {conv_err}")

        st.divider()

        with st.expander("🔍 Inspect Extracted Pen Strokes", expanded=True):
            chars = list(glyph_masks.keys())
            cols_per_row = 11
            for row_start in range(0, len(chars), cols_per_row):
                cols = st.columns(cols_per_row)
                for idx, ch in enumerate(chars[row_start : row_start + cols_per_row]):
                    inv_preview = cv2.bitwise_not(glyph_masks[ch])
                    cols[idx].image(inv_preview, caption=ch, use_container_width=True)
