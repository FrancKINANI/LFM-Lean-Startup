from fastapi import FastAPI
import uvicorn
import logging
from src.api.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="LFM Lean Startup API",
    description="API d'inférence pour l'analyste expert en Lean Startup augmenté (LFM + PostgreSQL Tool Use)",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API LFM Lean Startup. Visitez /docs pour la documentation interactive."}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
