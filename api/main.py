from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import products, filters, bridges, search, explore
import os

app = FastAPI(title="Vintage Vestige API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(search.router)
app.include_router(products.router)
app.include_router(filters.router)
app.include_router(bridges.router)
app.include_router(explore.router)

@app.get("/health")
def health():
    return {"status": "ok"}