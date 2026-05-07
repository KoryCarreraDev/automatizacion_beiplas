from fastapi import FastAPI
from src.routes import views, uploads

app = FastAPI(
    title="Automation System Beiplas",
    description="Sistema de automatización para procesamiento de documentos PDF y Excel.",
    version="1.0.0"
)

# Inclusión de routers
app.include_router(views.router)
app.include_router(uploads.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
