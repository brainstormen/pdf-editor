import streamlit as st
import fitz  # PyMuPDF
import os
import uuid
from io import BytesIO
from streamlit_drawable_canvas import st_canvas
from PIL import Image

st.set_page_config(page_title="Brainstormen.eu PDF Editor", layout="wide")

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Branding
col1, col2 = st.columns([1, 8])
with col1:
    st.image("assets/logo.png", width=100)
with col2:
    st.title("Brainstormen.eu PDF Editor")
    st.markdown("Upload your PDF and edit text and annotations directly.")

# Hide Streamlit defaults and add custom footer
custom_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
[data-testid="stToolbar"] {display: none;}
.custom-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: transparent;
    padding: 10px;
    text-align: center;
    font-size: 14px;
    color: #888;
    z-index: 999;
}
.custom-footer a {
    color: #ff3366;
    text-decoration: none;
    margin: 0 10px;
    font-weight: bold;
}
.custom-footer a:hover {
    text-decoration: underline;
}
</style>
<div class="custom-footer">
    © Brainstormen | 
    <a href="https://brainstormen.eu" target="_blank">brainstormen.eu</a> | 
    <a href="https://instagram.com/brainstormen.eu" target="_blank">Instagram</a>
</div>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# 1. File Upload
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Save the file temporarily if not already saved in session
    if 'file_path' not in st.session_state or st.session_state.get('last_filename') != uploaded_file.name:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state['file_path'] = file_path
        st.session_state['last_filename'] = uploaded_file.name
        st.session_state['page_num'] = 0

    file_path = st.session_state['file_path']
    doc = fitz.open(file_path)
    total_pages = len(doc)

    # 2. Sidebar Navigation and Tools
    st.sidebar.header("Navigation")
    page_num = st.sidebar.number_input("Page Number", min_value=1, max_value=total_pages, value=st.session_state['page_num'] + 1) - 1
    st.session_state['page_num'] = page_num

    st.sidebar.header("Editing Tools")
    tool_mode = st.sidebar.radio(
        "Select Tool",
        ("Redact / Erase", "Add Text")
    )

    if tool_mode == "Redact / Erase":
        st.sidebar.info("Draw a rectangle over the text or image you want to permanently erase. It will be redacted.")
        stroke_color = "#ffffff"
        fill_color = "#ffffff"
        rgb_color = (1.0, 1.0, 1.0)
    else:
        st.sidebar.info("Draw a rectangle where you want to insert text, then type the text below.")
        stroke_color = st.sidebar.color_picker("Text Color", "#000000")
        hex_color = stroke_color.lstrip('#')
        rgb_color = tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
        fill_color = f"rgba({int(rgb_color[0]*255)}, {int(rgb_color[1]*255)}, {int(rgb_color[2]*255)}, 0.2)"
        
    text_to_add = ""
    if tool_mode == "Add Text":
        text_to_add = st.sidebar.text_area("Text to insert in the drawn box:")
        font_size = st.sidebar.number_input("Font Size", min_value=8, max_value=72, value=16)

    # Render current page to image
    page = doc[page_num]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    bg_image = Image.open(BytesIO(img_data))

    # Canvas width and height based on the image
    canvas_width = 800
    canvas_height = int(bg_image.height * (canvas_width / bg_image.width))

    # Initialize a canvas key counter if not present
    if 'canvas_key' not in st.session_state:
        st.session_state['canvas_key'] = 0

    st.write("### Interactive Canvas")
    canvas_result = st_canvas(
        fill_color=fill_color,
        stroke_width=2,
        stroke_color=stroke_color,
        background_image=bg_image,
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="rect",
        key=f"canvas_{page_num}_{tool_mode}_{st.session_state['canvas_key']}",
    )

    # 3. Apply changes and save
    if st.sidebar.button("Apply Changes to Document"):
        if canvas_result.json_data is not None and len(canvas_result.json_data["objects"]) > 0:
            objects = canvas_result.json_data["objects"]
            
            # Scale factors between canvas width and actual PDF page width
            scale_x = page.rect.width / canvas_width
            scale_y = page.rect.height / canvas_height
            
            for obj in objects:
                if obj["type"] == "rect":
                    # Canvas coordinates
                    x, y, w, h = obj["left"], obj["top"], obj["width"] * obj["scaleX"], obj["height"] * obj["scaleY"]
                    
                    # Convert to PDF coordinates
                    rect = fitz.Rect(x * scale_x, y * scale_y, (x + w) * scale_x, (y + h) * scale_y)
                    
                    if tool_mode == "Redact / Erase":
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                    elif tool_mode == "Add Text" and text_to_add:
                        # Attempt to use insert_textbox for text wrapping
                        rc = page.insert_textbox(rect, text_to_add, fontsize=font_size, fontname="helv", color=rgb_color, align=0)
                        if rc < 0:
                            # Fallback if the drawn box is too small for the font size
                            point = fitz.Point(rect.x0, rect.y0 + font_size)
                            page.insert_text(point, text_to_add, fontsize=font_size, fontname="helv", color=rgb_color)
            
            if tool_mode == "Redact / Erase":
                page.apply_redactions()

            # Save the changes permanently to the session file
            doc.saveIncr() # Incremental save to the same file
            doc.close()
            
            # Increment canvas key to clear the drawing
            st.session_state['canvas_key'] += 1
            st.rerun()
        else:
            st.sidebar.warning("No changes detected on the canvas.")

    st.sidebar.markdown("---")
    st.sidebar.header("Download")
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    st.sidebar.download_button(
        label="⬇️ Download Final PDF",
        data=pdf_bytes,
        file_name="edited_document.pdf",
        mime="application/pdf"
    )
