from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, Response
from typing import List, Optional
import os
import io
import uuid
import pypdfium2 as pdfium

from src.services.pdf.extractor import extract_text
from src.services.parsers.ot_parser import extract_ot
from src.services.validators.ot_validator import ot_validation

from src.utils.path import resource_path

router = APIRouter()
templates = Jinja2Templates(directory=resource_path("src/templates"))

# Directorio temporal para archivos
TEMP_DIR = resource_path("temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/upload")
async def upload_files(
    request: Request, 
    files: List[UploadFile] = File(...),
    extra_percent: Optional[float] = Form(3.0)
):
    results = []
    
    for file in files:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(TEMP_DIR, f"{file_id}.pdf")
        
        try:
            content = await file.read()
            
            # Guardar archivo físicamente para impresión posterior
            with open(file_path, "wb") as f:
                f.write(content)
            
            pdf_stream = io.BytesIO(content)
            text = extract_text(pdf_stream)
            
            if not text:
                results.append({
                    "id": file_id,
                    "name": file.filename,
                    "status": "Error",
                    "details": "No se pudo extraer texto del PDF"
                })
                continue

            ot_data = extract_ot(text)
            validation = ot_validation(ot_data, extra_percent=extra_percent)
            
            results.append({
                "id": file_id,
                "name": file.filename,
                "ot": ot_data.get("Orden de Trabajo", "N/A"),
                "cliente": ot_data.get("Cliente", "Desconocido"),
                "status": "Válido" if validation["valid"] else "Inconsistente",
                "valid": validation["valid"],
                "data": ot_data,
                "validation": validation
            })
            
        except Exception as e:
            results.append({
                "id": file_id,
                "name": file.filename,
                "status": "Error",
                "details": str(e)
            })
    
    return templates.TemplateResponse(
        request,
        "components/results_table.html", 
        {"results": results}
    )

@router.get("/api/print/test")
async def print_test():
    return {"status": "ok", "message": "Rutas de impresión activas"}

@router.get("/api/print/single/{file_id}")
async def print_single(file_id: str):
    file_path = os.path.join(TEMP_DIR, f"{file_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {file_id}")
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    return Response(
        content, 
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

@router.get("/api/print/multiple")
async def print_multiple(ids: str):
    file_ids = ids.split(",")
    if not file_ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs")
    
    try:
        dest_pdf = pdfium.PdfDocument.new()
        files_added = 0
        for f_id in file_ids:
            path = os.path.join(TEMP_DIR, f"{f_id}.pdf")
            if os.path.exists(path):
                src_pdf = pdfium.PdfDocument(path)
                dest_pdf.import_pages(src_pdf)
                files_added += 1
        
        if files_added == 0:
            raise HTTPException(status_code=404, detail="No se encontraron archivos válidos para fusionar")

        output = io.BytesIO()
        dest_pdf.save(output)
        output.seek(0)
        
        return Response(
            output.getvalue(), 
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=merged_ots.pdf"}
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error al fusionar PDFs: {str(e)}")

@router.get("/results/clear")
async def clear_results(request: Request):
    # Opcional: Limpiar archivos del TEMP_DIR aquí si se desea
    return templates.TemplateResponse(
        request,
        "components/results_table.html", 
        {"results": []}
    )
