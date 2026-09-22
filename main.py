from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Backend")

# Permitir la conexión con el frontend de Angular (puerto 4200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/ping")
def ping():
    return {"mensaje": "Conexión exitosa con FastAPI"}
