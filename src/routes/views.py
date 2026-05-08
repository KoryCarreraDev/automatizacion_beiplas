from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.utils.path import resource_path


router = APIRouter()


templates = Jinja2Templates(
    directory=resource_path(
        "src/templates"
    )
)


@router.get("/")
async def index(request: Request):

    return templates.TemplateResponse(
        request,
        "index.html"
    )