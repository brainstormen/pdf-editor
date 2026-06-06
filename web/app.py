from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import fitz  # PyMuPDF
import os
import uuid
from io import BytesIO

app = FastAPI(title="Antigravity PDF Editor API")

# Setup static and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Temporary storage for uploaded PDFs
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory mapping of file_id to file_path
# In a real app, use a database or redis
session_files = {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        session_files[file_id] = file_path
        
        # Open to get basic info
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        
        return JSONResponse({
            "file_id": file_id,
            "filename": file.filename,
            "page_count": page_count,
            "message": "Upload successful"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/page/{file_id}/{page_num}")
async def get_page_image(file_id: str, page_num: int):
    if file_id not in session_files:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = session_files[file_id]
    
    try:
        doc = fitz.open(file_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Invalid page number")
            
        page = doc[page_num]
        
        # High resolution rendering (zoom factor 2.0)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return StreamingResponse(BytesIO(img_bytes), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
from typing import List, Optional

class ActionModel(BaseModel):
    type: str
    x: float
    y: float
    text: Optional[str] = None
    w: Optional[float] = None
    h: Optional[float] = None
    fontSize: Optional[float] = None
    imgWidth: float
    imgHeight: float

class SaveRequestModel(BaseModel):
    file_id: str
    page_num: int
    actions: List[ActionModel]

@app.post("/api/save")
async def save_pdf(request: SaveRequestModel):
    if request.file_id not in session_files:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = session_files[request.file_id]
    
    try:
        doc = fitz.open(file_path)
        if request.page_num < 0 or request.page_num >= len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Invalid page number")
            
        page = doc[request.page_num]
        
        for action in request.actions:
            # Calculate scaling factors
            scale_x = page.rect.width / action.imgWidth
            scale_y = page.rect.height / action.imgHeight
            
            if action.type == "redact" and action.w and action.h:
                x0 = action.x * scale_x
                y0 = action.y * scale_y
                x1 = (action.x + action.w) * scale_x
                y1 = (action.y + action.h) * scale_y
                rect = fitz.Rect(x0, y0, x1, y1)
                
                # Add white redaction
                annot = page.add_redact_annot(rect, fill=(1, 1, 1))
            
            elif action.type == "text" and action.text:
                x0 = action.x * scale_x
                y0 = action.y * scale_y
                
                # If width and height are provided, use high-fidelity insert_textbox
                if action.w and action.h:
                    x1 = (action.x + action.w) * scale_x
                    y1 = (action.y + action.h) * scale_y
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    font_size = (action.fontSize or 16) * scale_y
                    # default pink/red color from our UI: #ff3366 -> rgb(255, 51, 102) -> (1, 0.2, 0.4)
                    page.insert_textbox(rect, action.text, fontsize=font_size, fontname="helv", color=(1, 0.2, 0.4), align=0)
                else:
                    font_size = (action.fontSize or 16) * scale_y
                    point = fitz.Point(x0, y0 + font_size)
                    page.insert_text(point, action.text, fontsize=font_size, color=(1, 0.2, 0.4))
                
        # Apply any redactions
        page.apply_redactions()
        
        # Save to a new temporary file to send back
        output_id = str(uuid.uuid4())
        output_path = os.path.join(UPLOAD_DIR, f"{output_id}.pdf")
        doc.save(output_path)
        doc.close()
        
        # We can send the file as an attachment
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
            
        # Clean up output
        os.remove(output_path)
        
        return StreamingResponse(
            BytesIO(pdf_bytes), 
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=edited_document.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
