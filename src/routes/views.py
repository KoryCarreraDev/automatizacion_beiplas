from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

templates = Jinja2Templates(directory=os.path.join("src", "templates"))

@router.get("/")
async def index(request: Request):
    """Renderiza la página principal del sistema."""
    return templates.TemplateResponse(request, "index.html")
