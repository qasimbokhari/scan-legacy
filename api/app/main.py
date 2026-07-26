from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.app.core.config import settings
from api.app.routers.auth import router as auth_router

app = FastAPI(title="SCAN Legacy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
