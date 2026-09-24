from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infraestructure.adaptadores.inbound.rest import controller

app = FastAPI(title="DataHorse API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # tu Angular en desarrollo
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(controller.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok"}

