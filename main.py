from fastapi import FastAPI

from src.routes import views, uploads


app = FastAPI(
    title="Automation System Beiplas",
    description=(
        "Sistema de automatización "
        "para procesamiento "
        "de documentos PDF y Excel."
    ),
    version="1.0.0"
)

app.include_router(views.router)
app.include_router(uploads.router)