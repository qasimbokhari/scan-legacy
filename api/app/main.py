from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.records import router as records_router
from app.routers.analyzer import router as analyzer_router

app = FastAPI(title="SCAN Legacy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(records_router)
app.include_router(analyzer_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
