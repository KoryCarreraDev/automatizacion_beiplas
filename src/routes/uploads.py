from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import os
import io

from src.services.pdf.extractor import extract_text
from src.services.parsers.ot_parser import extract_ot
from src.services.validators.ot_validator import ot_validation

from src.utils.path import resource_path

router = APIRouter()
templates = Jinja2Templates(directory=resource_path("src/templates"))


@router.post("/upload")
async def upload_files(
    request: Request, 
    files: List[UploadFile] = File(...),
    extra_percent: Optional[float] = Form(3.0)
):
    results = []
    
    for file in files:
        try:
            content = await file.read()
            pdf_stream = io.BytesIO(content)
            
            text = extract_text(pdf_stream)
            
            if not text:
                results.append({
                    "name": file.filename,
                    "status": "Error",
                    "details": "No se pudo extraer texto del PDF"
                })
                continue

            ot_data = extract_ot(text)
            
            validation = ot_validation(ot_data, extra_percent=extra_percent)
            
            results.append({
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
                "name": file.filename,
                "status": "Error",
                "details": str(e)
            })
    
    return templates.TemplateResponse(
        request,
        "components/results_table.html", 
        {"results": results}
    )

@router.get("/results/clear")
async def clear_results(request: Request):
    return templates.TemplateResponse(
        request,
        "components/results_table.html", 
        {"results": []}
    )
