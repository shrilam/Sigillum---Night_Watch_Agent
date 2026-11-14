from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Nightwatch AI API",
    description="Local-only API for the Nightwatch AI incident-response simulator.",
    version="0.1.0",
)
app.include_router(router, prefix="/api")
